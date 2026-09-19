/* SPDX-License-Identifier: Apache-2.0 */
#ifndef QIJI_AVATAR_H
#define QIJI_AVATAR_H
#include <lvgl/lvgl.h>
typedef enum {
    QIJI_IDLE, QIJI_LISTEN, QIJI_THINK, QIJI_REPLY, QIJI_ERROR
} qiji_avatar_state_t;
void qiji_avatar_create(lv_obj_t *parent, int x, int y, int width, int height);
/* UI thread only. elapsed_ms uses LVGL's monotonic tick. */
void qiji_avatar_update(qiji_avatar_state_t state, uint32_t elapsed_ms);
#endif
