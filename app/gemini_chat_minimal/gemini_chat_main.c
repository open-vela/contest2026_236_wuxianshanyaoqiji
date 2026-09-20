/* SPDX-License-Identifier: Apache-2.0 */
/* Minimal Gemini-S1 UI, using the official LCD backend and AI Agent API.
 * Only the UI task calls LVGL. Recording/network/TTS run on a worker.
 */
#include <nuttx/config.h>
#include <lvgl/lvgl.h>
#include <velaclaw/client.h>
#include "voice/voice_channel.h"
#include <errno.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <netutils/netlib.h>
#include <arpa/inet.h>
#include <time.h>
#include "infra/config_store.h"
#include "qiji_view.h"
#include "qiji_keys.h"
#include "qiji_version.h"
#include "qiji_dialogue_text.h"
#include "qiji_audio_envelope.h"
#include "qiji_sprite.h"
#include "qiji_duet.h"

enum command { CMD_NONE, CMD_RECORD, CMD_STOP, CMD_ASK, CMD_SPEAK };
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t wake = PTHREAD_COND_INITIALIZER;
static enum command command;
static bool busy, recording, dirty = true, started, agent_ready;
static bool speak_reply;
static bool speech_requested, audio_network_done;
static uint64_t audio_bytes;
static uint32_t audio_start_ms;
static qiji_audio_envelope_t audio_envelope;

static uint32_t monotonic_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint32_t)((uint64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000);
}

/* Audio worker callbacks only update protected state, never LVGL. */
void qiji_chat_audio_chunk(const unsigned char *pcm, size_t bytes)
{
    pthread_mutex_lock(&lock);
    if (speech_requested && bytes) {
        if (!audio_bytes) audio_start_ms = monotonic_ms();
        audio_bytes += bytes; /* 24kHz, mono, signed 16-bit before upsampling */
        qiji_envelope_push(&audio_envelope, pcm, bytes);
    }
    pthread_mutex_unlock(&lock);
}

void qiji_chat_audio_network_done(void)
{
    pthread_mutex_lock(&lock);
    audio_network_done = true;
    pthread_mutex_unlock(&lock);
}
static qiji_avatar_state_t avatar_state = QIJI_IDLE;
static char status[128] = "准备就绪：按 ENTER 说话";
static char question[512], answer[2048], input[512];
static velaclaw_client_t *client;
static bool wifi_connected;
static int duet_result;

bool qiji_chat_duet_ready(void)
{
    pthread_mutex_lock(&lock);
    bool ready = started && agent_ready && !recording && (!busy || duet_result == -EINPROGRESS);
    pthread_mutex_unlock(&lock);
    return ready;
}

int qiji_chat_duet_result(void)
{
    pthread_mutex_lock(&lock);
    int result = duet_result;
    pthread_mutex_unlock(&lock);
    return result;
}

int qiji_chat_duet_present(const char *text, bool speak, bool summary, const char *speaker)
{
    if (!text || !*text || strlen(text) >= sizeof(answer)) return -EINVAL;
    pthread_mutex_lock(&lock);
    if (!started || !agent_ready || busy || recording) { pthread_mutex_unlock(&lock); return -EBUSY; }
    snprintf(answer, sizeof(answer), "%s", text);
    snprintf(question, sizeof(question), "%s", summary ? "给主人 · 本轮小结" :
             !strcmp(speaker, "xiaocheng") ? "小澄正在说话" : QIJI_ASSISTANT_NAME "正在说话");
    snprintf(status, sizeof(status), "%s", summary ? "伙伴们的共同总结" : QIJI_ASSISTANT_NAME "与小澄 · 伙伴对话");
    avatar_state = speak ? QIJI_REPLY : QIJI_LISTEN;
    duet_result = speak ? -EINPROGRESS : 0;
    busy = speak;
    dirty = true;
    if (speak) { command = CMD_SPEAK; pthread_cond_signal(&wake); }
    pthread_mutex_unlock(&lock);
    return 0;
}

void qiji_chat_print_result(void)
{
    pthread_mutex_lock(&lock);
    printf("busy=%d recording=%d\nstatus=%s\nreply=%s\n", busy, recording, status, answer);
    pthread_mutex_unlock(&lock);
}

/* Called by the agent after its queues, voice backend and worker tasks exist. */
void qiji_chat_agent_ready(bool ready)
{
    pthread_mutex_lock(&lock);
    agent_ready = ready;
    snprintf(status, sizeof(status), "%s", ready ?
             "准备就绪：按 ENTER 说话" : "AI 服务尚未就绪");
    dirty = true;
    pthread_mutex_unlock(&lock);
}

bool qiji_chat_is_ready(void)
{
    pthread_mutex_lock(&lock);
    bool ready = agent_ready;
    pthread_mutex_unlock(&lock);
    return ready;
}

