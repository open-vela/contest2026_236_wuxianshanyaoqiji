/* SPDX-License-Identifier: Apache-2.0 */
#ifndef QIJI_AUDIO_ENVELOPE_H
#define QIJI_AUDIO_ENVELOPE_H
#include <stdint.h>
#include <stddef.h>
#include <string.h>

/* 40ms windows of the accepted 24kHz mono s16le TTS stream. Caller locks.
 * 4KB ring holds 163 seconds ahead of the estimated playback position. */
#define QIJI_ENV_SAMPLES 960
#define QIJI_ENV_BINS 4096
typedef struct {
    uint8_t bins[QIJI_ENV_BINS];
    uint64_t windows;
    uint32_t sum;
    unsigned samples;
    uint8_t low_byte;
    int pending;
} qiji_audio_envelope_t;

static inline uint8_t qiji_envelope_level(uint32_t sum, unsigned samples)
{
    uint32_t mean = samples ? sum / samples : 0;
    if (mean <= 180) return 0;
    unsigned level = (mean - 180) * 255 / 8000;
    return level > 255 ? 255 : level;
}

static inline void qiji_envelope_reset(qiji_audio_envelope_t *e)
{ memset(e, 0, sizeof(*e)); }

static inline void qiji_envelope_push(qiji_audio_envelope_t *e,
                                      const uint8_t *pcm, size_t bytes)
{
    for (size_t i = 0; i < bytes; i++) {
        if (!e->pending) { e->low_byte = pcm[i]; e->pending = 1; continue; }
        int sample = e->low_byte | ((unsigned)pcm[i] << 8);
        if (sample >= 32768) sample -= 65536;
        e->pending = 0;
        e->sum += sample < 0 ? -sample : sample;
        if (++e->samples == QIJI_ENV_SAMPLES) {
            e->bins[e->windows++ % QIJI_ENV_BINS] = qiji_envelope_level(e->sum, e->samples);
            e->sum = e->samples = 0;
        }
    }
}

static inline uint8_t qiji_envelope_at(const qiji_audio_envelope_t *e, uint32_t ms)
{
    uint64_t window = ms / 40;
    if (window == e->windows) return qiji_envelope_level(e->sum, e->samples);
    if (window > e->windows || e->windows - window > QIJI_ENV_BINS) return 0;
    return e->bins[window % QIJI_ENV_BINS];
}
#endif
