/* SPDX-License-Identifier: Apache-2.0 */
#include "qiji_view.h"
#include "qiji_version.h"
#include "qiji_scroll.h"
#include "qiji_sprite.h"
#include "qiji_layout.h"
#include "qiji_material_icons.h"
#include <string.h>
#include <time.h>

static lv_obj_t *status_label, *question_label, *answer_label, *answer_clip;
static lv_obj_t *voice_button, *mic_icon, *stop_icon, *busy_icon;
static uint32_t status_since;
static unsigned status_slot;
static qiji_scroll_t scroll;
static bool audio_playing;
static uint32_t audio_played_ms, audio_duration_ms;
static char last_status[128];
static lv_obj_t *clock_label;
static char last_clock[32];

static lv_obj_t *plain(lv_obj_t *parent, int x, int y, int w, int h)
{
    lv_obj_t *obj = lv_obj_create(parent);
    lv_obj_remove_style_all(obj);
    lv_obj_remove_flag(obj, LV_OBJ_FLAG_CLICKABLE | LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_pos(obj, x, y);
    lv_obj_set_size(obj, w, h);
    return obj;
}

static lv_obj_t *material_icon(lv_obj_t *button, const lv_image_dsc_t *image)
{
    lv_obj_t *icon = lv_image_create(button);
    lv_obj_remove_flag(icon, LV_OBJ_FLAG_CLICKABLE);
    lv_image_set_src(icon, image);
    lv_obj_center(icon);
    return icon;
}

static void create_record_icons(lv_obj_t *button)
{
    mic_icon = material_icon(button, &material_mic);
    stop_icon = material_icon(button, &material_stop);
    busy_icon = material_icon(button, &material_more_horiz);
    lv_obj_add_flag(stop_icon, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(busy_icon, LV_OBJ_FLAG_HIDDEN);
}

static void show_record_icon(bool recording, bool waiting)
{
    lv_obj_add_flag(mic_icon, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(stop_icon, LV_OBJ_FLAG_HIDDEN);
    lv_obj_add_flag(busy_icon, LV_OBJ_FLAG_HIDDEN);
    lv_obj_remove_flag(recording ? stop_icon : waiting ? busy_icon : mic_icon,
                       LV_OBJ_FLAG_HIDDEN);
}

lv_obj_t *qiji_view_create(lv_obj_t *screen, int width, int height,
                           const char *font_path)
{
    const lv_font_t *body = &lv_font_simsun_16_cjk;
    const lv_font_t *small = body;
#if LV_USE_FREETYPE
    lv_font_t *font = lv_freetype_font_create(font_path,
        LV_FREETYPE_FONT_RENDER_MODE_BITMAP, 14, LV_FREETYPE_FONT_STYLE_NORMAL);
    if (font) body = font;
    font = lv_freetype_font_create(font_path,
        LV_FREETYPE_FONT_RENDER_MODE_BITMAP, 12, LV_FREETYPE_FONT_STYLE_NORMAL);
    if (font) small = font;
#else
    (void)font_path;
#endif
    lv_obj_remove_flag(screen, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_style_bg_color(screen, lv_color_hex(0x191a2c), 0);
    lv_obj_set_style_text_color(screen, lv_color_hex(0xf7f1ff), 0);
    lv_obj_set_style_text_font(screen, body, 0);

    /* A fixed 20px status row; only this narrow strip scrolls long messages. */
    lv_obj_t *header = plain(screen, 0, 0, width, QIJI_HEADER_HEIGHT);
    status_label = lv_label_create(header);
    lv_obj_set_style_text_font(status_label, small, 0);
    lv_obj_set_style_text_color(status_label, lv_color_hex(0xc6b7df), 0);
    lv_obj_set_pos(status_label, 8, 2);
    lv_obj_set_width(status_label, width - 108);
    lv_label_set_long_mode(status_label, LV_LABEL_LONG_SCROLL_CIRCULAR);
    clock_label = lv_label_create(header);
    lv_obj_set_style_text_font(clock_label, small, 0);
    lv_obj_set_style_text_color(clock_label, lv_color_hex(0xe5d7f4), 0);
    lv_obj_set_style_text_align(clock_label, LV_TEXT_ALIGN_RIGHT, 0);
    lv_obj_set_pos(clock_label, width - 96, 2);
    lv_obj_set_width(clock_label, 88);
    lv_label_set_long_mode(clock_label, LV_LABEL_LONG_CLIP);
    last_clock[0] = 0;

    const int card_x = QIJI_OUTER_GAP;
    const int card_y = QIJI_HEADER_HEIGHT + QIJI_OUTER_GAP;
    const int card_w = width - 2 * QIJI_OUTER_GAP;
    const int card_h = height - card_y - QIJI_OUTER_GAP;
    const int bubble_x = card_x + QIJI_INNER_GAP;
    const int bubble_w = card_w - 2 * QIJI_INNER_GAP;
    const int bubble_bottom = height - QIJI_OUTER_GAP - QIJI_INNER_GAP;
    const int bubble_y = bubble_bottom - QIJI_DIALOGUE_HEIGHT;
    const int button_x = bubble_x + bubble_w - QIJI_INNER_GAP - QIJI_RECORD_SIZE;
    const int button_y = bubble_bottom - QIJI_INNER_GAP - QIJI_RECORD_SIZE;
    const int text_w = button_x - QIJI_INNER_GAP - (bubble_x + QIJI_INNER_GAP);
    qiji_avatar_create(screen, card_x, card_y, card_w, card_h);

    /* Created after the character: text is a translucent foreground layer.
     * Keep the face visible, with the dialogue across the lower body. */
    lv_obj_t *bubble = plain(screen, bubble_x, bubble_y, bubble_w, QIJI_DIALOGUE_HEIGHT);
    lv_obj_set_style_bg_color(bubble, lv_color_hex(0x1c2036), 0);
    lv_obj_set_style_bg_opa(bubble, LV_OPA_60, 0);
    lv_obj_set_style_radius(bubble, QIJI_DIALOGUE_RADIUS, 0);
    lv_obj_set_style_border_width(bubble, 0, 0);
    question_label = lv_label_create(bubble);
    lv_obj_set_pos(question_label, QIJI_INNER_GAP, QIJI_INNER_GAP);
    lv_obj_set_width(question_label, bubble_w - 2 * QIJI_INNER_GAP);
    lv_obj_set_style_text_font(question_label, small, 0);
    lv_obj_set_style_text_color(question_label, lv_color_hex(0xb9e5da), 0);
    lv_label_set_long_mode(question_label, LV_LABEL_LONG_DOT);
    lv_obj_set_height(question_label, lv_font_get_line_height(small));

    /* Reserve a right gutter for the floating recording control. */
    answer_clip = plain(bubble, QIJI_INNER_GAP, 26, text_w,
                        QIJI_DIALOGUE_HEIGHT - 26 - QIJI_INNER_GAP);
    answer_label = lv_label_create(answer_clip);
    lv_obj_set_width(answer_label, text_w);
    lv_obj_set_style_text_line_space(answer_label, 2, 0);
    lv_label_set_long_mode(answer_label, LV_LABEL_LONG_WRAP);

    voice_button = lv_button_create(screen);
    lv_obj_remove_style_all(voice_button);
    lv_obj_remove_flag(voice_button, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_ext_click_area(voice_button, 6);
    lv_obj_set_pos(voice_button, button_x, button_y);
    lv_obj_set_size(voice_button, QIJI_RECORD_SIZE, QIJI_RECORD_SIZE);
    lv_obj_set_style_radius(voice_button, LV_RADIUS_CIRCLE, 0);
    lv_obj_set_style_pad_all(voice_button, 0, 0);
    lv_obj_set_style_border_width(voice_button, 0, 0);
    lv_obj_set_style_bg_opa(voice_button, LV_OPA_60, 0);
    lv_obj_set_style_bg_color(voice_button, lv_color_hex(0x9871bc), 0);
    lv_obj_set_style_shadow_width(voice_button, 0, 0);
    create_record_icons(voice_button);
    last_status[0] = 0;
    status_slot = 0;
    scroll = (qiji_scroll_t){0};
    status_since = 0;
    return voice_button;
}

void qiji_view_audio(bool playing, uint32_t played_ms, uint32_t duration_ms)
{
    audio_playing = playing;
    audio_played_ms = played_ms;
    audio_duration_ms = duration_ms;
}

void qiji_view_update(bool wifi, bool ready, bool busy, bool recording,
                      qiji_avatar_state_t state, const char *status,
                      const char *question, const char *answer,
                      bool changed, uint32_t tick)
{
    qiji_sprite_speaking(audio_playing);
    char clock_text[32];
    time_t now = time(NULL);
    if (now >= 1767225600) {
        /* Display Beijing time without changing the UTC clock used by TLS. */
        now += 8 * 60 * 60;
        struct tm local;
        gmtime_r(&now, &local);
        lv_snprintf(clock_text, sizeof(clock_text), "%02d:%02d v%s",
                    local.tm_hour, local.tm_min, QIJI_VERSION);
    } else {
        lv_snprintf(clock_text, sizeof(clock_text), "--:-- v%s", QIJI_VERSION);
    }
    if (strcmp(last_clock, clock_text)) {
        lv_label_set_text(clock_label, clock_text);
        lv_snprintf(last_clock, sizeof(last_clock), "%s", clock_text);
    }
    const char *current = ready ? status : "等待 AI 服务启动…";
    bool status_changed = strcmp(last_status, current) != 0;
    if (status_changed) {
        lv_snprintf(last_status, sizeof(last_status), "%s", current);
        status_slot = 0;
        status_since = tick;
    } else if (tick - status_since >= 4000) {
        status_slot ^= 1;
        status_since = tick;
        status_changed = true;
    }
    if (changed || status_changed) {
        lv_label_set_text(status_label, status_slot ?
            (wifi ? "Wi-Fi 已连接" : "Wi-Fi 未连接") : current);
        show_record_icon(recording, !ready || busy);
        if (busy || !ready) lv_obj_add_state(voice_button, LV_STATE_DISABLED);
        else lv_obj_remove_state(voice_button, LV_STATE_DISABLED);
        lv_obj_set_style_bg_color(voice_button,
            lv_color_hex(recording ? 0xb75d83 : 0x9871bc), 0);
    }
    /* Do not restart reading when only Wi-Fi or playback status changes. */
    const char *q = question[0] ? question : QIJI_ASSISTANT_NAME " · 在这里陪你";
    const char *a = answer[0] ? answer :
        (question[0] ? "让我想一想…" : "今天想聊点什么？");
    if (strcmp(lv_label_get_text(question_label), q) ||
        strcmp(lv_label_get_text(answer_label), a)) {
        lv_label_set_text(question_label, q);
        lv_label_set_text(answer_label, a);
        qiji_sprite_reply(a);
        scroll = (qiji_scroll_t){0};
        lv_obj_set_y(answer_label, 0);
        lv_obj_update_layout(answer_label);
    }
    unsigned characters = 0;
    for (const unsigned char *p = (const unsigned char *)a; *p; p++)
        if ((*p & 0xc0) != 0x80) characters++;
    /* Until streaming completes, estimate duration at 4.5 characters/s.
     * Once known, use PCM duration; monotonic scrolling avoids backtracking. */
    uint32_t duration = audio_duration_ms ? audio_duration_ms : characters * 220 + 800;
    int overflow = lv_obj_get_height(answer_label) - lv_obj_get_height(answer_clip);
    int offset = qiji_scroll_step(&scroll, tick, overflow, audio_playing,
        busy && answer[0] && !audio_playing, audio_played_ms, duration);
    lv_obj_set_y(answer_label, -offset);
    qiji_avatar_update(state, tick);
}
