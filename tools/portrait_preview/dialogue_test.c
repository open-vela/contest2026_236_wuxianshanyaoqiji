/* SPDX-License-Identifier: Apache-2.0 */
#include "../../app/gemini_chat_minimal/qiji_dialogue_text.h"
#include <assert.h>
#include <string.h>
int main(void)
{
    char text[128];
    qiji_dialogue_text(text, sizeof(text), "谢谢制作人。（脸颊发烫，下意识攥紧衣角）我会努力的。");
    assert(!strcmp(text, "谢谢制作人。我会努力的。"));
    qiji_dialogue_text(text, sizeof(text), "诶（抬手(又放下)）？嘿嘿！");
    assert(!strcmp(text, "诶？嘿嘿！"));
    qiji_dialogue_text(text, sizeof(text), "好呀（未闭合动作");
    assert(!strcmp(text, "好呀"));
    qiji_dialogue_text(text, sizeof(text), "琴音、Re;IRIS：15岁！");
    assert(!strcmp(text, "琴音、Re;IRIS：15岁！"));
    qiji_dialogue_text(text, 5, "藤田琴音");
    assert(!strcmp(text, "藤"));
    qiji_dialogue_text(text, 1, "藤");
    assert(!*text);
    qiji_dialogue_text(text, sizeof(text), NULL);
    assert(!*text);
    qiji_dialogue_text(NULL, 0, "x");
    return 0;
}
