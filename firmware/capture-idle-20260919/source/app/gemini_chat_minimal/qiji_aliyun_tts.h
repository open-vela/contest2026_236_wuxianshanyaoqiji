/* SPDX-License-Identifier: Apache-2.0 */
#pragma once
#include "voice/voice_tts.h"
void qiji_aliyun_tts_register(void);
/* PCM16 mono 24 kHz, matching the official streaming playback channel. */
int qiji_aliyun_tts_stream(const char *text, voice_tts_chunk_cb cb, void *user);
