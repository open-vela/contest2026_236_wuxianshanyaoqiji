/* Behaviour tests: bounce, hold/repeat, busy consumption and tick wrap. */
#include "../../app/gemini_chat_minimal/qiji_key_filter.h"
#include <stdio.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "Failed: %s\n", #x); return 1; } } while (0)
int main(void)
{
    qiji_key_filter_t f = {0};
    CHECK(!qiji_key_sample(&f, 8, 0));
    CHECK(!qiji_key_sample(&f, 8, 100)); /* held during startup */
    CHECK(!qiji_key_sample(&f, 0, 110));
    CHECK(!qiji_key_sample(&f, 0, 150));
    CHECK(!qiji_key_sample(&f, 8, 200));
    CHECK(!qiji_key_sample(&f, 0, 210)); /* contact bounce */
    CHECK(!qiji_key_sample(&f, 8, 220));
    CHECK(!qiji_key_sample(&f, 8, 240));
    CHECK(qiji_key_sample(&f, 8, 260));
    CHECK(!qiji_key_sample(&f, 8, 10000)); /* no long-press repeat */
    CHECK(!qiji_key_sample(&f, 0, 10010));
    CHECK(!qiji_key_sample(&f, 8, 10020)); /* release bounce */
    CHECK(!qiji_key_sample(&f, 8, 10080));
    CHECK(!qiji_key_sample(&f, 0, 10100));
    CHECK(!qiji_key_sample(&f, 0, 10140));
    CHECK(!qiji_key_sample(&f, 8, 10200));
    CHECK(qiji_key_sample(&f, 8, 10240)); /* consumer may reject while busy */
    CHECK(!qiji_key_sample(&f, 8, 11000)); /* cannot trigger later when idle */
    CHECK(!qiji_key_sample(&f, 0, 12000));
    CHECK(!qiji_key_sample(&f, 0, 12040));
    CHECK(!qiji_key_sample(&f, 16, 12100));
    CHECK(!qiji_key_sample(&f, 16, 12140)); /* HOME must not record */
    CHECK(!qiji_key_sample(&f, 8, 12200));
    CHECK(!qiji_key_sample(&f, 8, 12240)); /* require release between keys */
    CHECK(!qiji_key_sample(&f, 0, UINT32_MAX - 100));
    CHECK(!qiji_key_sample(&f, 0, UINT32_MAX - 60));
    CHECK(!qiji_key_sample(&f, 8, UINT32_MAX - 20));
    CHECK(qiji_key_sample(&f, 8, 20));
    puts("PASS: ENTER debounce, startup hold, repeat suppression, busy consumption, other keys, tick wrap");
    return 0;
}
