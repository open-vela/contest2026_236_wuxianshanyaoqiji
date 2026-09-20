/* SPDX-License-Identifier: Apache-2.0 */
#include "qiji_layers.h"
#include "qiji_layer_assets.h"
#include <stdio.h>
#include <string.h>

#ifndef QIJI_LAYER_DIR
#define QIJI_LAYER_DIR "/resource/qiji/kotone/layers"
#endif
#define LAYERS 12
#define ASSETS 16
static lv_obj_t *root, *parts[LAYERS];
static char paths[ASSETS][256];
static lv_image_dsc_t images[ASSETS];
static unsigned eye_variant, mouth_variant, smoothed;

static void free_images(void)
{
    for (int i = 0; i < ASSETS; i++) {
        if (images[i].data) lv_free((void *)images[i].data);
        memset(&images[i], 0, sizeof(images[i]));
    }
}

static void deleted(lv_event_t *e)
{
    (void)e;
    for (int i = 0; i < ASSETS; i++) lv_image_cache_drop(&images[i]);
    free_images();
    root = NULL;
}

static void set_asset(int part, int asset)
{
    lv_image_set_src(parts[part], &images[asset]);
    lv_obj_set_user_data(parts[part], (void *)qiji_layer_assets[asset].name);
}

static int wave(uint32_t tick, uint32_t period, int amplitude)
{
    int value = lv_trigo_sin((tick % period) * 360 / period) * amplitude;
    return (value + (value >= 0 ? 16384 : -16384)) / 32768;
}

bool qiji_layers_create(lv_obj_t *parent, int width, int height)
{
    if (root) lv_obj_delete(root);
    memset(parts, 0, sizeof(parts));
    smoothed = eye_variant = mouth_variant = 0;
    /* Validate the whole set before creating anything. Corrupt/missing art
     * falls back to the original eight sprites, never a half-built face. */
    for (int i = 0; i < ASSETS; i++) {
        snprintf(paths[i], sizeof(paths[i]), "%s/%s.bin", QIJI_LAYER_DIR, qiji_layer_assets[i].name);
        lv_image_header_t info;
        FILE *f = fopen(paths[i], "rb");
        if (!f) { free_images(); return false; }
        int seek_ok = fseek(f, 0, SEEK_END);
        long bytes = ftell(f);
        if (seek_ok || bytes != 12L + qiji_layer_assets[i].w * qiji_layer_assets[i].h * 4L) {
            fclose(f); free_images(); return false;
        }
        if (lv_image_decoder_get_info(paths[i], &info) != LV_RESULT_OK ||
            info.w != qiji_layer_assets[i].w || info.h != qiji_layer_assets[i].h ||
            info.cf != LV_COLOR_FORMAT_ARGB8888) {
            fclose(f); free_images(); return false;
        }
        /* Rotation needs a complete buffer. The pinned file decoder can
         * stream scanlines, which is valid only for untransformed images. */
        uint8_t *data = lv_malloc(bytes - 12);
        if (!data) { fclose(f); free_images(); return false; }
        fseek(f, 12, SEEK_SET);
        size_t got = fread(data, 1, bytes - 12, f);
        fclose(f);
        if (got != (size_t)bytes - 12) { lv_free(data); free_images(); return false; }
        images[i].header = info;
        images[i].data_size = bytes - 12;
        images[i].data = data;
    }
    root = lv_obj_create(parent);
    lv_obj_add_event_cb(root, deleted, LV_EVENT_DELETE, NULL);
    lv_obj_remove_style_all(root);
    lv_obj_remove_flag(root, LV_OBJ_FLAG_CLICKABLE | LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(root, LV_OBJ_FLAG_OVERFLOW_VISIBLE);
    lv_obj_set_size(root, 176, 272);
    lv_obj_set_pos(root, (width - 176) / 2, (height - 272) / 2);
    for (int i = 0; i < LAYERS; i++) {
        parts[i] = lv_image_create(root);
        lv_obj_remove_flag(parts[i], LV_OBJ_FLAG_CLICKABLE);
        set_asset(i, i);
        lv_obj_set_pos(parts[i], qiji_layer_assets[i].x, qiji_layer_assets[i].y);
        lv_image_set_pivot(parts[i], qiji_layer_assets[i].px - qiji_layer_assets[i].x,
                                   qiji_layer_assets[i].py - qiji_layer_assets[i].y);
    }
    lv_obj_move_to_index(parts[4], 3); /* neck behind the collar */
    lv_obj_move_to_index(parts[8], 10); /* eyebrows over the fringe */
    return true;
}

void qiji_layers_visible(bool visible)
{
    if (!root) return;
    if (visible) lv_obj_remove_flag(root, LV_OBJ_FLAG_HIDDEN);
    else lv_obj_add_flag(root, LV_OBJ_FLAG_HIDDEN);
}

void qiji_layers_update(qiji_avatar_state_t state, uint32_t tick, uint8_t level)
{
    if (!root) return;
    int breath = (wave(tick, 3600, 2) + 2) / 2;
    int tilt = wave(tick, 6200, 12) + (state == QIJI_LISTEN ? -8 : 0);
    int nod = wave(tick + 500, 4400, 1);
    unsigned cycle = tick / 5300;
    uint32_t blink_at = 3200 + (cycle * 719 % 1400);
    uint32_t phase = tick % 5300;
    unsigned blink = (phase >= blink_at && phase < blink_at + 140) ||
        (cycle % 3 == 2 && phase >= blink_at + 260 && phase < blink_at + 360);
    if (blink != eye_variant) {
        set_asset(6, blink ? 12 : 6);
        set_asset(7, blink ? 13 : 7);
        eye_variant = blink;
    }
    /* Real silence closes immediately; voiced frames get a short release. */
    smoothed = !level ? 0 : level > smoothed ? level : (smoothed + level) / 2;
    unsigned mouth = smoothed > 115 ? 2 : smoothed > 18 ? 1 : 0;
    if (mouth != mouth_variant) {
        set_asset(9, mouth ? 13 + mouth : 9);
        mouth_variant = mouth;
    }
    for (int i = 0; i < LAYERS; i++) {
        int x = qiji_layer_assets[i].x, y = qiji_layer_assets[i].y;
        int angle = 0;
        bool head_part = i == 1 || i == 2 || (i >= 5 && i <= 10);
        if (i) y -= breath;
        if (head_part) {
            int dx = qiji_layer_assets[i].px - qiji_layer_assets[5].px;
            int dy = qiji_layer_assets[i].py - qiji_layer_assets[5].py;
            /* Small angle rigid parent transform, rounded to a display pixel.
             * tilt is tenths of a degree; 573 is approx 1800/pi. */
            x -= dy * tilt / 573;
            y += dx * tilt / 573 + nod;
            angle = tilt;
        }
        if (i == 1 || i == 2) angle += wave(tick + (i == 1 ? 450 : 650), 6200, 28);
        if (i == 10) angle += wave(tick + 230, 6200, 5);
        if ((i == 6 || i == 7) && !blink) x += wave(tick, 8100, 1);
        if (i == 8 && state == QIJI_THINK) y--;
        lv_obj_set_pos(parts[i], x, y);
        lv_image_set_rotation(parts[i], angle);
    }
}
