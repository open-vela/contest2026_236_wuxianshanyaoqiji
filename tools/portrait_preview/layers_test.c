#include "qiji_sprite.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static uint8_t pixels[240*320*3];
static void flush(lv_display_t *display, const lv_area_t *area, uint8_t *map)
{ (void)area; (void)map; lv_display_flush_ready(display); }

static unsigned head_pixels(lv_display_t *display)
{
    lv_refr_now(display);
    unsigned bright = 0;
    for (int y = 30; y < 125; y++) for (int x = 60; x < 180; x++) {
        unsigned at = (y*240+x)*3;
        if (pixels[at] > 100 && pixels[at+1] > 100 && pixels[at+2] > 100) bright++;
    }
    return bright;
}

static lv_obj_t *part(lv_obj_t *rig, const char *name)
{
    for (unsigned i = 0; i < lv_obj_get_child_count(rig); i++) {
        lv_obj_t *obj = lv_obj_get_child(rig, i);
        const char *src = lv_obj_get_user_data(obj);
        if (src && !strcmp(src, name)) return obj;
    }
    return NULL;
}

int main(void)
{
    lv_init();
    lv_display_t *display = lv_display_create(240,320);
    lv_display_set_color_format(display,LV_COLOR_FORMAT_RGB888);
    lv_display_set_buffers(display,pixels,NULL,sizeof(pixels),LV_DISPLAY_RENDER_MODE_DIRECT);
    lv_display_set_flush_cb(display,flush);
    lv_obj_t *stage = lv_obj_create(lv_screen_active());
    lv_obj_remove_style_all(stage);
    lv_obj_set_pos(stage,0,0);
    lv_obj_set_size(stage,240,320);
    lv_obj_set_style_bg_color(stage,lv_color_hex(0x302c46),0);
    lv_obj_set_style_bg_opa(stage,LV_OPA_COVER,0);
    assert(qiji_sprite_create(stage,232,292));
#ifdef TEST_FALLBACK
    assert(lv_obj_get_child_count(stage) == 1);
    qiji_sprite_update(QIJI_LISTEN,0);
    assert(strstr(lv_image_get_src(lv_obj_get_child(stage,0)),"listen.bin"));
    puts("PASS: missing layers preserve the original sprite fallback");
#else
    assert(lv_obj_get_child_count(stage) == 2);
    lv_obj_t *rig = lv_obj_get_child(stage,0), *special = lv_obj_get_child(stage,1);
    assert(lv_obj_get_child_count(rig) == 12);
    qiji_sprite_update(QIJI_IDLE,0);
    assert(!lv_obj_has_flag(rig,LV_OBJ_FLAG_HIDDEN));
    unsigned rest = head_pixels(display);
    assert(rest > 4000);
    qiji_sprite_update(QIJI_IDLE,1600);
    /* Scanline-only decoding previously collapsed the rotated head into a
     * strip. Verify actual pixels, not just successful LVGL property calls. */
    assert(head_pixels(display) > rest * 8 / 10);
    qiji_sprite_update(QIJI_IDLE,3250);
    assert(part(rig,"eye_closed_l") && part(rig,"eye_closed_r"));
    qiji_sprite_update(QIJI_IDLE,3450);
    assert(part(rig,"eye_l"));
    qiji_sprite_reply("辛苦了，别担心");
    qiji_sprite_update(QIJI_REPLY,3500);
    assert(lv_obj_has_flag(rig,LV_OBJ_FLAG_HIDDEN));
    assert(strstr(lv_image_get_src(special),"comfort.bin"));
    qiji_sprite_update(QIJI_REPLY,5200);
    assert(!lv_obj_has_flag(rig,LV_OBJ_FLAG_HIDDEN));
    qiji_sprite_speaking(true);
    qiji_sprite_audio_level(250);
    qiji_sprite_update(QIJI_REPLY,5300);
    assert(part(rig,"mouth_large"));
    qiji_sprite_audio_level(0);
    qiji_sprite_update(QIJI_REPLY,5350);
    assert(part(rig,"mouth_closed"));
    qiji_sprite_audio_level(50);
    qiji_sprite_update(QIJI_REPLY,5400);
    assert(part(rig,"mouth_small"));
    qiji_sprite_speaking(false);
    qiji_sprite_update(QIJI_REPLY,5450);
    assert(part(rig,"mouth_closed"));
    qiji_sprite_update(QIJI_ERROR,5500);
    assert(strstr(lv_image_get_src(special),"surprise.bin"));
    qiji_sprite_update(QIJI_ERROR,7150);
    assert(!lv_obj_has_flag(rig,LV_OBJ_FLAG_HIDDEN));
    qiji_sprite_update(QIJI_IDLE,UINT32_MAX-500);
    qiji_sprite_update(QIJI_ERROR,UINT32_MAX-400);
    qiji_sprite_update(QIJI_ERROR,1300);
    assert(!lv_obj_has_flag(rig,LV_OBJ_FLAG_HIDDEN));
    puts("PASS: 12 live layers, blinking, PCM mouth states, special return and tick wrap");
#endif
    lv_deinit();
}
