/* SPDX-License-Identifier: Apache-2.0 */
/* Original procedural character: "Qiji / Lilac", a chibi girl.
 * Every layer is a local LVGL shape; no third-party character/model assets.
 * Native 96x104 artwork, clipped to a small stage to limit SPI redraw traffic.
 */
#include "qiji_avatar.h"

static lv_obj_t *figure, *eye_l, *eye_r, *mouth, *cheek_l, *cheek_r;
static lv_obj_t *orb, *dots[3], *shadow;
static int center_y;

static lv_obj_t *shape(lv_obj_t *parent, int x, int y, int w, int h,
                       int radius, uint32_t color)
{
    lv_obj_t *o = lv_obj_create(parent);
    lv_obj_remove_style_all(o);
    lv_obj_remove_flag(o, LV_OBJ_FLAG_CLICKABLE | LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_set_pos(o, x, y);
    lv_obj_set_size(o, w, h);
    lv_obj_set_style_radius(o, radius, 0);
    lv_obj_set_style_bg_color(o, lv_color_hex(color), 0);
    lv_obj_set_style_bg_opa(o, LV_OPA_COVER, 0);
    return o;
}

void qiji_avatar_create(lv_obj_t *parent, int x, int y, int width, int height)
{
    lv_obj_t *stage = shape(parent, x, y, width, height, 12, 0x302c46);
    shape(stage, 9, 17, 3, 3, 2, 0x8e7caa);
    shape(stage, width - 13, height - 24, 4, 4, 2, 0x8e7caa);
    center_y = (height - 104) / 2;
    shadow = shape(stage, (width - 56) / 2, center_y + 98, 56, 5, 3, 0x201e34);
    figure = lv_obj_create(stage);
    lv_obj_remove_style_all(figure);
    lv_obj_set_size(figure, 96, 104);
    lv_obj_set_pos(figure, (width - 96) / 2, center_y);
    lv_obj_remove_flag(figure, LV_OBJ_FLAG_CLICKABLE | LV_OBJ_FLAG_SCROLLABLE);
    /* Two-head-tall silhouette: bob hair, puff sleeves and a lilac dress. */
    shape(figure, 12, 8, 72, 66, 28, 0x372d48);
    shape(figure, 15, 10, 66, 61, 27, 0x766187);
    shape(figure, 31, 85, 12, 13, 4, 0xf5e8ed);
    shape(figure, 53, 85, 12, 13, 4, 0xf5e8ed);
    shape(figure, 27, 95, 17, 7, 4, 0x493953);
    shape(figure, 52, 95, 17, 7, 4, 0x493953);
    shape(figure, 26, 65, 44, 25, 9, 0x9d83be);
    shape(figure, 22, 81, 52, 11, 5, 0xc4a9de);
    shape(figure, 25, 89, 46, 4, 2, 0xffe9ef);
    shape(figure, 20, 65, 13, 17, 6, 0xffeef1);
    shape(figure, 63, 65, 13, 17, 6, 0xffeef1);
    shape(figure, 22, 78, 9, 9, 5, 0xffd9cb);
    shape(figure, 65, 78, 9, 9, 5, 0xffd9cb);
    shape(figure, 42, 59, 12, 12, 4, 0xffd9cb);
    shape(figure, 34, 65, 14, 9, 4, 0xffeef1);
    shape(figure, 48, 65, 14, 9, 4, 0xffeef1);
    shape(figure, 39, 70, 9, 7, 3, 0xcc7097);
    shape(figure, 48, 70, 9, 7, 3, 0xcc7097);
    shape(figure, 45, 71, 6, 7, 3, 0xf8bed1);
    /* Face and ears. Hair is drawn over the upper face as separate locks. */
    shape(figure, 15, 40, 10, 15, 5, 0xffd9cb);
    shape(figure, 71, 40, 10, 15, 5, 0xffd9cb);
    shape(figure, 20, 23, 56, 43, 21, 0xffecdf);
    shape(figure, 17, 15, 17, 43, 8, 0x766187);
    shape(figure, 66, 18, 13, 43, 6, 0x766187);
    shape(figure, 23, 12, 20, 24, 9, 0x9680a8);
    shape(figure, 39, 12, 19, 20, 8, 0x9680a8);
    shape(figure, 54, 15, 16, 20, 7, 0x9680a8);
    shape(figure, 25, 16, 10, 4, 2, 0xc1a8cb);
    shape(figure, 40, 15, 10, 3, 2, 0xc1a8cb);
    /* Large irises with two highlights, clipped by each blinking eye. */
    eye_l = shape(figure, 30, 39, 12, 16, 5, 0x49364f);
    eye_r = shape(figure, 55, 39, 12, 16, 5, 0x49364f);
    lv_obj_t *eyes[] = {eye_l, eye_r};
    for (int i = 0; i < 2; i++) {
        shape(eyes[i], 1, 3, 10, 12, 4, 0xfffaf6);
        shape(eyes[i], 3, 3, 8, 12, 4, 0x9574c0);
        shape(eyes[i], 5, 4, 4, 8, 2, 0x49364f);
        shape(eyes[i], 3, 3, 4, 4, 2, 0xffffff);
        shape(eyes[i], 8, 11, 2, 2, 1, 0xeed2ff);
    }
    cheek_l = shape(figure, 27, 55, 12, 4, 2, 0xf4b5c0);
    cheek_r = shape(figure, 59, 55, 12, 4, 2, 0xf4b5c0);
    mouth = shape(figure, 45, 57, 7, 3, 2, 0xc97991);
    /* Asymmetric petal clip; no borrowed character emblem. */
    shape(figure, 70, 24, 9, 6, 3, 0xffd3e4);
    shape(figure, 68, 28, 9, 6, 3, 0xffd3e4);
    orb = shape(figure, 72, 27, 5, 5, 3, 0xffdfa5);
    for (int i = 0; i < 3; i++)
        dots[i] = shape(figure, 36 + i * 10, 1, 4, 4, 2, 0xffd3e4);
    qiji_avatar_update(QIJI_IDLE, 0);
}

void qiji_avatar_update(qiji_avatar_state_t state, uint32_t tick)
{
    if (!figure) return;
    /* 3.2-second breathing, 140ms blink every 4.7 seconds. */
    uint32_t breath = tick % 3200;
    int rise = (breath < 1600 ? breath : 3200 - breath) / 530;
    lv_obj_set_y(figure, center_y - rise);
    bool blink = tick % 4700 > 4560;
    int eye_h = blink ? 2 : state == QIJI_REPLY ? 11 : 16;
    lv_obj_set_height(eye_l, eye_h);
    lv_obj_set_height(eye_r, eye_h);
    lv_obj_set_y(eye_l, 39 + (16 - eye_h) / 2);
    lv_obj_set_y(eye_r, 39 + (16 - eye_h) / 2);
    int look = state == QIJI_THINK ? 2 : 0;
    lv_obj_set_x(eye_l, 30 + look);
    lv_obj_set_x(eye_r, 55 + look);
    /* A text reply has a stable happy face, not fabricated audio lip-sync. */
    lv_obj_set_size(mouth, state == QIJI_REPLY ? 9 : 7,
                    state == QIJI_LISTEN ? 5 : state == QIJI_REPLY ? 5 : 2);
    lv_obj_set_style_bg_color(orb, lv_color_hex(state == QIJI_ERROR ? 0xf2a78c :
                                state == QIJI_LISTEN ? 0x9df5cf : 0xffd58e), 0);
    lv_obj_set_style_bg_opa(cheek_l, state == QIJI_REPLY ? LV_OPA_COVER : LV_OPA_60, 0);
    lv_obj_set_style_bg_opa(cheek_r, state == QIJI_REPLY ? LV_OPA_COVER : LV_OPA_60, 0);
    for (int i = 0; i < 3; i++) {
        if (state == QIJI_THINK) {
            lv_obj_remove_flag(dots[i], LV_OBJ_FLAG_HIDDEN);
            lv_obj_set_style_bg_opa(dots[i], (tick / 250) % 3 == (uint32_t)i ? LV_OPA_COVER : LV_OPA_30, 0);
        } else lv_obj_add_flag(dots[i], LV_OBJ_FLAG_HIDDEN);
    }
    lv_obj_set_style_bg_opa(shadow, rise > 1 ? LV_OPA_60 : LV_OPA_COVER, 0);
}
