/* SPDX-License-Identifier: Apache-2.0 */
#ifndef QIJI_LAYOUT_H
#define QIJI_LAYOUT_H
enum {
    QIJI_HEADER_HEIGHT = 20,
    QIJI_OUTER_GAP = 8,
    QIJI_INNER_GAP = 8,
    QIJI_CARD_RADIUS = 16,
    /* Nested bottom corners share the same centre. */
    QIJI_DIALOGUE_RADIUS = QIJI_CARD_RADIUS - QIJI_INNER_GAP,
    QIJI_DIALOGUE_HEIGHT = 88,
    QIJI_RECORD_SIZE = 32
};
#endif
