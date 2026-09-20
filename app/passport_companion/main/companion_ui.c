/* SPDX-License-Identifier: Apache-2.0
 * Original Xiaocheng character, flash-resident frames from editable artwork.
 */
#include "companion_ui.h"
#include "bsp_display.h"
#include "lvgl.h"
#include <stdatomic.h>

LV_FONT_DECLARE(companion_font);
LV_FONT_DECLARE(companion_status_font);
LV_IMAGE_DECLARE(companion_character_idle);
LV_IMAGE_DECLARE(companion_character_half_blink);
LV_IMAGE_DECLARE(companion_character_blink);
LV_IMAGE_DECLARE(companion_character_speak_small);
LV_IMAGE_DECLARE(companion_character_speak_large);
static lv_obj_t *portrait, *state_label, *who_label;
static lv_obj_t *text_label, *bubble, *battery;
static atomic_uint audio_level;
/* The 16 px font reserves a 31 px line box; tighten dialogue to 20 px. */
enum { DIALOGUE_LINE_SPACE = -11 };

static lv_obj_t *shape(lv_obj_t *p, int x, int y, int w, int h, int radius, unsigned color)
{
    lv_obj_t *o = lv_obj_create(p);
    lv_obj_remove_style_all(o);
    lv_obj_set_pos(o, x, y); lv_obj_set_size(o, w, h);
    lv_obj_set_style_bg_color(o, lv_color_hex(color), 0);
    lv_obj_set_style_bg_opa(o, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(o, radius, 0);
    lv_obj_remove_flag(o, LV_OBJ_FLAG_SCROLLABLE);
    return o;
}

static lv_obj_t *label(lv_obj_t *p, int x, int y, int width, const char *s, unsigned color)
{
    lv_obj_t *o = lv_label_create(p);
    lv_obj_set_pos(o, x, y); lv_obj_set_width(o, width);
    lv_obj_set_style_text_font(o, &companion_font, 0);
    lv_obj_set_style_text_color(o, lv_color_hex(color), 0);
    lv_label_set_text(o, s);
    return o;
}

static void animate(lv_timer_t *timer)
{
    (void)timer;
    unsigned t = lv_tick_get();
    lv_obj_set_y(portrait, 28 + (t / 500 % 4 == 0 ? 0 : t / 500 % 4 == 2 ? 2 : 1));
    unsigned level = atomic_load(&audio_level);
    unsigned blink_tick = t % 4500;
    const lv_image_dsc_t *frame = blink_tick >= 4290 && blink_tick < 4420 ? &companion_character_blink :
        blink_tick >= 4210 ? &companion_character_half_blink :
        level > 55 ? &companion_character_speak_large :
        level > 10 ? &companion_character_speak_small : &companion_character_idle;
    if (lv_image_get_src(portrait) != frame) lv_image_set_src(portrait, frame);
    /* Keep long dialogue readable without a touchscreen; keys can also scroll. */
    if (t % 8000 < 80 && lv_obj_get_scroll_bottom(bubble) > 0)
        lv_obj_scroll_by(bubble, 0, -(companion_font.line_height + DIALOGUE_LINE_SPACE), LV_ANIM_ON);
}

void companion_ui_init(void)
{
    lv_obj_t *s = lv_screen_active();
    lv_obj_set_style_bg_color(s, lv_color_hex(0xeff1fb), 0);
    lv_obj_remove_flag(s, LV_OBJ_FLAG_SCROLLABLE);
    state_label = label(s, 16, 8, 168, "小澄 / 等待伙伴", 0x656a92);
    lv_obj_set_style_text_font(state_label, &companion_status_font, 0);
    lv_obj_set_height(state_label, companion_status_font.line_height);
    lv_label_set_long_mode(state_label, LV_LABEL_LONG_DOT);
    battery = label(s, 189, 8, 35, "--%", 0x656a92);
    lv_obj_set_style_text_font(battery, &companion_status_font, 0);
    lv_obj_set_style_text_align(battery, LV_TEXT_ALIGN_RIGHT, 0);
    portrait = lv_image_create(s);
    lv_image_set_src(portrait, &companion_character_idle);
    lv_obj_set_pos(portrait, 0, 28);
    /* Created after the portrait: translucent dialogue floats over its body. */
    lv_obj_t *overlay = shape(s, 12, 212, 216, 96, 14, 0xffffff);
    lv_obj_set_style_bg_opa(overlay, 204, 0);
    who_label = label(overlay, 10, 3, 196, "随身伙伴", 0x6b65a2);
    lv_obj_set_style_text_font(who_label, &companion_status_font, 0);
    bubble = shape(overlay, 10, 25, 196, 63, 0, 0xffffff);
    lv_obj_set_style_bg_opa(bubble, LV_OPA_TRANSP, 0);
    lv_obj_add_flag(bubble, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_scroll_dir(bubble, LV_DIR_VER);
    lv_obj_set_scrollbar_mode(bubble, LV_SCROLLBAR_MODE_OFF);
    text_label = label(bubble, 0, 0, 195, "我会把我们聊到的小点子，整理给主人。", 0x384263);
    lv_obj_set_style_text_line_space(text_label, DIALOGUE_LINE_SPACE, 0);
    lv_timer_create(animate, 80, NULL);
}

void companion_ui_message(const char *state, const char *who, const char *text)
{
    if (!bsp_lvgl_lock(1000)) return;
    lv_label_set_text_fmt(state_label, "小澄 / %s", state);
    if (who) lv_label_set_text(who_label, who);
    if (text) { lv_label_set_text(text_label, text); lv_obj_scroll_to_y(bubble, 0, LV_ANIM_OFF); }
    bsp_lvgl_unlock();
}

void companion_ui_battery(int percent)
{
    if (!bsp_lvgl_lock(100)) return;
    if (percent < 0) lv_label_set_text(battery, "--%");
    else lv_label_set_text_fmt(battery, "%d%%", percent);
    bsp_lvgl_unlock();
}

void companion_ui_scroll(int delta)
{
    if (!bsp_lvgl_lock(100)) return;
    int line_step = companion_font.line_height + DIALOGUE_LINE_SPACE;
    if (delta) lv_obj_scroll_by(bubble, 0, delta < 0 ? -line_step : line_step, LV_ANIM_ON);
    bsp_lvgl_unlock();
}

void companion_ui_level(unsigned level) { atomic_store(&audio_level, level > 100 ? 100 : level); }
