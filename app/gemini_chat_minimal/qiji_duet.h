/* SPDX-License-Identifier: Apache-2.0 */
#pragma once
#include <stdbool.h>
void qiji_duet_start(void);
bool qiji_duet_active(void);
void qiji_duet_stop(void);
int qiji_duet_configure(const char *ip, const char *port, const char *token);
int qiji_chat_duet_present(const char *text, bool speak, bool summary, const char *speaker);
int qiji_chat_duet_result(void);
bool qiji_chat_duet_ready(void);
