#include "pfw.h"
#include <stdio.h>
#include <string.h>
static int bad_command;
static void command(void *cookie,const char *params)
{
    (void)cookie;
    if (strncmp(params,"VolApb,volume,",14) && strncmp(params,"VolAcap,volume,",15)) bad_command=1;
}
int main(int argc,char **argv)
{
    if (argc!=3) return 2;
    pfw_plugin_def_t plugins[]={{"FFmpegCommand",NULL,command},{"SetParameter",NULL,command}};
    void *p=pfw_create(argv[1],argv[2],plugins,2,NULL,NULL,NULL);
    if (!p) { puts("FAIL: media policy rejected"); return 1; }
    char route[64];
    if (pfw_getstring(p,"Capture",route,sizeof(route))<0 || strcmp(route,"abufsink@acap")) return 1;
    if (pfw_getstring(p,"Music",route,sizeof(route))<0 || strcmp(route,"abufsrc@apb")) return 1;
    pfw_apply(p);
    if (pfw_setint(p,"MusicVolume",0)) return 1;
    pfw_apply(p);
    if (pfw_setint(p,"MusicVolume",6)) return 1;
    pfw_apply(p);
    pfw_destroy(p,NULL);
    if (bad_command) return 1;
    puts("PASS: media policy, capture/playback routes and volume targets");
    return 0;
}
