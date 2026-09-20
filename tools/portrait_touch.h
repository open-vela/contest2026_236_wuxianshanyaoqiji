/* SPDX-License-Identifier: Apache-2.0 */
#ifndef QIJI_PORTRAIT_TOUCH_H
#define QIJI_PORTRAIT_TOUCH_H
#include <stdint.h>

/* ILI9341 landscape MADCTL=MV -> portrait MADCTL=MX:
 * (xp, yp) = (239 - yl, xl). TPADC's original yl reverses raw x.
 * Thus portrait X uses raw x/y calibration, Y uses raw y/x calibration.
 * Clamp before conversion; the original unsigned math wraps at the edges. */
static inline uint16_t qiji_touch_axis(uint16_t raw, uint16_t min,
                                       uint16_t max, uint16_t size)
{
    if (max <= min || size == 0 || raw <= min) return 0;
    if (raw >= max) return size - 1;
    return (uint32_t)(raw - min) * (size - 1) / (max - min);
}

static inline void qiji_touch_portrait(uint16_t raw_x, uint16_t raw_y,
    uint16_t x_min, uint16_t x_max, uint16_t y_min, uint16_t y_max,
    uint16_t *screen_x, uint16_t *screen_y)
{
    *screen_x = qiji_touch_axis(raw_x, y_min, y_max, 240);
    *screen_y = qiji_touch_axis(raw_y, x_min, x_max, 320);
}
#endif
