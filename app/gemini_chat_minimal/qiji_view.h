/* SPDX-License-Identifier: Apache-2.0 */
#ifndef QIJI_VIEW_H
#define QIJI_VIEW_H
#include "qiji_avatar.h"
/* All calls belong to the LVGL UI thread. Also used by the host preview. */
lv_obj_t *qiji_view_create(lv_obj_t *screen, int width, int height,
                           const char *font_path);
void qiji_view_audio(bool playing, uint32_t played_ms, uint32_t duration_ms);
void qiji_view_update(bool wifi, bool ready, bool busy, bool recording,
                      qiji_avatar_state_t state, const char *status,
                      const char *question, const char *answer,
                      bool changed, uint32_t tick);
#endif
