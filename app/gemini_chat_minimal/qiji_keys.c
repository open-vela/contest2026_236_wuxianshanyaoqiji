/* SPDX-License-Identifier: Apache-2.0 */
#include <nuttx/config.h>
#include <nuttx/input/buttons.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include "qiji_keys.h"
#include "qiji_key_filter.h"

extern int qiji_chat_toggle(void);
static int button_fd = -1;
static qiji_key_filter_t filter;

void qiji_keys_init(void)
{
    button_fd = open("/dev/input/event1", O_RDONLY | O_NONBLOCK);
    if (button_fd < 0) perror("qiji_chat: ENTER button unavailable");
    else puts("qiji_chat: ENTER=0x08 on /dev/input/event1");
}

void qiji_keys_poll(uint32_t tick)
{
    if (button_fd < 0) return;
    btn_buttonset_t buttons;
    if (read(button_fd, &buttons, sizeof(buttons)) != sizeof(buttons)) {
        filter = (qiji_key_filter_t){0};
        return;
    }
    if (qiji_key_sample(&filter, buttons, tick)) {
        int rc = qiji_chat_toggle();
        printf("qiji_chat: ENTER %s\n", rc ? "ignored (busy/not ready)" : "accepted");
    }
}
