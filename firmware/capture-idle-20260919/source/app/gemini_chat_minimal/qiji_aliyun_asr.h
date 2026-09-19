/* SPDX-License-Identifier: Apache-2.0 */
#pragma once
#include <stddef.h>
void qiji_aliyun_register(void);
void *qiji_aliyun_open(void);
int qiji_aliyun_send(void *session, const unsigned char *pcm, size_t len);
int qiji_aliyun_finish(void *session, char *text, size_t cap);
void qiji_aliyun_abort(void *session);
