#pragma once
#include <stddef.h>
#include <sys/types.h>
#define MEDIA_STREAM_MUSIC "music"
#define MEDIA_EVENT_COMPLETED 6
typedef void (*media_event_callback)(void *,int,int,const char *);
void *media_player_open(const char *);
int media_player_close(void *,int);
int media_player_stop(void *);
int media_player_prepare(void *,const char *,const char *);
int media_player_start(void *);
int media_player_set_event_callback(void *,void *,media_event_callback);
ssize_t media_player_write_data(void *,const void *,size_t);
void media_player_close_socket(void *);
