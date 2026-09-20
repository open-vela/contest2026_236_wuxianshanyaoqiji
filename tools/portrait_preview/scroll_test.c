#include "../../app/gemini_chat_minimal/qiji_scroll.h"
#include <stdio.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "Failed: %s\n", #x); return 1; } } while (0)
int main(void)
{
    qiji_scroll_t s = {0};
    for (unsigned t = 0; t < 10000; t += 100)
        CHECK(qiji_scroll_step(&s,t,180,false,true,0,0)==0); /* wait for PCM */
    int previous = 0;
    for (unsigned t = 10000; t < 30000; t += 100) {
        int offset = qiji_scroll_step(&s,t,180,true,false,t-10000,20000);
        CHECK(offset>=previous && offset<=180 && offset-previous<=2);
        previous=offset;
    }
    CHECK(previous>=170);
    int offset=qiji_scroll_step(&s,30100,180,true,false,20000,60000);
    CHECK(offset>=previous); /* late duration must not rewind */
    offset=qiji_scroll_step(&s,1000000,180,true,false,60000,60000);
    CHECK(offset-previous<=4); /* stalled UI cannot jump */
    CHECK(qiji_scroll_step(&s,1000100,-5,false,false,0,0)==0);
    puts("PASS: waiting, smooth monotonic speech scroll, late duration, stalled UI, short text");
    return 0;
}
