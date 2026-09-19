#include "voice/audio_playback.h"
#include "media_player.h"
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
extern int qiji_audio_playback_finish(audio_playback_t *);
static media_event_callback callback;
static void *cookie;
static unsigned char captured[8192];
static size_t received;
static int fail_write,eof,stopped,stall,retries;
void *media_player_open(const char *stream)
{ (void)stream; received=0;eof=0;stopped=0;return &received; }
int media_player_close(void *p,int pending) { (void)p;(void)pending;return 0; }
int media_player_stop(void *p) { (void)p;stopped=1;return 0; }
int media_player_prepare(void *p,const char *url,const char *options)
{ (void)p;(void)url;assert(strstr(options,"sample_rate=48000:ch_layout=stereo"));return 0; }
int media_player_start(void *p) { (void)p;return 0; }
int media_player_set_event_callback(void *p,void *c,media_event_callback cb)
{ (void)p;cookie=c;callback=cb;return 0; }
ssize_t media_player_write_data(void *p,const void *data,size_t len)
{
    (void)p;
    if (fail_write) return -EIO;
    if (stall || retries-- > 0) return -EAGAIN;
    size_t n=len>6?6:len;
    assert(received+n<=sizeof(captured));
    memcpy(captured+received,data,n);received+=n;return n;
}
void media_player_close_socket(void *p)
{ (void)p;assert(!stopped);eof=1;callback(cookie,MEDIA_EVENT_COMPLETED,0,NULL); }
static long long now_ms(void)
{ struct timespec ts;clock_gettime(CLOCK_MONOTONIC,&ts);return (long long)ts.tv_sec*1000+ts.tv_nsec/1000000; }
static void *cancel(void *p) { usleep(100000);audio_playback_stop(p);return NULL; }
int main(void)
{
    int16_t pcm[]={0,1000,2000,-1000};
    int16_t expected[]={0,0,0,0,500,500,1000,1000,1500,1500,2000,2000,500,500,-1000,-1000};
    audio_playback_t *p=audio_playback_open("unused",24000,1,16);
    retries=3;
    assert(p && audio_playback_write(p,pcm,sizeof(pcm))==sizeof(pcm));
    assert(received==sizeof(expected) && !memcmp(captured,expected,received));
    assert(qiji_audio_playback_finish(p)==0 && eof && !stopped);
    audio_playback_close(p);
    p=audio_playback_open("unused",24000,1,16);
    for (int i=0;i<4;i++) assert(audio_playback_write(p,pcm+i,2)==2);
    assert(received==sizeof(expected) && !memcmp(captured,expected,received));
    audio_playback_close(p);
    p=audio_playback_open("unused",16000,1,16);
    assert(audio_playback_write(p,pcm,sizeof(pcm))==sizeof(pcm));
    assert(received==sizeof(pcm)*6);
    for (size_t i=0;i<received;i+=4) assert(!memcmp(captured+i,captured+i+2,2));
    audio_playback_close(p);
    p=audio_playback_open("unused",24000,1,16);fail_write=1;
    assert(audio_playback_write(p,pcm,sizeof(pcm))==-EIO);
    assert(qiji_audio_playback_finish(p)==-EIO);audio_playback_close(p);
    fail_write=0;stall=1;p=audio_playback_open("unused",24000,1,16);
    long long start=now_ms();
    assert(audio_playback_write(p,pcm,sizeof(pcm))==-ETIMEDOUT);
    assert(now_ms()-start>=4900 && now_ms()-start<6500);
    audio_playback_close(p);
    p=audio_playback_open("unused",24000,1,16);
    pthread_t thread;assert(!pthread_create(&thread,NULL,cancel,p));
    start=now_ms();assert(audio_playback_write(p,pcm,sizeof(pcm))==-ECANCELED);
    assert(now_ms()-start<1000);pthread_join(thread,NULL);
    assert(!stopped); /* cancellation never blocks on media IPC */
    audio_playback_close(p);
    puts("PASS: PCM rate/channels, chunk continuity, short writes, EOF, errors, timeout and cancellation");
    return 0;
}
