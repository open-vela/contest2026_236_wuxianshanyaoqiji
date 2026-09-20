/* SPDX-License-Identifier: Apache-2.0 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdatomic.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/event_groups.h"
#include "freertos/semphr.h"
#include "esp_event.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "esp_http_client.h"
#include "esp_system.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "cJSON.h"
#include "bsp_display.h"
#include "bsp_audio.h"
#include "bsp_button.h"
#include "bsp_battery.h"
#include "companion_ui.h"
#include "config_line.h"

static EventGroupHandle_t events;
static QueueHandle_t keys, audio_jobs;
static char host[128], token[96];
static atomic_int completed, audio_result;
static atomic_bool cancel_audio, playing;
static bool audio_ready;
static SemaphoreHandle_t audio_mutex;
static TaskHandle_t voice_task;
enum { VOICE_IDLE, VOICE_STARTING, VOICE_RECORDING, VOICE_WAITING, VOICE_PLAYING, VOICE_DONE };
static atomic_int voice_state;
static atomic_bool voice_finish, voice_cancel;
typedef struct { int button, event; } key_job_t;
enum { WIFI_READY = 1 };
typedef struct { int seq, rate; char path[64]; } audio_job_t;

static const char *str(cJSON *o, const char *key)
{
    cJSON *v = cJSON_GetObjectItemCaseSensitive(o, key);
    return cJSON_IsString(v) ? v->valuestring : "";
}

static esp_http_client_handle_t http(const char *path, esp_http_client_method_t method)
{
    char url[208], auth[112];
    if (snprintf(url, sizeof(url), "%s%s", host, path) >= sizeof(url)) return NULL;
    snprintf(auth, sizeof(auth), "Bearer %s", token);
    esp_http_client_config_t cfg = { .url = url, .timeout_ms = 4000,
        .buffer_size = 1024, .buffer_size_tx = 512, .disable_auto_redirect = true };
    esp_http_client_handle_t h = esp_http_client_init(&cfg);
    if (!h) return NULL;
    esp_http_client_set_method(h, method);
    esp_http_client_set_header(h, "Authorization", auth);
    esp_http_client_set_header(h, "Content-Type", "application/json");
    return h;
}

static cJSON *poll_server(int ack, bool ok, const char *action)
{
    char request[192];
    snprintf(request, sizeof(request),
        "{\"device\":\"xiaocheng\",\"ack\":%d,\"result\":\"%s\",\"action\":\"%s\",\"ready\":%s}",
        ack, ok ? "ok" : "error", action, atomic_load(&voice_state) == VOICE_IDLE ? "true" : "false");
    esp_http_client_handle_t h = http("/v1/poll", HTTP_METHOD_POST);
    if (!h) return NULL;
    cJSON *result = NULL;
    char *response = malloc(4096);
    if (!response) goto done;
    size_t length = strlen(request);
    if (esp_http_client_open(h, length) != ESP_OK) goto done;
    int sent = 0;
    while (sent < length) {
        int n = esp_http_client_write(h, request + sent, length - sent);
        if (n <= 0) goto done;
        sent += n;
    }
    int64_t expected = esp_http_client_fetch_headers(h);
    if (esp_http_client_get_status_code(h) != 200 || expected < 0 || expected >= 4096) goto done;
    int used = 0;
    while (used < expected) {
        int n = esp_http_client_read(h, response + used, expected - used);
        if (n <= 0) goto done;
        used += n;
    }
    response[used] = 0;
    result = cJSON_Parse(response);
done:
    free(response);
    esp_http_client_close(h); esp_http_client_cleanup(h);
    return result;
}

static bool play_audio(const audio_job_t *job)
{
    if (!audio_ready || (job->rate != 16000 && job->rate != 24000)) return false;
    if (bsp_audio_set_format(job->rate, 16, 1) != ESP_OK) return false;
    esp_http_client_handle_t h = http(job->path, HTTP_METHOD_GET);
    if (!h) return false;
    bool ok = false;
    unsigned char pcm[1024];
    if (esp_http_client_open(h, 0) != ESP_OK) goto done;
    int64_t total = esp_http_client_fetch_headers(h);
    if (esp_http_client_get_status_code(h) != 200 || total <= 0 || total > 3000000 || total % 2) goto done;
    int64_t read = 0;
    unsigned carry = 0;
    while (read < total && !atomic_load(&cancel_audio)) {
        int n = esp_http_client_read(h, (char *)pcm + carry, sizeof(pcm) - carry);
        if (n <= 0) goto done;
        read += n;
        unsigned bytes = (n + carry) & ~1u;
        unsigned energy = 0;
        for (unsigned i = 0; i < bytes; i += 2) {
            int sample = (int16_t)(pcm[i] | ((unsigned)pcm[i + 1] << 8));
            energy += (unsigned)abs(sample);
        }
        companion_ui_level(bytes ? energy / (bytes / 2) / 90 : 0);
        if (bytes && bsp_audio_write(pcm, bytes) != ESP_OK) goto done;
        carry = (n + carry) - bytes;
        if (carry) pcm[0] = pcm[bytes];
    }
    /* Allow the small I2S DMA tail to finish before granting the next speaker. */
    vTaskDelay(pdMS_TO_TICKS(180));
    ok = read == total && !carry && !atomic_load(&cancel_audio);
