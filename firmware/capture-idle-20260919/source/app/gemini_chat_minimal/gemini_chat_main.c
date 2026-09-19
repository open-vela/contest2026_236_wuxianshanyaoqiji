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
#include "qiji_avatar.h"

enum command { CMD_NONE, CMD_RECORD, CMD_STOP, CMD_ASK, CMD_SPEAK };
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t wake = PTHREAD_COND_INITIALIZER;
static enum command command;
static bool busy, recording, dirty = true, started, agent_ready;
static bool speak_reply;
static qiji_avatar_state_t avatar_state = QIJI_IDLE;
static char status[128] = "准备就绪：点击说话";
static char question[512], answer[2048], input[512];
static velaclaw_client_t *client;
static lv_obj_t *status_label, *question_label, *answer_label;
static lv_obj_t *voice_label, *voice_button;
static bool wifi_connected;

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
             "准备就绪：点击说话" : "AI 服务尚未就绪");
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
    snprintf(status, sizeof(status), "%s (%d)", text, code);
    busy = false;
    recording = false;
    avatar_state = answer[0] ? QIJI_REPLY : QIJI_ERROR;
    dirty = true;
    pthread_mutex_unlock(&lock);
}

static void reply(int rc, const char *text, void *cookie)
{
    (void)cookie;
    pthread_mutex_lock(&lock);
    snprintf(answer, sizeof(answer), "%s", text ? text : "没有收到回复");
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
    if (!client) client = velaclaw_client_open("qiji_chat");
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
                snprintf(status, sizeof(status), "%s", "正在录音，再点一次结束");
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
            set_status("正在朗读回复…");
            rc = voice_channel_speak(text);
            if (rc) fail("回复已显示，语音播放未成功", rc);
            else {
                pthread_mutex_lock(&lock);
                busy = false;
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

static void voice_event(lv_event_t *event)
{
    (void)event;
    pthread_mutex_lock(&lock);
    bool start = !recording;
    pthread_mutex_unlock(&lock);
    qiji_chat_record(start);
}

static void refresh(lv_timer_t *timer)
{
    (void)timer;
    static unsigned refresh_count;
    pthread_mutex_lock(&lock);
    if (refresh_count++ % 20 == 0) {
        struct in_addr addr = {0};
        bool connected = !netlib_get_ipv4addr("wlan0", &addr) && addr.s_addr &&
            addr.s_addr != inet_addr("10.0.0.2");
        if (connected != wifi_connected) { wifi_connected = connected; dirty = true; }
    }
    qiji_avatar_update(avatar_state, lv_tick_get());
    if (dirty) {
        lv_label_set_text_fmt(status_label, "%s · %s",
            wifi_connected ? "Wi-Fi 已连接" : "Wi-Fi 未连接",
            agent_ready ? status : "等待 AI 服务启动…");
        lv_label_set_text(question_label, question[0] ? question : "你好，我是绮迹。");
        lv_label_set_text(answer_label, answer[0] ? answer : "今天想聊点什么？");
        lv_label_set_text(voice_label, recording ? "结束录音" : "点击说话");
        if (busy || !agent_ready) lv_obj_add_state(voice_button, LV_STATE_DISABLED);
        else lv_obj_remove_state(voice_button, LV_STATE_DISABLED);
        dirty = false;
    }
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
    lv_obj_t *screen = lv_screen_active();
    lv_obj_remove_flag(screen, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_style_bg_color(screen, lv_color_hex(0x14243a), 0);
    lv_obj_set_style_text_color(screen, lv_color_hex(0xf3f7ff), 0);
    const lv_font_t *font = &lv_font_simsun_16_cjk;
#if LV_USE_FREETYPE
    lv_font_t *ttf = lv_freetype_font_create("/resource/fonts/MiSans-Normal.ttf",
        LV_FREETYPE_FONT_RENDER_MODE_BITMAP, 16, LV_FREETYPE_FONT_STYLE_NORMAL);
    if (ttf) font = ttf;
#endif
    lv_obj_set_style_text_font(screen, font, 0);
    int width = lv_display_get_horizontal_resolution(result.disp);
    int height = lv_display_get_vertical_resolution(result.disp);
    status_label = lv_label_create(screen);
    lv_obj_set_pos(status_label, 8, 6);
    lv_obj_set_width(status_label, width - 16);
    lv_label_set_long_mode(status_label, LV_LABEL_LONG_SCROLL_CIRCULAR);
    int stage_width = width >= 300 ? 108 : 100;
    qiji_avatar_create(screen, 6, 32, stage_width, height - 104);
    lv_obj_t *chat = lv_obj_create(screen);
    lv_obj_set_pos(chat, stage_width + 12, 32);
    lv_obj_set_size(chat, width - stage_width - 18, height - 104);
    lv_obj_set_style_bg_color(chat, lv_color_hex(0x21364d), 0);
    lv_obj_set_style_border_width(chat, 0, 0);
    lv_obj_set_style_pad_all(chat, 8, 0);
    lv_obj_set_flex_flow(chat, LV_FLEX_FLOW_COLUMN);
    question_label = lv_label_create(chat);
    answer_label = lv_label_create(chat);
    lv_obj_set_width(question_label, lv_pct(100));
    lv_obj_set_width(answer_label, lv_pct(100));
    lv_obj_set_style_text_color(question_label, lv_color_hex(0x83e2cb), 0);
    voice_button = lv_button_create(screen);
    lv_obj_set_pos(voice_button, 6, height - 64);
    lv_obj_set_size(voice_button, width - 12, 58);
    voice_label = lv_label_create(voice_button);
    lv_obj_center(voice_label);
    lv_obj_add_event_cb(voice_button, voice_event, LV_EVENT_CLICKED, NULL);
    pthread_t thread;
    pthread_attr_t attr;
    pthread_attr_init(&attr);
    pthread_attr_setstacksize(&attr, 65536);
    int rc = pthread_create(&thread, &attr, worker, NULL);
    pthread_attr_destroy(&attr);
    if (rc) { fail("对话线程启动失败", rc); goto failed; }
    pthread_detach(thread);
    lv_timer_create(refresh, 100, NULL);
    printf("qiji_chat: LCD ready %dx%d, /dev/lcd0, /dev/input0\n", width, height);
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
