/* SPDX-License-Identifier: Apache-2.0 */
/* Expose the official agent's configuration commands to the ADB NSH shell.
 * Do not launch a second ai_agent instance to configure the running service.
 */
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <string.h>
#include "channels/cmd_llm.h"
#include "channels/cmd_voice.h"
#include "infra/config_store.h"
#include "voice/voice_asr.h"
#include "voice/voice_tts.h"
#include "voice/voice_channel.h"
#include "qiji_duet.h"

extern bool qiji_chat_is_ready(void);
extern int qiji_chat_submit(const char *text);
extern int qiji_chat_record(bool start);
extern int qiji_wifi_connect(const char *ssid, const char *password);
extern void qiji_chat_print_result(void);

/* The official test helper launches a detached pthread. NSH exits the builtin
 * task immediately, which kills its child threads. Keep diagnostics synchronous. */
static int qiji_test_asr(const char *path)
{
    FILE *f=fopen(path,"rb");
    if (!f) { puts("Cannot open PCM file"); return 1; }
    if (fseek(f,0,SEEK_END)) { fclose(f); return 1; }
    long len=ftell(f);
    if (len<=0 || len>320000 || len%2 || fseek(f,0,SEEK_SET)) { fclose(f); return 1; }
    unsigned char *pcm=malloc((size_t)len);
    if (!pcm) { fclose(f); return 1; }
    size_t got=fread(pcm,1,(size_t)len,f);fclose(f);
    char text[1024]={0};
    int ret=got==(size_t)len ? voice_asr_recognize(pcm,got,text,sizeof(text)) : -1;
    free(pcm);
    if (ret) printf("ASR test failed: %d\n",ret);
    else printf("ASR result: %s\n",text);
    return ret ? 1 : 0;
}