done:
    companion_ui_level(0);
    esp_http_client_close(h); esp_http_client_cleanup(h);
    return ok;
}

static void audio_worker(void *arg)
{
    (void)arg;
    audio_job_t job;
    for (;;) {
        if (!xQueueReceive(audio_jobs, &job, portMAX_DELAY)) continue;
        bool locked = xSemaphoreTake(audio_mutex, pdMS_TO_TICKS(5000)) == pdTRUE;
        bool ok = locked && atomic_load(&voice_state) == VOICE_IDLE && !atomic_load(&cancel_audio) && play_audio(&job);
        if (locked) xSemaphoreGive(audio_mutex);
        atomic_store(&audio_result, ok ? 0 : -1);
        atomic_store(&completed, job.seq);
        atomic_store(&playing, false);
    }
}

static bool http_write_all(esp_http_client_handle_t h, const void *data, size_t length)
{
    const char *p = data;
    while (length) {
        int n = esp_http_client_write(h, p, length);
        if (n <= 0) return false;
        p += n; length -= n;
    }
    return true;
}

static cJSON *voice_request(const char *path, const char *body)
{
    esp_http_client_handle_t h = http(path, body ? HTTP_METHOD_POST : HTTP_METHOD_GET);
    if (!h) return NULL;
    char *data = malloc(4096);
    cJSON *result = NULL;
    size_t length = body ? strlen(body) : 0;
    if (!data || esp_http_client_open(h, length) != ESP_OK) goto done;
    if (length && !http_write_all(h, body, length)) goto done;
    int64_t total = esp_http_client_fetch_headers(h);
    if (esp_http_client_get_status_code(h) != 200 || total < 0 || total >= 4096) goto done;
    int used = 0;
    while (used < total) {
        int n = esp_http_client_read(h, data + used, total - used);
        if (n <= 0) goto done;
        used += n;
    }
    data[used] = 0; result = cJSON_Parse(data);
done:
    free(data);
    esp_http_client_close(h); esp_http_client_cleanup(h);
    return result;
}

