#pragma once
#include <stdbool.h>
void companion_ui_init(void);
void companion_ui_message(const char *state, const char *who, const char *text);
void companion_ui_battery(int percent);
void companion_ui_scroll(int delta);
void companion_ui_level(unsigned level);
