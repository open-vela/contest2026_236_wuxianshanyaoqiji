/* SPDX-License-Identifier: Apache-2.0 */
/* Paraformer WSS client. One caller owns a session; no concurrent TLS access.
 * All waits use a monotonic deadline. Credentials never enter diagnostics.
 */
#include "qiji_aliyun_asr.h"
#include "qiji_aliyun_ca.h"
#include "voice/voice_asr.h"
#include "voice/voice_tts.h"
#include "qiji_aliyun_tts.h"
#include "infra/config_store.h"
#include "agent_compat.h"
#include "cJSON.h"
#include "mbedtls/base64.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/net_sockets.h"
#include "mbedtls/sha1.h"
#include "mbedtls/ssl.h"
#include "mbedtls/x509_crt.h"
#include <errno.h>
#include <fcntl.h>
#include <netdb.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/socket.h>
#include <syslog.h>
#include <time.h>
#include <unistd.h>

#define HOST "dashscope.aliyuncs.com"
#define PATH "/api-ws/v1/inference"
#define EVENT_CAP 16384
typedef struct {
    mbedtls_ssl_context ssl;
    mbedtls_ssl_config conf;
    mbedtls_net_context net;
    mbedtls_ctr_drbg_context rng;
    mbedtls_x509_crt ca;
    int64_t deadline, expires;
    int started, finished, error, message_opcode;
    size_t message_len;
    int pcm_pending;
    unsigned char pcm_byte;
    char id[37], result[2048];
    int last_begin;
    size_t last_offset;
    unsigned char message[EVENT_CAP];
} session_t;

static int64_t now_ms(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (int64_t)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}
static int entropy(void *unused, unsigned char *out, size_t len)
{ (void)unused; return agent_secure_random(out, len); }