static bool record_upload(const char *id)
{
    char path[64]; snprintf(path, sizeof(path), "/v1/voice/upload/%s", id);
    if (bsp_audio_set_format(16000, 16, 1) != ESP_OK) return false;
    esp_http_client_handle_t h = http(path, HTTP_METHOD_POST);
    if (!h) return false;
    esp_http_client_set_header(h, "Content-Type", "application/octet-stream");
    esp_http_client_set_header(h, "Transfer-Encoding", "chunked");
    bool ok = false;
    int16_t pcm[512];
    if (esp_http_client_open(h, -1) != ESP_OK) goto done;
    /* Drain old RX DMA before displaying the recording indicator. */
    for (int i = 0; i < 4; ++i)
        if (bsp_audio_read(pcm, sizeof(pcm)) != ESP_OK) goto done;
    if (atomic_load(&voice_cancel)) goto done;
    atomic_store(&voice_state, VOICE_RECORDING);
    companion_ui_message("正在录音", "主人", "请说话，再按确认键发送。最长录音二十秒。");
    size_t total = 0;
    int64_t started = esp_timer_get_time();
    unsigned last_seconds = 0;
    while (!atomic_load(&voice_finish) && !atomic_load(&voice_cancel) && total + sizeof(pcm) <= 640000) {
        if (bsp_audio_read(pcm, sizeof(pcm)) != ESP_OK) goto done;
        /* Long stalls would lose microphone samples: reject, never send a partial transcript. */
        int64_t write_start = esp_timer_get_time();
        if (!http_write_all(h, "400\r\n", 5) || !http_write_all(h, pcm, sizeof(pcm)) ||
            !http_write_all(h, "\r\n", 2) || esp_timer_get_time() - write_start > 250000) goto done;
        total += sizeof(pcm);
        unsigned seconds = (esp_timer_get_time() - started) / 1000000;
        if (seconds != last_seconds) {
            char status[48]; snprintf(status, sizeof(status), "正在录音 %us", seconds);
            companion_ui_message(status, NULL, NULL); last_seconds = seconds;
        }
        if (seconds >= 20) break;
    }
    if (atomic_load(&voice_cancel) || total < 8000) goto done;
    atomic_store(&voice_state, VOICE_WAITING);
    companion_ui_message("正在识别", "主人", "录音已结束，正在识别你说的话。");
    if (!http_write_all(h, "0\r\n\r\n", 5)) goto done;
    esp_http_client_fetch_headers(h);
    ok = esp_http_client_get_status_code(h) == 200;
done:
    esp_http_client_close(h); esp_http_client_cleanup(h);
    return ok;
}

static void voice_worker(void *arg)
{
    (void)arg;
    for (;;) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        char id[17] = "", path[64];
        bool held = false, success = false, acknowledged = false;
        companion_ui_message("准备录音", "小澄", "正在准备麦克风，请稍等。");
        if (!(xEventGroupGetBits(events) & WIFI_READY) || !audio_ready) goto failed;
        /* Cancel and drain the old playback before touching the codec format. */
        atomic_store(&cancel_audio, true);
        int64_t end = esp_timer_get_time() + 6000000;
        while (atomic_load(&playing) && esp_timer_get_time() < end) vTaskDelay(pdMS_TO_TICKS(20));
        if (atomic_load(&playing) || atomic_load(&voice_cancel)) goto failed;
        if (xSemaphoreTake(audio_mutex, pdMS_TO_TICKS(2000)) != pdTRUE) goto failed;
        held = true;
        cJSON *r = voice_request("/v1/voice/start", "{}");
        if (!r) {
            companion_ui_message("语音服务未就绪", "小澄", "请检查电脑语音服务和接口配置，再按确认键重试。");
            goto finish;
        }
        const char *value = str(r, "id");
        if (strlen(value) == 16 && strspn(value, "0123456789abcdef") == 16) snprintf(id, sizeof(id), "%s", value);
        cJSON_Delete(r);
        if (!id[0] || atomic_load(&voice_cancel) || !record_upload(id)) goto failed;
        xSemaphoreGive(audio_mutex); held = false;
        end = esp_timer_get_time() + 120000000;
        char last[24] = "";
        while (!atomic_load(&voice_cancel) && esp_timer_get_time() < end) {
            snprintf(path, sizeof(path), "/v1/voice/%s", id);
            r = voice_request(path, NULL);
            if (!r) goto failed;
            const char *state = str(r, "state");
            if (!strcmp(state, "error") || !strcmp(state, "cancelled")) {
                companion_ui_message("语音请求失败", "小澄", str(r, "error"));
                cJSON_Delete(r); goto finish;
            }
            if (!strcmp(state, "ready")) {
                audio_job_t job = {0};
                cJSON *rate = cJSON_GetObjectItemCaseSensitive(r, "rate");
                job.rate = cJSON_IsNumber(rate) ? rate->valueint : 0;
                snprintf(path, sizeof(path), "/v1/voice/audio/%s", id);
                bool valid = !strcmp(str(r, "audio"), path);
                snprintf(job.path, sizeof(job.path), "%s", path);
                if (valid) companion_ui_message("小澄正在回答", "小澄", str(r, "text"));
                cJSON_Delete(r);
                if (!valid || atomic_load(&voice_cancel)) goto failed;
                if (xSemaphoreTake(audio_mutex, pdMS_TO_TICKS(2000)) != pdTRUE) goto failed;
                held = true;
                atomic_store(&cancel_audio, false);
                atomic_store(&voice_state, VOICE_PLAYING);
                if (atomic_load(&voice_cancel)) atomic_store(&cancel_audio, true);
                success = play_audio(&job);
                xSemaphoreGive(audio_mutex); held = false;
                if (atomic_load(&voice_cancel)) goto finish;
                snprintf(path, sizeof(path), "/v1/voice/ack/%s", id);
                r = voice_request(path, success ? "{\"ok\":true}" : "{\"ok\":false}");
                acknowledged = r != NULL; cJSON_Delete(r);
                if (!success) goto failed;
                companion_ui_message("按确认键继续聊", NULL, NULL);
                goto finish;
            }
            if (strcmp(last, state)) {
                if (!strcmp(state, "thinking")) companion_ui_message("正在想回答", "你说", str(r, "transcript"));
                else if (!strcmp(state, "synthesizing")) companion_ui_message("准备语音", "小澄", str(r, "text"));
                snprintf(last, sizeof(last), "%s", state);
            }
            cJSON_Delete(r);
            vTaskDelay(pdMS_TO_TICKS(400));
        }
failed:
        if (!atomic_load(&voice_cancel)) companion_ui_message("语音请求失败", "小澄", "录音太短、网络或语音服务异常，请按确认键重试。");
finish:
        if (held) xSemaphoreGive(audio_mutex);
        if (id[0] && (!success || !acknowledged || atomic_load(&voice_cancel))) {
            snprintf(path, sizeof(path), "/v1/voice/cancel/%s", id);
            cJSON *cancel = voice_request(path, "{}"); cJSON_Delete(cancel);
        }
        if (atomic_load(&voice_cancel)) companion_ui_message("已停止", "小澄", "按确认键重新录音，或长按确认键找伙伴聊天。");
        companion_ui_level(0);
        atomic_store(&voice_state, VOICE_DONE);
    }
}

