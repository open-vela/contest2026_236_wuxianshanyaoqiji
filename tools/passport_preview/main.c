/* Render the actual firmware UI and font. No device verification is implied. */
#include "lvgl.h"
#include "companion_ui.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
LV_FONT_DECLARE(companion_font);
static unsigned char pixels[240 * 320 * 3];
bool bsp_lvgl_lock(int timeout) { (void)timeout; return true; }
void bsp_lvgl_unlock(void) {}
static void flush(lv_display_t *d, const lv_area_t *a, uint8_t *p)
{ (void)a; (void)p; lv_display_flush_ready(d); }
int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    lv_init();
    lv_display_t *d = lv_display_create(240, 320);
    lv_display_set_color_format(d, LV_COLOR_FORMAT_RGB888);
    lv_display_set_buffers(d, pixels, NULL, sizeof(pixels), LV_DISPLAY_RENDER_MODE_DIRECT);
    lv_display_set_flush_cb(d, flush);
    companion_ui_init(); companion_ui_battery(86);
    lv_font_glyph_dsc_t glyph = {0};
    for (unsigned c = 0x4e00; c <= 0x9fef; ++c)
        assert(lv_font_get_glyph_dsc(&companion_font, &glyph, c, 0) && !glyph.is_placeholder);
    assert(!lv_font_get_glyph_dsc(&companion_font, &glyph, 0x1f9ff, 0) || glyph.is_placeholder);
    companion_ui_message("在听伙伴说话", "藤田琴音", "小澄，今天我们给主人准备两个轻松休息的小点子吧。");
    for (int i = 0; i < 60; ++i) {
        if (i == 20) companion_ui_message("轮到小澄说话", "小澄", "可以听一首喜欢的歌，或者安静看看窗外。让主人自己选，好吗？");
        if (i == 45) companion_ui_message("给主人：本轮小结", "共同整理", "主人，我们准备了两个休息选项：听歌或看看窗外。你现在想聊天，还是想安静一会儿？");
        companion_ui_level(i >= 20 && i < 45 ? (i % 4) * 30 : 0);
        lv_tick_inc(100); lv_timer_handler(); lv_refr_now(d);
        char path[512]; snprintf(path, sizeof(path), "%s/%03d.ppm", argv[1], i);
        FILE *f = fopen(path, "wb"); if (!f) return 1;
        fprintf(f, "P6\n240 320\n255\n");
        for (unsigned j = 0; j < sizeof(pixels); j += 3) {
            fputc(pixels[j + 2], f); fputc(pixels[j + 1], f); fputc(pixels[j], f);
        }
        fclose(f);
    }
    puts("UI rendered; 20976 basic CJK glyphs present; negative glyph test passed.");
    return 0;
}
