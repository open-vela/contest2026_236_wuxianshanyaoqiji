/* SPDX-License-Identifier: Apache-2.0 */
#ifndef QIJI_DIALOGUE_TEXT_H
#define QIJI_DIALOGUE_TEXT_H
#include <stddef.h>
#include <string.h>

/* This voice character requests spoken lines only. Models may still insert
 * parenthesized stage directions: omit them from both captions and speech.
 * Other punctuation and complete UTF-8 code points are preserved. */
static inline void qiji_dialogue_text(char *dst, size_t capacity, const char *src)
{
    size_t out = 0;
    unsigned depth = 0;
    if (!capacity) return;
    if (!src) src = "";
    while (*src) {
        size_t open = *src == '(' ? 1 : !strncmp(src, "（", 3) ? 3 : 0;
        size_t close = *src == ')' ? 1 : !strncmp(src, "）", 3) ? 3 : 0;
        if (open) { ++depth; src += open; continue; }
        if (close && depth) { --depth; src += close; continue; }
        unsigned char c = (unsigned char)*src;
        size_t width = c < 0x80 ? 1 : (c & 0xe0) == 0xc0 ? 2 :
                       (c & 0xf0) == 0xe0 ? 3 : (c & 0xf8) == 0xf0 ? 4 : 1;
        size_t valid = 1;
        while (valid < width && src[valid] &&
               ((unsigned char)src[valid] & 0xc0) == 0x80) ++valid;
        if (valid != width) width = 1;
        if (!depth) {
            if (out + width >= capacity) break;
            memcpy(dst + out, src, width);
            out += width;
        }
        src += width;
    }
    dst[out] = '\0';
}
#endif