static void key_event(bsp_btn_t button, bsp_btn_ev_t event, void *arg)
{
    (void)arg;
    if (event != BSP_BTN_CLICK && event != BSP_BTN_LONG) return;
    int state = atomic_load(&voice_state);
    if (button == BSP_BTN_OK && state > VOICE_IDLE && state < VOICE_DONE) {
        if (event == BSP_BTN_CLICK && state == VOICE_RECORDING) atomic_store(&voice_finish, true);
        else { atomic_store(&voice_cancel, true); atomic_store(&cancel_audio, true); }
        return;
    }
    key_job_t job = {button, event}; xQueueSend(keys, &job, 0);
}

static void network_worker(void *arg)
{
    (void)arg;
    int last_seq = 0;
    bool active = false;
    int64_t battery_at = 0;
    char last_state[32] = "";
    for (;;) {
        const char *action = "";
        key_job_t key;
        while (xQueueReceive(keys, &key, 0)) {
            if (key.event == BSP_BTN_CLICK && key.button == BSP_BTN_UP) companion_ui_scroll(40);
            if (key.event == BSP_BTN_CLICK && key.button == BSP_BTN_DOWN) companion_ui_scroll(-40);
            if (key.button == BSP_BTN_OK) {
                int state = atomic_load(&voice_state);
                if (state != VOICE_IDLE && state != VOICE_DONE) continue;
                if (key.event == BSP_BTN_LONG) {
                    atomic_store(&voice_state, VOICE_IDLE);
                    action = active ? "stop" : "start";
                    if (active) atomic_store(&cancel_audio, true);
                } else {
                    atomic_store(&voice_finish, false); atomic_store(&voice_cancel, false);
                    atomic_store(&voice_state, VOICE_STARTING); atomic_store(&cancel_audio, true);
                    action = "stop"; active = false;
                    xTaskNotifyGive(voice_task);
                }
            }
        }
        if (esp_timer_get_time() > battery_at) {
            companion_ui_battery(bsp_battery_soc());
            battery_at = esp_timer_get_time() + 60000000;
        }
        if (!(xEventGroupGetBits(events) & WIFI_READY) || !host[0]) {
            vTaskDelay(pdMS_TO_TICKS(300)); continue;
        }
        cJSON *r = poll_server(atomic_load(&completed), atomic_load(&audio_result) == 0, action);
        if (atomic_load(&voice_state) != VOICE_IDLE) {
            cJSON_Delete(r); last_state[0] = 0;
            vTaskDelay(pdMS_TO_TICKS(150)); continue;
        }
        if (!r) {
            atomic_store(&cancel_audio, true);
            companion_ui_message("连接服务中", NULL, NULL);
            last_state[0] = 0;
            vTaskDelay(pdMS_TO_TICKS(1000)); continue;
        }
        const char *state = str(r, "state");
        active = !strcmp(state, "generating") || !strcmp(state, "speaking") || !strcmp(state, "summarizing");
        if (strcmp(state, last_state)) {
            if (!strcmp(state, "complete")) companion_ui_message("给主人：本轮小结", NULL, NULL);
            else if (!strcmp(state, "stopped")) {
                atomic_store(&cancel_audio, true);
                companion_ui_message("本轮已停止", "长按确认键重新开始", str(r, "error"));
            } else if (!strcmp(state, "waiting")) companion_ui_message("按确认键与我聊天", "小澄", "短按确认键开始录音，再按发送。长按确认键与伙伴聊天。");
            else if (strcmp(state, "speaking")) companion_ui_message("正在想下一句话", NULL, NULL);
            snprintf(last_state, sizeof(last_state), "%s", state);
        }
        cJSON *seq = cJSON_GetObjectItemCaseSensitive(r, "seq");
        if (active && cJSON_IsNumber(seq) && seq->valueint > 0 && seq->valueint != last_seq && !atomic_load(&playing)) {
            int id = seq->valueint;
            const char *text = str(r, "text");
            bool speak = cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(r, "speak"));
            bool summary = !strcmp(str(r, "kind"), "summary");
            bool mine = !strcmp(str(r, "speaker"), "xiaocheng");
            companion_ui_message(summary ? "给主人：本轮小结" : mine ? "轮到小澄说话" : "在听伙伴说话",
                summary ? "共同整理" : str(r, "speaker_name"), text);
            last_seq = id;
            atomic_store(&audio_result, 0);
            if (speak) {
                audio_job_t job = { .seq = id };
                cJSON *rate = cJSON_GetObjectItemCaseSensitive(r, "rate");
                job.rate = cJSON_IsNumber(rate) ? rate->valueint : 0;
                const char *path = str(r, "audio");
                if (strncmp(path, "/v1/audio/", 10) || strlen(path) >= sizeof(job.path)) {
                    atomic_store(&audio_result, -1); atomic_store(&completed, id);
                } else {
                    snprintf(job.path, sizeof(job.path), "%s", path);
                    atomic_store(&cancel_audio, false); atomic_store(&playing, true);
                    if (!xQueueSend(audio_jobs, &job, 0)) {
                        atomic_store(&playing, false); atomic_store(&audio_result, -1); atomic_store(&completed, id);
                    }
                }
            } else atomic_store(&completed, id);
        }
        cJSON_Delete(r);
        vTaskDelay(pdMS_TO_TICKS(650));
    }
}

