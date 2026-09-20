/* Bounds, axes and corner mapping for the actual header copied to TPADC. */
#include "../portrait_touch.h"
#include <stdio.h>
#define CHECK(expr) do { if (!(expr)) { fprintf(stderr, "Failed: %s\n", #expr); return 1; } } while (0)
int main(void)
{
    uint16_t x, y, previous_x = 0, previous_y = 0;
    qiji_touch_portrait(100, 100, 100, 3900, 100, 3900, &x, &y);
    CHECK(x == 0 && y == 0);
    qiji_touch_portrait(3900, 100, 100, 3900, 100, 3900, &x, &y);
    CHECK(x == 239 && y == 0);
    qiji_touch_portrait(100, 3900, 100, 3900, 100, 3900, &x, &y);
    CHECK(x == 0 && y == 319);
    qiji_touch_portrait(3900, 3900, 100, 3900, 100, 3900, &x, &y);
    CHECK(x == 239 && y == 319);
    for (unsigned raw = 0; raw <= 65535; raw++) {
        qiji_touch_portrait(raw, raw, 100, 3900, 100, 3900, &x, &y);
        CHECK(x < 240 && y < 320 && x >= previous_x && y >= previous_y);
        previous_x = x; previous_y = y;
    }
    /* Different calibrations catch accidentally swapped ADC axes. */
    qiji_touch_portrait(1000, 500, 500, 3500, 1000, 3000, &x, &y);
    CHECK(x == 0 && y == 0);
    qiji_touch_portrait(3000, 3500, 500, 3500, 1000, 3000, &x, &y);
    CHECK(x == 239 && y == 319);
    CHECK(qiji_touch_axis(500, 100, 100, 240) == 0);
    CHECK(qiji_touch_axis(500, 100, 3900, 0) == 0);
    puts("PASS: portrait corners, clamping, monotonic axes and calibration");
    return 0;
}