int qiji_chat_submit(const char *text)
{
    if (qiji_duet_active()) return -EBUSY;
    if (!text || !*text || strlen(text) >= sizeof(input)) return -EINVAL;
    pthread_mutex_lock(&lock);
    if (!agent_ready || !started || busy || recording) {
        pthread_mutex_unlock(&lock);
        return -EBUSY;
    }
    snprintf(input, sizeof(input), "%s", text);
    speak_reply = true;
    avatar_state = QIJI_THINK;
    busy = true;
    command = CMD_ASK;
    dirty = true;
    pthread_cond_signal(&wake);
    pthread_mutex_unlock(&lock);
    return 0;
}

static void set_status(const char *text)
{
    pthread_mutex_lock(&lock);
    snprintf(status, sizeof(status), "%s", text);
    dirty = true;
    pthread_mutex_unlock(&lock);
}

static void fail(const char *text, int code)
{
    pthread_mutex_lock(&lock);
    if (duet_result == -EINPROGRESS) duet_result = code ? code : -EIO;
    snprintf(status, sizeof(status), "%s (%d)", text, code);
    busy = false;
    recording = false;
    speech_requested = false;
    avatar_state = answer[0] ? QIJI_REPLY : QIJI_ERROR;
    dirty = true;
    pthread_mutex_unlock(&lock);
}

static void reply(int rc, const char *text, void *cookie)
{
    (void)cookie;
    pthread_mutex_lock(&lock);
    qiji_dialogue_text(answer, sizeof(answer), text);
    if (!answer[0]) snprintf(answer, sizeof(answer), "%s", "没有收到可朗读的回复，请再试一次。");
    snprintf(status, sizeof(status), "%s", rc ? "对话失败" : "已收到回复");
    dirty = true;
    avatar_state = rc ? QIJI_ERROR : QIJI_REPLY;
    if (!rc && text && *text && speak_reply) {
        command = CMD_SPEAK;
        pthread_cond_signal(&wake);
    } else {
        busy = false;
    }
    pthread_mutex_unlock(&lock);
}

static void ask(const char *text)
{
    pthread_mutex_lock(&lock);
    snprintf(question, sizeof(question), "%s", text);
    answer[0] = 0;
    avatar_state = QIJI_THINK;
    snprintf(status, sizeof(status), "%s", "正在等待模型回复…");
    dirty = true;
    pthread_mutex_unlock(&lock);
    if (!client) client = velaclaw_client_open(QIJI_CHARACTER_SESSION);
    if (!client) {
        fail("AI 服务尚未就绪", -ENODEV);
        return;
    }
    velaclaw_ask_req_t req = { .text = text, .timeout_ms = 90000 };
    int rc = velaclaw_ask(client, &req, reply, NULL);
    if (rc) fail("发送失败，请检查 AI 服务", rc);
}

static void *worker(void *arg)
{
    (void)arg;
    char text[2048];
    for (;;) {
        pthread_mutex_lock(&lock);
        while (command == CMD_NONE) pthread_cond_wait(&wake, &lock);
        enum command next = command;
        command = CMD_NONE;
        snprintf(text, sizeof(text), "%s", next == CMD_SPEAK ? answer : input);
        pthread_mutex_unlock(&lock);
        int rc;
        if (next == CMD_RECORD) {
            struct in_addr address={0};
            if (netlib_get_ipv4addr("wlan0", &address)<0 || !address.s_addr ||
                address.s_addr==inet_addr("10.0.0.2")) {
                fail("Wi-Fi 未连接，请先配置网络", -ENETUNREACH);
                continue;
            }
            char key[256]={0};
            int key_rc=claw_config_get("aliyun_asr_key",key,sizeof(key));
            bool have_key=!key_rc && key[0];
            memset(key,0,sizeof(key));
            if (!have_key) {
                fail("请先配置阿里云语音 Key", -EACCES);
                continue;
            }
            if (time(NULL)<1767225600) {
                fail("正在等待网络校时，请稍后重试", -EAGAIN);
                continue;
            }
            rc = voice_channel_start();
            if (rc) {
                fail(rc == -ETIMEDOUT ? "语音服务等待超时，请稍后重试" :
                     "麦克风服务启动失败，请检查媒体服务", rc);
            } else {
                pthread_mutex_lock(&lock);
                recording = true;
                avatar_state = QIJI_LISTEN;
                busy = false;
                snprintf(status, sizeof(status), "%s", "正在录音，再按 ENTER 结束");
                dirty = true;
                pthread_mutex_unlock(&lock);
            }
        } else if (next == CMD_STOP) {
            text[0] = 0;
            rc = voice_channel_stop_with_text(text, sizeof(text));
            if (rc) fail("语音识别失败，请检查配置和网络", rc);
            else if (!text[0]) fail("没有识别到语音，请重试", 0);
            else ask(text);
        } else if (next == CMD_ASK) {
            ask(text);
        } else if (next == CMD_SPEAK) {
            pthread_mutex_lock(&lock);
            speech_requested = true;
            audio_network_done = false;
            audio_bytes = 0;
            qiji_envelope_reset(&audio_envelope);
            pthread_mutex_unlock(&lock);
            set_status("正在朗读回复…");
            rc = voice_channel_speak(text);
            if (rc) fail("回复已显示，语音播放未成功", rc);
            else {
                pthread_mutex_lock(&lock);
                busy = false;
                speech_requested = false;
                if (duet_result == -EINPROGRESS) duet_result = 0;
                snprintf(status, sizeof(status), "%s", "可以继续对话");
                dirty = true;
                pthread_mutex_unlock(&lock);
            }
        }
    }
    return NULL;
}

