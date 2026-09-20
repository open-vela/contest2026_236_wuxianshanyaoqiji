/* SPDX-License-Identifier: Apache-2.0 */
#ifndef QIJI_KEY_FILTER_H
#define QIJI_KEY_FILTER_H
#include <stdbool.h>
#include <stdint.h>
/* Official factory_test: Home=0x10, Enter=0x08, Menu=0x04, Vol+=2, Vol-=1. */
#define QIJI_ENTER_MASK 0x08u
typedef struct {
    uint32_t candidate, since;
    bool initialized, armed;
} qiji_key_filter_t;

/* One action per stable press. Require a stable release even after boot or
 * a rejected busy press. Tick subtraction is safe across uint32 wraparound. */
static inline bool qiji_key_sample(qiji_key_filter_t *f, uint32_t mask, uint32_t tick)
{
    if (!f->initialized || f->candidate != mask) {
        f->initialized = true;
        f->candidate = mask;
        f->since = tick;
        return false;
    }
    if (tick - f->since < 40) return false;
    if (mask == 0) {
        f->armed = true;
        return false;
    }
    bool fire = f->armed && mask == QIJI_ENTER_MASK;
    f->armed = false;
    return fire;
}
#endif
