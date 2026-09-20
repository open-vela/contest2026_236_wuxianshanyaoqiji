/* SPDX-License-Identifier: Apache-2.0 */
#ifndef QIJI_SCROLL_H
#define QIJI_SCROLL_H
#include <stdbool.h>
#include <stdint.h>
typedef struct {
    uint32_t tick, hold;
    uint64_t offset_milli;
    bool initialized, reached_end;
} qiji_scroll_t;

/* Duration-relative reading aid, not word-level alignment. Move at most
 * 14px/s during playback; after playback allow a slow reread with end pause. */
static inline int qiji_scroll_step(qiji_scroll_t *s, uint32_t tick,
    int overflow, bool playing, bool waiting_audio, uint32_t played_ms,
    uint32_t duration_ms)
{
    if (!s->initialized) { s->tick = tick; s->hold = tick; s->initialized = true; }
    uint32_t dt = tick - s->tick;
    s->tick = tick;
    if (dt > 250) dt = 250; /* never jump after a stalled UI */
    if (overflow <= 0) { s->offset_milli = 0; return 0; }
    uint64_t max = (uint64_t)overflow * 1000;
    if (playing) {
        if (duration_ms < 2000) duration_ms = 2000;
        uint64_t target = max * played_ms / duration_ms;
        if (target > max) target = max;
        if (target > s->offset_milli) {
            uint64_t step = (uint64_t)dt * 14;
            if (step > target - s->offset_milli) step = target - s->offset_milli;
            s->offset_milli += step;
        }
        s->hold = tick;
        s->reached_end = s->offset_milli >= max;
    } else if (!waiting_audio && tick - s->hold >= 2200) {
        if (s->offset_milli < max) {
            s->offset_milli += (uint64_t)dt * 7;
            if (s->offset_milli >= max) {
                s->offset_milli = max;
                s->reached_end = true;
                s->hold = tick;
            }
        } else if (s->reached_end && tick - s->hold >= 4500) {
            s->offset_milli = 0;
            s->reached_end = false;
            s->hold = tick;
        }
    }
    if (s->offset_milli > max) s->offset_milli = max;
    return (int)(s->offset_milli / 1000);
}
#endif