static int wait_io(session_t *s, int code)
{
    int64_t remaining = s->deadline - now_ms();
    if (remaining <= 0) return -ETIMEDOUT;
    struct pollfd p = { .fd=s->net.fd,
        .events=code == MBEDTLS_ERR_SSL_WANT_WRITE ? POLLOUT : POLLIN };
    int r;
    do { r = poll(&p, 1, (int)remaining); } while (r < 0 && errno == EINTR && now_ms() < s->deadline);
    return r > 0 ? 0 : r == 0 ? -ETIMEDOUT : -EIO;
}
static int connect_tcp(session_t *s)
{
    struct addrinfo hints={0}, *list=NULL;
    hints.ai_family=AF_INET; hints.ai_socktype=SOCK_STREAM;
    if (getaddrinfo(HOST,"443",&hints,&list)) return -EHOSTUNREACH;
    int r=-ECONNREFUSED;
    for (struct addrinfo *a=list; a && now_ms()<s->deadline; a=a->ai_next) {
        s->net.fd=socket(a->ai_family,a->ai_socktype,a->ai_protocol);
        if (s->net.fd<0) continue;
        if (fcntl(s->net.fd,F_SETFL,O_NONBLOCK)<0) { mbedtls_net_free(&s->net); continue; }
        r=connect(s->net.fd,a->ai_addr,a->ai_addrlen);
        if (r<0 && errno==EINPROGRESS) {
            r=wait_io(s,MBEDTLS_ERR_SSL_WANT_WRITE);
            if (!r) {
                int error=0; socklen_t len=sizeof(error);
                if (getsockopt(s->net.fd,SOL_SOCKET,SO_ERROR,&error,&len)<0 || error) r=-ECONNREFUSED;
            }
        }
        if (!r) break;
        mbedtls_net_free(&s->net);
    }
    freeaddrinfo(list);
    return r;
}
static int transfer(session_t *s, unsigned char *buf, size_t len, int writing)
{
    while (len) {
        if (now_ms() >= s->deadline) return -ETIMEDOUT;
        int r = writing ? mbedtls_ssl_write(&s->ssl, buf, len) : mbedtls_ssl_read(&s->ssl, buf, len);
        if (r > 0) { buf += r; len -= r; continue; }
        if (r != MBEDTLS_ERR_SSL_WANT_READ && r != MBEDTLS_ERR_SSL_WANT_WRITE) return -EIO;
        r = wait_io(s, r);
        if (r) return r;
    }
    return 0;
}
static int send_frame(session_t *s, int opcode, const unsigned char *data, size_t len)
{
    if (len > 65535) return -EOVERFLOW;
    unsigned char header[8], mask[4], chunk[1024];
    size_t n = 2;
    header[0] = 0x80 | opcode;
    if (len < 126) header[1] = 0x80 | len;
    else { header[1]=0xfe; header[2]=len >> 8; header[3]=len; n=4; }
    if (mbedtls_ctr_drbg_random(&s->rng, mask, 4)) return -EIO;
    memcpy(header+n, mask, 4);
    int r = transfer(s, header, n+4, 1);
    for (size_t at=0; !r && at<len;) {
        size_t count = len-at > sizeof(chunk) ? sizeof(chunk) : len-at;
        for (size_t i=0; i<count; i++) chunk[i]=data[at+i]^mask[(at+i)%4];
        r=transfer(s, chunk, count, 1); at+=count;
    }
    return r;
}
/* Assemble fragmented text messages and handle interleaved ping/pong. */
static int read_message(session_t *s, voice_tts_chunk_cb cb, void *user, size_t *audio_bytes)
{
    size_t used=0;
    int fragmented=0;
    for (;;) {
        unsigned char h[2], ext[8], control[125];
        int r=transfer(s,h,2,0);
        if (r) return r;
        int op=h[0]&15, fin=h[0]&128;
        uint64_t len=h[1]&127;
        if ((h[0]&0x70) || (h[1]&128)) return -EPROTO;
        if (len>=126) {
            int bytes=len==126 ? 2 : 8;
            if ((r=transfer(s,ext,bytes,0))) return r;
            len=0; for(int i=0;i<bytes;i++) len=(len<<8)|ext[i];
        }
        if (op>=8) {
            if (!fin || len>125) return -EPROTO;
            if ((r=transfer(s,control,len,0))) return r;
            if (op==8) return -ECONNRESET;
            if (op==9) { if ((r=send_frame(s,10,control,len))) return r; }
            else if (op!=10) return -EPROTO;
            continue;
        }
        if ((!fragmented && op!=1 && op!=2) || (fragmented && op!=0)) return -EPROTO;
        if (!fragmented) s->message_opcode=op;
        if (s->message_opcode==2) {
            if (!cb || !audio_bytes || !s->started) return -EPROTO;
            if (len>24000*2*120 || *audio_bytes+len>24000*2*120) return -EOVERFLOW;
            while (len) {
                size_t prefix=s->pcm_pending ? 1 : 0;
                size_t count=len>EVENT_CAP-2 ? EVENT_CAP-2 : (size_t)len;
                if (prefix) s->message[0]=s->pcm_byte;
                if ((r=transfer(s,s->message+prefix,count,0))) return r;
                size_t total=count+prefix, complete=total&~(size_t)1;
                s->pcm_pending=total%2;
                if (s->pcm_pending) s->pcm_byte=s->message[complete];
                if (complete) cb(s->message,complete,0,user);
                *audio_bytes+=count; len-=count;
            }
            if (fin) { s->message_len=0; return 0; }
            fragmented=1; continue;
        }
        if (len>=EVENT_CAP-used) return -EOVERFLOW;
        if ((r=transfer(s,s->message+used,(size_t)len,0))) return r;
        used+=(size_t)len;
        if (fin) { s->message[used]=0; s->message_len=used; return 0; }
        fragmented=1;
    }
}
static int event(session_t *s)
{
    int r=read_message(s,NULL,NULL,NULL);
    if (r) return r;
    if (s->message_opcode!=1) return -EPROTO;
    cJSON *root=cJSON_Parse((char *)s->message);
    if (!root) return -EPROTO;
    cJSON *header=cJSON_GetObjectItemCaseSensitive(root,"header");
    cJSON *id=cJSON_GetObjectItemCaseSensitive(header,"task_id");
    cJSON *kind=cJSON_GetObjectItemCaseSensitive(header,"event");
    r=-EPROTO;
    if (!cJSON_IsString(id) || strcmp(id->valuestring,s->id) || !cJSON_IsString(kind)) goto done;
    r=0;
    if (!strcmp(kind->valuestring,"task-started")) s->started=1;
    else if (!strcmp(kind->valuestring,"task-finished")) s->finished=1;
    else if (!strcmp(kind->valuestring,"task-failed")) {
        cJSON *code=cJSON_GetObjectItemCaseSensitive(header,"error_code");
        syslog(LOG_ERR,"[aliyun_asr] task failed: %.80s\n",cJSON_IsString(code)?code->valuestring:"unknown");
        r=-EIO;
    } else if (!strcmp(kind->valuestring,"result-generated")) {
        cJSON *payload=cJSON_GetObjectItemCaseSensitive(root,"payload");
        cJSON *output=cJSON_GetObjectItemCaseSensitive(payload,"output");
        cJSON *sentence=cJSON_GetObjectItemCaseSensitive(output,"sentence");
        if (cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(sentence,"heartbeat"))) goto done;
        if (!cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(sentence,"sentence_end"))) goto done;
        cJSON *text=cJSON_GetObjectItemCaseSensitive(sentence,"text");
        cJSON *begin=cJSON_GetObjectItemCaseSensitive(sentence,"begin_time");
        if (!cJSON_IsString(text) || !cJSON_IsNumber(begin)) { r=-EPROTO; goto done; }
        /* begin_time identifies ordered sentences in this API (no sentence_id).
         * A repeated final replaces the same sentence instead of duplicating it. */
        if (begin->valueint<s->last_begin) goto done;
        size_t offset=begin->valueint==s->last_begin ? s->last_offset : strlen(s->result);
        size_t n=strlen(text->valuestring);
        if (n>=sizeof(s->result)-offset) { r=-ENOSPC; goto done; }
        memcpy(s->result+offset,text->valuestring,n+1);
        s->last_offset=offset; s->last_begin=begin->valueint;
    } else r=-EPROTO;