/* ADB diagnostics use the same worker and transitions as the touch button. */
int qiji_chat_record(bool start)
{
    if (qiji_duet_active()) { qiji_duet_stop(); return 0; }
    int rc = -EBUSY;
    pthread_mutex_lock(&lock);
    if (started && !busy && agent_ready && recording != start) {
        speak_reply = true;
        avatar_state = recording ? QIJI_THINK : QIJI_LISTEN;
        busy = true;
        command = recording ? CMD_STOP : CMD_RECORD;
        recording = false;
        snprintf(status, sizeof(status), "%s",
                 command == CMD_STOP ? "正在识别语音…" : "正在开启麦克风…");
        dirty = true;
        pthread_cond_signal(&wake);
        rc = 0;
    }
    pthread_mutex_unlock(&lock);
    return rc;
}

int qiji_chat_toggle(void)
{
    pthread_mutex_lock(&lock);
    bool start = !recording;
    pthread_mutex_unlock(&lock);
    return qiji_chat_record(start);
}

static void voice_event(lv_event_t *event)
{
    (void)event;
    qiji_chat_toggle();
}

static void read_keys(lv_timer_t *timer)
{
    (void)timer;
    qiji_keys_poll(lv_tick_get());
}

static void refresh(lv_timer_t *timer)
{
    (void)timer;
    static unsigned refresh_count;
    pthread_mutex_lock(&lock);
    if (refresh_count++ % 40 == 0) {
        struct in_addr addr = {0};
        bool connected = !netlib_get_ipv4addr("wlan0", &addr) && addr.s_addr &&
            addr.s_addr != inet_addr("10.0.0.2");
        if (connected != wifi_connected) { wifi_connected = connected; dirty = true; }
    }
    bool playing = speech_requested && audio_bytes > 0;
    uint32_t pcm_ms = audio_bytes / 48;
    uint32_t played = playing ? monotonic_ms() - audio_start_ms : 0;
    if (played > pcm_ms) played = pcm_ms;
    qiji_view_audio(playing, played, audio_network_done ? pcm_ms : 0);
    qiji_sprite_audio_level(playing ? qiji_envelope_at(&audio_envelope, played) : 0);
    qiji_view_update(wifi_connected, agent_ready, busy, recording, avatar_state,
                     status, question, answer, dirty, lv_tick_get());
    dirty = false;
    pthread_mutex_unlock(&lock);
}

int qiji_chat_main(int argc, char **argv)
{
    (void)argc;
    (void)argv;
    pthread_mutex_lock(&lock);
    if (started) { pthread_mutex_unlock(&lock); return -EBUSY; }
    started = true;
    pthread_mutex_unlock(&lock);
    if (lv_is_initialized()) {
        fprintf(stderr, "qiji_chat requires sole ownership of LVGL; disable launcher autostart\n");
        goto failed;
    }
    lv_init();
    lv_nuttx_dsc_t info;
    lv_nuttx_result_t result;
    lv_nuttx_dsc_init(&info);
    info.fb_path = "/dev/lcd0";
    info.input_path = "/dev/input0";
    lv_nuttx_init(&info, &result);
    if (!result.disp) {
        fprintf(stderr, "qiji_chat: /dev/lcd0 initialization failed\n");
        goto failed;
    }
    int width = lv_display_get_horizontal_resolution(result.disp);
    int height = lv_display_get_vertical_resolution(result.disp);
    lv_obj_t *voice_button = qiji_view_create(lv_screen_active(), width, height,
                                              "/resource/fonts/MiSans-Normal.ttf");
    lv_obj_add_event_cb(voice_button, voice_event, LV_EVENT_CLICKED, NULL);
    pthread_t thread;
    pthread_attr_t attr;
    pthread_attr_init(&attr);
    pthread_attr_setstacksize(&attr, 65536);
    int rc = pthread_create(&thread, &attr, worker, NULL);
    pthread_attr_destroy(&attr);
    if (rc) { fail("对话线程启动失败", rc); goto failed; }
    pthread_detach(thread);
    qiji_duet_start();
    qiji_keys_init();
    lv_timer_create(read_keys, 20, NULL);
    lv_timer_create(refresh, 50, NULL);
    printf("qiji_chat: v%s LCD ready %dx%d, /dev/lcd0, /dev/input0\n", QIJI_VERSION, width, height);
    for (;;) {
        uint32_t delay = lv_timer_handler();
        if (delay > 20) delay = 20;
        usleep((delay ? delay : 1) * 1000);
    }
failed:
    pthread_mutex_lock(&lock);
    started = false;
    pthread_mutex_unlock(&lock);
    return 1;
}