static void wifi_event(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    (void)arg; (void)data;
    if (base == IP_EVENT) xEventGroupSetBits(events, WIFI_READY);
    else if (id == WIFI_EVENT_STA_START) esp_wifi_connect();
    else if (id == WIFI_EVENT_STA_DISCONNECTED) {
        xEventGroupClearBits(events, WIFI_READY);
        atomic_store(&cancel_audio, true);
        esp_wifi_connect();
    }
}

/* USB console configuration avoids compiling SSIDs or secrets into firmware.
 * One JSON line, never echoed. Stored in our own NVS namespace only. */
static void console_worker(void *arg)
{
    (void)arg;
    config_line_t line = {0};
    for (;;) {
        int ch = getchar();
        if (ch == EOF) { clearerr(stdin); vTaskDelay(pdMS_TO_TICKS(20)); continue; }
        int frame = config_line_feed(&line, ch);
        if (!frame) continue;
        if (frame < 0) { puts("DUET_CONFIG_INVALID"); continue; }
        cJSON *j = cJSON_Parse(line.text);
        memset(line.text, 0, sizeof(line.text));
        if (!j) continue;
        const char *ssid = str(j, "ssid"), *password = str(j, "password");
        const char *h = str(j, "host"), *t = str(j, "token");
        bool valid = *ssid && strlen(ssid) <= 32 && strlen(password) <= 63 &&
            !strncmp(h, "http://", 7) && strlen(h) < sizeof(host) &&
            strlen(t) >= 16 && strlen(t) < sizeof(token) && !strpbrk(h, "\r\n\"") && !strpbrk(t, "\r\n\"");
        nvs_handle_t nvs;
        bool ok = false;
        if (valid && nvs_open("qiji_duet", NVS_READWRITE, &nvs) == ESP_OK) {
            ok = nvs_set_str(nvs, "ssid", ssid) == ESP_OK && nvs_set_str(nvs, "password", password) == ESP_OK &&
                nvs_set_str(nvs, "host", h) == ESP_OK && nvs_set_str(nvs, "token", t) == ESP_OK && nvs_commit(nvs) == ESP_OK;
            nvs_close(nvs);
        }
        cJSON_Delete(j);
        puts(ok ? "DUET_CONFIG_OK" : "DUET_CONFIG_INVALID");
        if (ok) { vTaskDelay(pdMS_TO_TICKS(300)); esp_restart(); }
    }
}