done:
    cJSON_Delete(root);
    return r;
}

static int upgrade(session_t *s, const char *key)
{
    unsigned char random[16], b64[32], digest[20], expected[32];
    size_t n;
    if (mbedtls_ctr_drbg_random(&s->rng,random,sizeof(random))) return -EIO;
    if (mbedtls_base64_encode(b64,sizeof(b64),&n,random,sizeof(random))) return -EIO;
    b64[n]=0;
    char joined[80];
    snprintf(joined,sizeof(joined),"%s258EAFA5-E914-47DA-95CA-C5AB0DC85B11",b64);
    if (mbedtls_sha1((unsigned char *)joined,strlen(joined),digest)) return -EIO;
    if (mbedtls_base64_encode(expected,sizeof(expected),&n,digest,20)) return -EIO;
    expected[n]=0;
    int count=snprintf((char *)s->message,EVENT_CAP,
        "GET " PATH " HTTP/1.1\r\nHost: " HOST "\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
        "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\nAuthorization: Bearer %s\r\n\r\n",b64,key);
    if (count<0 || count>=EVENT_CAP) return -EOVERFLOW;
    int r=transfer(s,s->message,count,1);
    memset(s->message,0,EVENT_CAP);
    if (r) return r;
    /* Consume only the HTTP header, preserving any coalesced WS frame. */
    size_t used=0;
    while (used<4095) {
        if ((r=transfer(s,s->message+used,1,0))) return r;
        used++;
        if (used>=4 && !memcmp(s->message+used-4,"\r\n\r\n",4)) break;
    }
    s->message[used]=0;
    int status=0, accept=0;
    if (sscanf((char *)s->message,"HTTP/1.1 %d",&status)!=1 || status!=101) {
        syslog(LOG_ERR,"[aliyun_asr] WebSocket HTTP %d\n",status); return -EACCES;
    }
    char *line=(char *)s->message;
    while ((line=strstr(line,"\r\n"))) {
        line+=2;
        if (!strncasecmp(line,"Sec-WebSocket-Accept:",21)) {
            char *value=line+21; while (*value==' ' || *value=='\t') value++;
            accept=!strncmp(value,(char *)expected,n) && !strncmp(value+n,"\r\n",2);
        }
    }
    return accept ? 0 : -EPROTO;
}

