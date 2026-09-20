/* SPDX-License-Identifier: Apache-2.0 */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    char text[640];
    size_t used;
    bool rejected;
} config_line_t;

/* Nonblocking USB reads can end between any two bytes, including inside JSON.
 * Keep the frame until LF; reject an entire oversized/binary frame. */
static inline int config_line_feed(config_line_t *line, int ch)
{
    if (ch == EOF) return 0;
    if (ch == '\n') {
        int result = line->rejected ? -1 : 1;
        line->text[line->used] = '\0';
        line->used = 0;
        line->rejected = false;
        return result;
    }
    if (line->rejected) return 0;
    if (ch == 0 || line->used == sizeof(line->text) - 1) {
        memset(line->text, 0, sizeof(line->text));
        line->used = 0;
        line->rejected = true;
        return 0;
    }
    line->text[line->used++] = (char)ch;
    return 0;
}
