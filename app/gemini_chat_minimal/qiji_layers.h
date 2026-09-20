/* SPDX-License-Identifier: Apache-2.0 */
#ifndef QIJI_LAYERS_H
#define QIJI_LAYERS_H
#include "qiji_avatar.h"
bool qiji_layers_create(lv_obj_t *parent, int width, int height);
void qiji_layers_visible(bool visible);
void qiji_layers_update(qiji_avatar_state_t state, uint32_t tick, uint8_t level);
#endif