void app_main(void)
{
    ESP_ERROR_CHECK(bsp_display_init());
    if (!bsp_lvgl_init() || !bsp_lvgl_lock(2000)) return;
    companion_ui_init(); bsp_lvgl_unlock();
    bsp_display_backlight(75);
    events = xEventGroupCreate(); keys = xQueueCreate(6, sizeof(key_job_t)); audio_jobs = xQueueCreate(1, sizeof(audio_job_t));
    audio_mutex = xSemaphoreCreateMutex();
    if (!events || !keys || !audio_jobs || !audio_mutex) { companion_ui_message("内存不足", NULL, NULL); return; }
    audio_ready = bsp_audio_init() == ESP_OK;
    if (audio_ready) bsp_audio_set_volume(55);
    bsp_battery_init();
    ESP_ERROR_CHECK(bsp_button_init(key_event, NULL));
    esp_err_t nvserr = nvs_flash_init();
    if (nvserr != ESP_OK) {
        companion_ui_message("配置存储需要检查", NULL, "没有自动擦除原有数据，请检查串口日志。");
        ESP_LOGE("duet", "NVS: %s; not erased", esp_err_to_name(nvserr)); return;
    }
    if (xTaskCreate(voice_worker, "solo_voice", 8192, NULL, 4, &voice_task) != pdPASS ||
        xTaskCreate(audio_worker, "duet_audio", 6144, NULL, 4, NULL) != pdPASS ||
        xTaskCreate(network_worker, "duet_net", 7168, NULL, 3, NULL) != pdPASS ||
        xTaskCreate(console_worker, "duet_config", 4096, NULL, 2, NULL) != pdPASS) {
        companion_ui_message("任务启动失败", NULL, NULL); return;
    }
    nvs_handle_t nvs;
    char ssid[33] = "", password[65] = "";
    if (nvs_open("qiji_duet", NVS_READONLY, &nvs) == ESP_OK) {
        size_t n = sizeof(ssid); nvs_get_str(nvs, "ssid", ssid, &n);
        n = sizeof(password); nvs_get_str(nvs, "password", password, &n);
        n = sizeof(host); nvs_get_str(nvs, "host", host, &n);
        n = sizeof(token); nvs_get_str(nvs, "token", token, &n); nvs_close(nvs);
    }
    if (!ssid[0] || !host[0] || !token[0]) {
        companion_ui_message("初次见面，我是小澄", "等待配置网络", "请通过电脑配置网络，之后我就能和桌面伙伴自动聊天啦。"); return;
    }
    ESP_ERROR_CHECK(esp_netif_init()); ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT(); ESP_ERROR_CHECK(esp_wifi_init(&init));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, wifi_event, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, wifi_event, NULL));
    wifi_config_t config = {0};
    memcpy(config.sta.ssid, ssid, strlen(ssid)); memcpy(config.sta.password, password, strlen(password));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA)); ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &config));
    memset(password, 0, sizeof(password)); memset(&config, 0, sizeof(config));
    ESP_ERROR_CHECK(esp_wifi_start());
    printf("Xiaocheng 0.1 started; free heap=%lu\n", (unsigned long)esp_get_free_heap_size());
}