void qiji_aliyun_abort(void *handle)
{
    session_t *s=handle;
    if (!s) return;
    mbedtls_net_free(&s->net);
    mbedtls_ssl_free(&s->ssl);
    mbedtls_ssl_config_free(&s->conf);
    mbedtls_ctr_drbg_free(&s->rng);
    mbedtls_x509_crt_free(&s->ca);
    free(s);
}
static session_t *open_connection(void)
{
    char key[256]={0};
    if (claw_config_get("aliyun_asr_key",key,sizeof(key)) || !*key || strpbrk(key,"\r\n")) {
        syslog(LOG_ERR,"[aliyun_asr] configure a Beijing API key first\n"); return NULL;
    }
    /* Trust verification requires real time. Wi-Fi starts the NTP daemon. */
    if (time(NULL)<1767225600) {
        syslog(LOG_ERR,"[aliyun_asr] waiting for time synchronization\n");
        memset(key,0,sizeof(key)); return NULL;
    }
    session_t *s=calloc(1,sizeof(*s));
    if (!s) { memset(key,0,sizeof(key)); return NULL; }
    s->last_begin=-1;
    s->deadline=now_ms()+15000; s->expires=now_ms()+90000;
    mbedtls_net_init(&s->net); mbedtls_ssl_init(&s->ssl);
    mbedtls_ssl_config_init(&s->conf); mbedtls_ctr_drbg_init(&s->rng); mbedtls_x509_crt_init(&s->ca);
    int r=mbedtls_ctr_drbg_seed(&s->rng,entropy,NULL,(unsigned char *)"qiji-aliyun",11);
    if (!r) r=mbedtls_x509_crt_parse(&s->ca,(unsigned char *)qiji_aliyun_ca,sizeof(qiji_aliyun_ca));
    if (!r) r=mbedtls_ssl_config_defaults(&s->conf,MBEDTLS_SSL_IS_CLIENT,MBEDTLS_SSL_TRANSPORT_STREAM,MBEDTLS_SSL_PRESET_DEFAULT);
    if (!r) {
        mbedtls_ssl_conf_authmode(&s->conf,MBEDTLS_SSL_VERIFY_REQUIRED);
        mbedtls_ssl_conf_ca_chain(&s->conf,&s->ca,NULL);
        mbedtls_ssl_conf_rng(&s->conf,mbedtls_ctr_drbg_random,&s->rng);
        r=mbedtls_ssl_setup(&s->ssl,&s->conf);
    }
    if (!r) r=mbedtls_ssl_set_hostname(&s->ssl,HOST);
    if (!r) r=connect_tcp(s);
    if (!r) {
        mbedtls_ssl_set_bio(&s->ssl,&s->net,mbedtls_net_send,mbedtls_net_recv,NULL);
        while ((r=mbedtls_ssl_handshake(&s->ssl))) {
            if (r!=MBEDTLS_ERR_SSL_WANT_READ && r!=MBEDTLS_ERR_SSL_WANT_WRITE) break;
            if ((r=wait_io(s,r))) break;
        }
    }
    if (!r) r=upgrade(s,key);
    memset(key,0,sizeof(key));
    unsigned char uuid[16];
    if (!r) r=mbedtls_ctr_drbg_random(&s->rng,uuid,16);
    if (!r) {
        uuid[6]=(uuid[6]&15)|64; uuid[8]=(uuid[8]&63)|128;
        snprintf(s->id,sizeof(s->id),"%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
            uuid[0],uuid[1],uuid[2],uuid[3],uuid[4],uuid[5],uuid[6],uuid[7],uuid[8],uuid[9],uuid[10],uuid[11],uuid[12],uuid[13],uuid[14],uuid[15]);
    }
    if (r) {
        syslog(LOG_ERR,"[aliyun] connect failed (%d), certificate flags=%lu\n",r,(unsigned long)mbedtls_ssl_get_verify_result(&s->ssl));
        qiji_aliyun_abort(s); return NULL;
    }
    return s;
}
void *qiji_aliyun_open(void)
{
    session_t *s=open_connection();
    if (!s) return NULL;
    int r=0;
    {
        int n=snprintf((char *)s->message,EVENT_CAP,
            "{\"header\":{\"action\":\"run-task\",\"task_id\":\"%s\",\"streaming\":\"duplex\"},"
            "\"payload\":{\"task_group\":\"audio\",\"task\":\"asr\",\"function\":\"recognition\","
            "\"model\":\"paraformer-realtime-v2\",\"parameters\":{\"format\":\"pcm\",\"sample_rate\":16000,"
            "\"language_hints\":[\"zh\",\"en\"]},\"input\":{}}}",s->id);
        r=send_frame(s,1,s->message,n);
        if (!r) r=event(s);
        if (!r && !s->started) r=-EPROTO;
    }
    if (r) {
        syslog(LOG_ERR,"[aliyun_asr] open failed (%d), certificate flags=%lu\n",r,(unsigned long)mbedtls_ssl_get_verify_result(&s->ssl));
        qiji_aliyun_abort(s); return NULL;
    }
    syslog(LOG_INFO,"[aliyun_asr] task started\n");
    return s;
}
int qiji_aliyun_send(void *handle, const unsigned char *pcm, size_t len)
{
    session_t *s=handle;
    if (!s || !pcm || !len || len%2) return -EINVAL;
    if (s->error) return s->error;
    s->deadline=now_ms()+5000;
    if (s->deadline>s->expires) s->deadline=s->expires;
    int r=send_frame(s,2,pcm,len);
    for (int i=0; !r && i<32; i++) {
        struct pollfd p={.fd=s->net.fd,.events=POLLIN};
        if (!mbedtls_ssl_check_pending(&s->ssl) && poll(&p,1,0)<=0) break;
        r=event(s);
        if (!r && s->finished) r=-EPROTO;
    }
    return s->error=r;
}
int qiji_aliyun_finish(void *handle, char *text, size_t cap)
{
    session_t *s=handle;
    if (!s) return -EINVAL;
    int r=s->error;
    if (!text || !cap) r=-EINVAL;
    if (text && cap) *text=0;
    s->deadline=now_ms()+15000;
    if (!r) {
        int n=snprintf((char *)s->message,EVENT_CAP,
            "{\"header\":{\"action\":\"finish-task\",\"task_id\":\"%s\",\"streaming\":\"duplex\"},\"payload\":{\"input\":{}}}",s->id);
        r=send_frame(s,1,s->message,n);
        while (!r && !s->finished) r=event(s);
        if (!r && strlen(s->result)>=cap) r=-ENOSPC;
        if (!r) memcpy(text,s->result,strlen(s->result)+1);
    }
    if (r) syslog(LOG_ERR,"[aliyun_asr] finish failed (%d)\n",r);
    qiji_aliyun_abort(s);
    return r;
}
static int recognize(const unsigned char *pcm, size_t len, char *text, size_t cap)
{
    if (!pcm || !len || len%2 || !text || !cap) return -EINVAL;
    *text=0;
    void *s=qiji_aliyun_open();
    if (!s) return -EIO;
    for (size_t at=0; at<len;) {
        size_t n=len-at>3200 ? 3200 : len-at;
        int r=qiji_aliyun_send(s,pcm+at,n);
        if (r) { qiji_aliyun_abort(s); return r; }
        at+=n; usleep(100000);
    }
    return qiji_aliyun_finish(s,text,cap);
}
void qiji_aliyun_register(void)
{
    static const voice_asr_ops_t ops={.name="aliyun",.recognize=recognize};
    voice_asr_register(&ops);
    char selected[24]={0};
    if (!claw_config_get("qiji_asr_backend",selected,sizeof(selected))) voice_asr_set_backend(selected);
}

