#include <assert.h>
#include <string.h>
#include "config_line.h"

int main(void)
{
    const char *json = "{\"ssid\":\"test-network\",\"password\":\"test-only-password\","
        "\"host\":\"http://192.0.2.1:8765\",\"token\":\"0123456789abcdef0123456789abcdef\"}";
    /* Replay USB packet gaps at every possible boundary, including 64 bytes. */
    for (size_t gap = 0; gap <= strlen(json); ++gap) {
        config_line_t line = {0};
        for (size_t i = 0; i < strlen(json); ++i) {
            if (i == gap) {
                assert(config_line_feed(&line, EOF) == 0);
                assert(config_line_feed(&line, EOF) == 0);
            }
            assert(config_line_feed(&line, (unsigned char)json[i]) == 0);
        }
        assert(config_line_feed(&line, EOF) == 0);
        assert(config_line_feed(&line, '\n') == 1);
        assert(strcmp(line.text, json) == 0);
    }
    config_line_t line = {0};
    for (int i = 0; i < 639; ++i) assert(config_line_feed(&line, 'a') == 0);
    assert(config_line_feed(&line, '\n') == 1);
    assert(strlen(line.text) == 639);
    for (int i = 0; i < 700; ++i) assert(config_line_feed(&line, 'b') == 0);
    assert(config_line_feed(&line, '\n') == -1);
    assert(line.text[0] == 0);
    assert(config_line_feed(&line, '{') == 0);
    assert(config_line_feed(&line, 0) == 0);
    assert(config_line_feed(&line, '}') == 0);
    assert(config_line_feed(&line, '\n') == -1);
    assert(config_line_feed(&line, '{') == 0);
    assert(config_line_feed(&line, '}') == 0);
    assert(config_line_feed(&line, '\r') == 0);
    assert(config_line_feed(&line, '\n') == 1);
    assert(strcmp(line.text, "{}\r") == 0);
    puts("USB configuration framing: PASS");
    return 0;
}
