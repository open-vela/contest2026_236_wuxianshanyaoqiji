/* Exercise the exact firmware backend against the real service on Linux.
 * Supply API key through stdin; it never appears in argv or source files. */
#include "voice/voice_asr.h"
#include "qiji_aliyun_asr.h"
#include "qiji_aliyun_tts.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <syslog.h>
#include <unistd.h>
static char key[256];
int agent_secure_random(void *out, size_t len)
{ return getrandom(out,len,0)==(ssize_t)len ? 0 : -1; }
int claw_config_get(const char *name,char *out,size_t cap)
{
    const char *value=NULL;
    if (!strcmp(name,"qiji_tts_voice")) value=getenv("QIJI_TTS_VOICE");
    if (!strcmp(name,"qiji_tts_instruction")) value=getenv("QIJI_TTS_INSTRUCTION");
    if (value && strlen(value)<cap) { strcpy(out,value); return 0; }
    if (strcmp(name,"aliyun_asr_key")) return -1;
    if (strlen(key)>=cap) return -1;
    strcpy(out,key); return 0;
}
int voice_asr_register(const voice_asr_ops_t *ops) { (void)ops; return 0; }
int voice_asr_set_backend(const char *name) { (void)name; return 0; }
int voice_tts_register(const voice_tts_ops_t *ops) { (void)ops; return 0; }
int voice_tts_set_backend(const char *name) { (void)name; return 0; }
static int output_error;
static void output_pcm(const unsigned char *pcm,size_t len,int last,void *user)
{
    (void)last;
    if (len && fwrite(pcm,1,len,user)!=len) output_error=1;
}
int main(int argc,char **argv)
{
    openlog("qiji-asr-host",LOG_PERROR,LOG_USER);
    if ((argc!=2 && argc!=4) || !fgets(key,sizeof(key),stdin)) return 2;
    key[strcspn(key,"\r\n")]=0;
    if (argc==4 && !strcmp(argv[1],"tts")) {
        FILE *out=fopen(argv[3],"wb");
        if (!out) return 2;
        int r=qiji_aliyun_tts_stream(argv[2],output_pcm,out);
        if (fclose(out)) output_error=1;
        memset(key,0,sizeof(key));
        return r || output_error ? 1 : 0;
    }
    if (argc!=2) return 2;
    FILE *pcm=fopen(argv[1],"rb");
    if (!pcm) return 2;
    void *s=qiji_aliyun_open();
    if (!s) { fclose(pcm); return 1; }
    unsigned char chunk[3200];
    size_t n; int ret=0;
    while ((n=fread(chunk,1,sizeof(chunk),pcm))) {
        ret=qiji_aliyun_send(s,chunk,n);
        if (ret) break;
        usleep(100000);
    }
    fclose(pcm);
    char text[2048];
    if (ret) qiji_aliyun_abort(s);
    else ret=qiji_aliyun_finish(s,text,sizeof(text));
    if (!ret) printf("Recognized: %s\n",text);
    memset(key,0,sizeof(key));
    return ret ? 1 : 0;
}