int qiji_config_main(int argc, char **argv)
{
    if (argc < 2) {
        puts("qiji_config status | ask <text> | set_llm <preset> <key>");
        puts("qiji_config set_volc_key <key> | set_volc_asr <app_id> <token> <cluster>");
        puts("qiji_config set_voice_asr <backend> | set_voice_tts <backend>");
        puts("qiji_config wifi <ssid> <password> | wifi_reconnect | result");
        puts("qiji_config record | stop  (same path as screen button)");
        puts("qiji_config model turbo|character  (reuse saved API key)");
        puts("qiji_config set_aliyun_asr <key> | test_asr <pcm_file> | voice_status");
        puts("qiji_config tts_voice <voice_id> | tts_style natural|cheerful|gentle");
        puts("qiji_config speak <text> | test_tts <text> <pcm_file>");
        puts("qiji_config duet <server_ipv4> <port> <pairing_token> | duet_off");
        return 1;
    }
    if (!strcmp(argv[1], "wifi") && argc == 4)
        return qiji_wifi_connect(argv[2], argv[3]) ? 1 : 0;
    if (!strcmp(argv[1], "duet") && argc == 5)
        return qiji_duet_configure(argv[2], argv[3], argv[4]) ? 1 : 0;
    if (!strcmp(argv[1], "duet_off") && argc == 2)
        return qiji_duet_configure("", NULL, NULL) ? 1 : 0;
    if (!strcmp(argv[1], "wifi_reconnect") && argc == 2)
        return qiji_wifi_connect(NULL, NULL) ? 1 : 0;
    if (!strcmp(argv[1], "result") && argc == 2) {
        qiji_chat_print_result();
        return 0;
    }
    bool ready = qiji_chat_is_ready();
    if (!strcmp(argv[1], "status")) {
        puts(ready ? "AI Agent ready" : "AI Agent not ready");
        return ready ? 0 : 1;
    }
    if (!ready) {
        puts("Wait for the AI Agent to finish initialization.");
        return 1;
    }
    if ((!strcmp(argv[1], "record") || !strcmp(argv[1], "stop")) && argc == 2) {
        int rc = qiji_chat_record(!strcmp(argv[1], "record"));
        puts(rc ? "Record transition not accepted (busy or invalid state)" :
             "Record transition accepted; see device screen");
        return rc ? 1 : 0;
    }
    if (!strcmp(argv[1], "set_aliyun_asr") && argc == 3) {
        if (strlen(argv[2]) < 8 || strlen(argv[2]) >= 256 || strpbrk(argv[2], "\r\n")) return 1;
        if (claw_config_set("aliyun_asr_key", argv[2]) ||
            claw_config_set("qiji_asr_backend", "aliyun") ||
            voice_asr_set_backend("aliyun")) return 1;
        puts("Aliyun ASR configured; key hidden.");
        return 0;
    }
    if (!strcmp(argv[1], "test_asr") && argc == 3)
        return qiji_test_asr(argv[2]);
    if (!strcmp(argv[1], "voice_status") && argc == 2) {
        char key[256]={0};
        bool present=!claw_config_get("aliyun_asr_key",key,sizeof(key)) && *key;
        memset(key,0,sizeof(key));
        printf("ASR=%s TTS=%s AliyunKey=%s clock=%s\n",voice_asr_get_backend(),
            voice_tts_get_backend(),present ? "configured" : "missing",
            time(NULL)>=1767225600 ? "set" : "not_set");
        return 0;
    }
    if (!strcmp(argv[1], "speak") && argc == 3)
        return voice_channel_speak(argv[2]) ? 1 : 0;
    if (!strcmp(argv[1], "test_tts") && argc == 4)
        return voice_channel_test_tts(argv[2], argv[3]) ? 1 : 0;
    if (!strcmp(argv[1], "tts_voice") && argc == 3) {
        if (!*argv[2] || strlen(argv[2]) >= 96) return 1;
        return claw_config_set("qiji_tts_voice", argv[2]) ? 1 : 0;
    }
    if (!strcmp(argv[1], "tts_style") && argc == 3) {
        const char *instruction = !strcmp(argv[2], "natural") ? "用自然、亲切的年轻女性声音说话，语气轻快，略带笑意，情绪适度，像朋友聊天。" :
            !strcmp(argv[2], "cheerful") ? "用开心、轻快的年轻女性声音说话，带着笑意，表达自然，不要夸张。" :
            !strcmp(argv[2], "gentle") ? "用温柔、关切的年轻女性声音说话，语速稍慢，轻声安慰，表达自然。" : NULL;
        if (!instruction) return 1;
        return claw_config_set("qiji_tts_instruction", instruction) ? 1 : 0;
    }
    if (!strcmp(argv[1], "model") && argc == 3) {
        const char *model = !strcmp(argv[2], "turbo") ? "doubao-seed-2-1-turbo-260628" :
            !strcmp(argv[2], "character") ? "doubao-seed-character-260628" : NULL;
        if (!model) { puts("Choose turbo or character"); return 1; }
        char *args[] = {"set_llm", "https://ark.cn-beijing.volces.com/api/v3/chat/completions", (char *)model};
        cmd_set_llm(3, args);
        return 0;
    }
    if (!strcmp(argv[1], "ask") && argc == 3) {
        int rc = qiji_chat_submit(argv[2]);
        puts(rc ? "Request not accepted (busy or invalid text)" : "Request accepted; see device screen");
        return rc ? 1 : 0;
    }
    if (!strcmp(argv[1], "set_llm") && argc >= 4)
        cmd_set_llm(argc - 1, argv + 1);
    else if (!strcmp(argv[1], "set_volc_key") && argc == 3)
        cmd_set_volc_key(argc - 1, argv + 1);
    else if (!strcmp(argv[1], "set_volc_asr") && argc == 5)
        cmd_set_volc_asr(argc - 1, argv + 1);
    else if (!strcmp(argv[1], "set_volc_speaker") && argc == 3)
        cmd_set_volc_speaker(argc - 1, argv + 1);
    else if (!strcmp(argv[1], "set_voice_asr") && argc == 3) {
        cmd_set_voice_asr(argc - 1, argv + 1);
        const char *active = voice_asr_get_backend();
        if (!active || strcmp(active, argv[2])) return 1;
        return claw_config_set("qiji_asr_backend", active) ? 1 : 0;
    }
    else if (!strcmp(argv[1], "set_voice_tts") && argc == 3) {
        cmd_set_voice_tts(argc - 1, argv + 1);
        const char *active = voice_tts_get_backend();
        if (!active || strcmp(active, argv[2])) return 1;
        return claw_config_set("qiji_tts_backend", active) ? 1 : 0;
    }
    else {
        puts("Unknown command or incorrect argument count; run qiji_config for usage.");
        return 1;
    }
    return 0;
}
