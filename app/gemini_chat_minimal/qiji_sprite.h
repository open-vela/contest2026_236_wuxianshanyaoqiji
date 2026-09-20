/* SPDX-License-Identifier: Apache-2.0 */
#ifndef QIJI_SPRITE_H
#define QIJI_SPRITE_H
#include "qiji_avatar.h"
bool qiji_sprite_create(lv_obj_t *stage, int width, int height);
void qiji_sprite_update(qiji_avatar_state_t state, uint32_t tick);
void qiji_sprite_speaking(bool speaking);
void qiji_sprite_audio_level(uint8_t level);
void qiji_sprite_reply(const char *text);
#endif
