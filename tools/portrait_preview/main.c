/* Render the exact firmware view, official LVGL and MiSans font. */
#include "qiji_view.h"
#include "qiji_sprite.h"
#include <stdio.h>
#include <stdlib.h>
static unsigned char pixels[240 * 320 * 3];
static void flush(lv_display_t *d, const lv_area_t *area, uint8_t *map)
{
    (void)area; (void)map;
    lv_display_flush_ready(d);
}
int main(int argc, char **argv)
{
    if (argc < 3 || argc > 6) return 2;
    int state = argc >= 4 ? atoi(argv[3]) : QIJI_IDLE;
    uint32_t tick = argc >= 5 ? strtoul(argv[4], NULL, 10) : 1200;
    lv_init();
    lv_display_t *d = lv_display_create(240, 320);
    lv_display_set_color_format(d, LV_COLOR_FORMAT_RGB888);
    lv_display_set_buffers(d, pixels, NULL, sizeof(pixels), LV_DISPLAY_RENDER_MODE_DIRECT);
    lv_display_set_flush_cb(d, flush);
    qiji_view_create(lv_screen_active(), 240, 320, argv[2]);
    const char *status[] = {"准备就绪：按 ENTER 说话", "正在录音，再按 ENTER 结束",
        "正在等待模型回复…", "可以继续对话", "Wi-Fi 未连接，请先配置网络"};
    const char *question = state == QIJI_REPLY ? "今天有一点累，可以鼓励我吗？" : "";
    const char *answer = state == QIJI_REPLY ?
        "辛苦啦，今天也很努力呢！先放松一下肩膀，喝一口水。\n不用急着把所有事情做完，休息也是前进的一部分。\n我会陪着你，一起慢慢来。" : "";
    if (state < 0 || state > QIJI_ERROR) return 2;
    for (uint32_t t = 0; t <= tick; t += 50) {
        bool speaking = state == QIJI_REPLY && t >= 1500 && t < 22000;
        qiji_view_audio(speaking, speaking ? t - 1500 : 0, 20500);
        /* Preview-only synthetic level. Firmware uses accepted PCM windows. */
        qiji_sprite_audio_level(speaking ? ((t / 200) % 3) * 90 : 0);
        qiji_view_update(state != QIJI_ERROR, true, state == QIJI_THINK,
            state == QIJI_LISTEN, state, status[state], question, answer, t == 0, t);
        lv_refr_now(d);
        if (argc == 6 && t % 100 == 0) {
            char frame_path[512];
            snprintf(frame_path, sizeof(frame_path), "%s/%05u.ppm", argv[5], t);
            FILE *frame = fopen(frame_path, "wb");
            if (!frame) return 1;
            fprintf(frame, "P6\n240 320\n255\n");
            for (size_t i = 0; i < sizeof(pixels); i += 3) {
                fputc(pixels[i+2], frame); fputc(pixels[i+1], frame); fputc(pixels[i], frame);
            }
            fclose(frame);
        }
    }
    FILE *f = fopen(argv[1], "wb");
    if (!f) return 1;
    fprintf(f, "P6\n240 320\n255\n");
    for (size_t i = 0; i < sizeof(pixels); i += 3) {
        fputc(pixels[i + 2], f); fputc(pixels[i + 1], f); fputc(pixels[i], f);
    }
    fclose(f);
    return 0;
}
