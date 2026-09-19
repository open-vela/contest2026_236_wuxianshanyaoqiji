/* Render the actual firmware avatar code using the same official LVGL tree. */
#include "qiji_avatar.h"
#include <stdio.h>
#include <stdlib.h>
static unsigned char pixels[540 * 140 * 3];
static void flush(lv_display_t *d, const lv_area_t *area, uint8_t *map)
{
    (void)area; (void)map;
    lv_display_flush_ready(d);
}
int main(int argc, char **argv)
{
    if (argc < 2 || argc > 3) return 2;
    uint32_t tick = argc == 3 ? (uint32_t)strtoul(argv[2], NULL, 10) : 1200;
    lv_init();
    lv_display_t *d = lv_display_create(540, 140);
    lv_display_set_color_format(d, LV_COLOR_FORMAT_RGB888);
    lv_display_set_buffers(d, pixels, NULL, sizeof(pixels), LV_DISPLAY_RENDER_MODE_DIRECT);
    lv_display_set_flush_cb(d, flush);
    lv_obj_t *s = lv_screen_active();
    lv_obj_set_style_bg_color(s, lv_color_hex(0x14243a), 0);
    const char *names[] = {"IDLE", "LISTEN", "THINK", "REPLY", "ERROR"};
    for (int i = 0; i < 5; i++) {
        lv_obj_t *label = lv_label_create(s);
        lv_label_set_text(label, names[i]);
        lv_obj_set_style_text_color(label, lv_color_hex(0xf3f7ff), 0);
        lv_obj_set_pos(label, i * 108 + 18, 4);
        qiji_avatar_create(s, i * 108 + 2, 25, 104, 106);
        qiji_avatar_update((qiji_avatar_state_t)i, tick);
    }
    lv_refr_now(d);
    FILE *f = fopen(argv[1], "wb");
    if (!f) return 1;
    fprintf(f, "P6\n540 140\n255\n");
    for (size_t i = 0; i < sizeof(pixels); i += 3) {
        fputc(pixels[i + 2], f); fputc(pixels[i + 1], f); fputc(pixels[i], f);
    }
    fclose(f);
    return 0;
}
