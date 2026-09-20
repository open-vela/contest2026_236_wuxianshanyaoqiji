/* SPDX-License-Identifier: Apache-2.0 */
/* Bitmap sprite player. Artwork provenance/licensing is recorded separately. */
#include "qiji_sprite.h"
#include "qiji_layers.h"
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#ifndef QIJI_SPRITE_DIR
#define QIJI_SPRITE_DIR "/resource/qiji/kotone"
#endif
static const char *names[] = {"idle", "blink", "listen", "think", "speak",
                              "happy", "comfort", "surprise"};
static char paths[8][256];
static bool available[8], talking, caring;
static lv_obj_t *sprite;
static int selected = -1, base_y;
static bool layered, special_pending;
static uint8_t audio_level;
static qiji_avatar_state_t previous_state;
static uint32_t special_since;
static int special = -1;

bool qiji_sprite_create(lv_obj_t *stage, int width, int height)
{
    for (int i = 0; i < 8; i++) {
        snprintf(paths[i], sizeof(paths[i]), "%s/%s.bin", QIJI_SPRITE_DIR, names[i]);
        available[i] = access(paths[i], R_OK) == 0;
    }
    layered = qiji_layers_create(stage, width, height);
    if (!available[0] && !layered) return false;
    sprite = lv_image_create(stage);
    lv_obj_remove_flag(sprite, LV_OBJ_FLAG_CLICKABLE);
    if (available[0]) lv_image_set_src(sprite, paths[0]);
    lv_obj_set_size(sprite, 176, 272);
    base_y = (height - 272) / 2;
    lv_obj_set_pos(sprite, (width - 176) / 2, base_y);
    selected = 0;
    previous_state = QIJI_IDLE;
    special = -1;
    special_pending = talking = caring = false;
    audio_level = 0;
    if (layered) lv_obj_add_flag(sprite, LV_OBJ_FLAG_HIDDEN);
    return true;
}

void qiji_sprite_speaking(bool value) { talking = value; }
void qiji_sprite_audio_level(uint8_t level) { audio_level = level; }

void qiji_sprite_reply(const char *text)
{
    if (!text) text = "";
    caring = strstr(text, "辛苦") || strstr(text, "难过") || strstr(text, "没关系") ||
             strstr(text, "别担心") || strstr(text, "陪着你");
    special_pending = true;
}

void qiji_sprite_update(qiji_avatar_state_t state, uint32_t tick)
{
    if (!sprite) return;
    if (layered) {
        if (state != previous_state) {
            special = -1;
            if (state == QIJI_ERROR) { special = 7; special_since = tick; }
            if (state == QIJI_REPLY) special_pending = true;
        }
        if (state == QIJI_REPLY && special_pending && !talking) {
            special = caring ? 6 : 5;
            special_since = tick;
            special_pending = false;
        }
        previous_state = state;
        /* Speech always returns to the rig to show amplitude-driven lips. */
        if (talking || (special >= 0 && tick - special_since >= 1600)) special = -1;
        bool show_special = special >= 0 && available[special];
        qiji_layers_visible(!show_special);
        if (!show_special) {
            lv_obj_add_flag(sprite, LV_OBJ_FLAG_HIDDEN);
            qiji_layers_update(state, tick, talking ? audio_level : 0);
            return;
        }
        lv_obj_remove_flag(sprite, LV_OBJ_FLAG_HIDDEN);
        if (selected != special) { lv_image_set_src(sprite, paths[special]); selected = special; }
        lv_obj_set_y(sprite, base_y);
        return;
    }
    int next = 0;
    if (talking) next = (tick / 260) % 2 ? 4 : 0;
    else if (state == QIJI_LISTEN) next = 2;
    else if (state == QIJI_THINK) next = 3;
    else if (state == QIJI_ERROR) next = 7;
    else if (state == QIJI_REPLY) next = caring ? 6 : 5;
    else if (tick % 4700 >= 4500) next = 1;
    if (!available[next]) next = 0;
    if (next != selected) {
        lv_image_set_src(sprite, paths[next]);
        selected = next;
    }
    uint32_t breath = tick % 3200;
    int rise = (breath < 1600 ? breath : 3200 - breath) / 650;
    lv_obj_set_y(sprite, base_y - rise);
}