/* TTS uses the same authenticated transport, with an independent session.
 * Streaming playback in the official voice channel expects 24 kHz; the
 * batch voice_tts_ops contract expects 16 kHz. Request the proper rate. */
static int send_json(session_t *s, cJSON *root)
{
    if (!root) return -ENOMEM;
    char *json=cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    if (!json) return -ENOMEM;
    int r=send_frame(s,1,(unsigned char *)json,strlen(json));
    free(json);
    return r;
}
static cJSON *task_json(session_t *s, const char *action)
{
    cJSON *root=cJSON_CreateObject();
    cJSON *h=cJSON_AddObjectToObject(root,"header");
    if (!h || !cJSON_AddStringToObject(h,"action",action) ||
        !cJSON_AddStringToObject(h,"task_id",s->id) ||
        !cJSON_AddStringToObject(h,"streaming","duplex")) {
        cJSON_Delete(root); return NULL;
    }
    cJSON *p=cJSON_AddObjectToObject(root,"payload");
    if (!p || !cJSON_AddObjectToObject(p,"input")) { cJSON_Delete(root); return NULL; }
    return root;
}
static int tts_event(session_t *s, voice_tts_chunk_cb cb, void *user, size_t *bytes)
{
    int r=read_message(s,cb,user,bytes);
    if (r) return r;
    if (s->message_opcode==2) {
        return 0;
    }
    cJSON *root=cJSON_Parse((char *)s->message);
    cJSON *h=cJSON_GetObjectItemCaseSensitive(root,"header");
    cJSON *id=cJSON_GetObjectItemCaseSensitive(h,"task_id");
    cJSON *kind=cJSON_GetObjectItemCaseSensitive(h,"event");
    r=-EPROTO;
    if (cJSON_IsString(id) && !strcmp(id->valuestring,s->id) && cJSON_IsString(kind)) {
        r=0;
        if (!strcmp(kind->valuestring,"task-started")) s->started=1;
        else if (!strcmp(kind->valuestring,"task-finished")) s->finished=1;
        else if (!strcmp(kind->valuestring,"task-failed")) {
            cJSON *code=cJSON_GetObjectItemCaseSensitive(h,"error_code");
            syslog(LOG_ERR,"[qwen_tts] task failed: %.80s\n",cJSON_IsString(code)?code->valuestring:"unknown");
            r=-EIO;
        } else if (strcmp(kind->valuestring,"result-generated")) r=-EPROTO;
    }
    cJSON_Delete(root);
    return r;
}
static int synthesize_stream(const char *text, int rate, voice_tts_chunk_cb cb, void *user)
{
    if (!text || !*text || strlen(text)>8192 || !cb) return -EINVAL;
    int64_t start=now_ms();
    session_t *s=open_connection();
    if (!s) return -EIO;
    char voice[96]="longanlingxi_v3.1";
    char instruction[512]="用自然、亲切的年轻女性声音说话，语气轻快，略带笑意，情绪适度，像朋友聊天。";
    claw_config_get("qiji_tts_voice",voice,sizeof(voice));
    claw_config_get("qiji_tts_instruction",instruction,sizeof(instruction));
    cJSON *root=task_json(s,"run-task");
    cJSON *p=cJSON_GetObjectItemCaseSensitive(root,"payload");
    cJSON *params=cJSON_AddObjectToObject(p,"parameters");
    int r=0;
    if (!params || !cJSON_AddStringToObject(p,"task_group","audio") ||
        !cJSON_AddStringToObject(p,"task","tts") || !cJSON_AddStringToObject(p,"function","SpeechSynthesizer") ||
        !cJSON_AddStringToObject(p,"model","qwen-audio-3.1-tts-flash") ||
        !cJSON_AddStringToObject(params,"text_type","PlainText") || !cJSON_AddStringToObject(params,"voice",voice) ||
        !cJSON_AddStringToObject(params,"format","pcm") || !cJSON_AddNumberToObject(params,"sample_rate",rate) ||
        !cJSON_AddNumberToObject(params,"volume",50) || !cJSON_AddNumberToObject(params,"rate",1.0) ||
        !cJSON_AddStringToObject(params,"instruction",instruction)) {
        cJSON_Delete(root); r=-ENOMEM;
    } else r=send_json(s,root);
    size_t bytes=0;
    if (!r) r=tts_event(s,NULL,NULL,&bytes);
    if (!r && !s->started) r=-EPROTO;
    if (!r) {
        root=task_json(s,"continue-task");
        p=cJSON_GetObjectItemCaseSensitive(root,"payload");
        cJSON *input=cJSON_GetObjectItemCaseSensitive(p,"input");
        if (!input || !cJSON_AddStringToObject(input,"text",text)) { cJSON_Delete(root); r=-ENOMEM; }
        else r=send_json(s,root);
    }
    if (!r) r=send_json(s,task_json(s,"finish-task"));
    s->expires=now_ms()+120000;
    while (!r && !s->finished) {
        s->deadline=now_ms()+15000;
        if (s->deadline>s->expires) s->deadline=s->expires;
        size_t before=bytes;
        r=tts_event(s,cb,user,&bytes);
        if (!before && bytes) syslog(LOG_INFO,"[qwen_tts] first PCM: %lld ms\n",(long long)(now_ms()-start));
    }
    if (!r && !bytes) r=-ENODATA;
    if (!r && s->pcm_pending) r=-EPROTO;
    if (!r) cb(NULL,0,1,user);
    syslog(LOG_INFO,"[qwen_tts] completed rc=%d bytes=%zu rate=%d\n",r,bytes,rate);
    qiji_aliyun_abort(s);
    return r;
}
int qiji_aliyun_tts_stream(const char *text, voice_tts_chunk_cb cb, void *user)
{ return synthesize_stream(text,24000,cb,user); }
typedef struct { unsigned char *pcm; size_t cap,len; int overflow; } tts_buffer_t;
static void buffer_tts(const unsigned char *pcm,size_t len,int last,void *user)
{
    (void)last;
    tts_buffer_t *b=user;
    if (b->overflow || len>b->cap-b->len) { b->overflow=1; return; }
    if (len) { memcpy(b->pcm+b->len,pcm,len); b->len+=len; }
}
static int tts_batch(const char *text,unsigned char *pcm,size_t cap,size_t *len)
{
    if (!pcm || !cap || !len) return -EINVAL;
    *len=0;
    tts_buffer_t b={.pcm=pcm,.cap=cap};
    int r=synthesize_stream(text,16000,buffer_tts,&b);
    if (!r && b.overflow) r=-ENOSPC;
    if (!r) *len=b.len;
    return r;
}
void qiji_aliyun_tts_register(void)
{
    static const voice_tts_ops_t ops={.name="aliyun",.synthesize=tts_batch};
    if (voice_tts_register(&ops)) return;
    char selected[24]="aliyun";
    claw_config_get("qiji_tts_backend",selected,sizeof(selected));
    voice_tts_set_backend(selected);
}
