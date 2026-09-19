/* SPDX-License-Identifier: Apache-2.0 */
#include <nuttx/config.h>
#include <wireless/wapi.h>
#include <netutils/netlib.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <sys/stat.h>

static pthread_mutex_t wifi_lock = PTHREAD_MUTEX_INITIALIZER;

#include <netutils/ntpclient.h>

/* Credentials stay in /data; never compile them into a distributable image. */
int qiji_wifi_connect(const char *ssid, const char *password)
{
    struct wpa_wconfig_s conf;
    void *loaded = NULL;
    int rc;
    if (pthread_mutex_trylock(&wifi_lock)) return -EBUSY;
    memset(&conf, 0, sizeof(conf));
    if (ssid) {
        if (!*ssid || strlen(ssid) > 32 || !password ||
            strlen(password) < 8 || strlen(password) > 63) {
            rc = -EINVAL;
            goto out;
        }
        /* Factory reset may remove the saved network directory. */
        if ((mkdir("/data/etc",0700)<0 && errno!=EEXIST) ||
            (mkdir("/data/etc/wifi",0700)<0 && errno!=EEXIST)) {
            rc=-errno; goto out;
        }
        conf.ifname = "wlan0";
        conf.sta_mode = WAPI_MODE_MANAGED;
        conf.auth_wpa = IW_AUTH_WPA_VERSION_WPA2;
        conf.cipher_mode = IW_AUTH_CIPHER_CCMP;
        conf.alg = WPA_ALG_CCMP;
        conf.ssid = ssid;
        conf.ssidlen = strlen(ssid);
        conf.bssid = "";
        conf.passphrase = password;
        conf.phraselen = strlen(password);
        rc = wapi_save_config("wlan0", NULL, &conf);
        if (rc < 0) goto out;
    }
    /* The loader requires a bssid string, even when association uses SSID. */
    loaded = wapi_load_config("wlan0", NULL, &conf);
    if (!loaded) { rc = -ENOENT; goto out; }
    rc = netlib_ifup("wlan0");
    if (rc < 0) goto out;
    rc = wpa_driver_wext_associate(&conf);
    if (rc < 0) goto out;
    bool associated = false;
    for (int i = 0; i < 20; i++) {
        uint8_t flags = 0;
        netlib_getifstatus("wlan0", &flags);
        if (flags & IFF_RUNNING) { associated = true; break; }
        sleep(1);
    }
    if (!associated) { rc=-ENETUNREACH; goto out; }
    /* Factory 10.0.0.2 is not a lease on the selected WLAN. */
    struct in_addr address = { .s_addr = INADDR_ANY };
    rc = netlib_set_ipv4addr("wlan0", &address);
    if (rc < 0) goto out;
    for (int i = 0; i < 3; i++) {
        rc = netlib_obtain_ipv4addr("wlan0");
        if (rc == 0) break;
        sleep(2);
    }
    if (rc == 0 && netlib_get_ipv4addr("wlan0", &address) == 0) {
        char ip[INET_ADDRSTRLEN];
        printf("Wi-Fi connected: %s\n", inet_ntop(AF_INET, &address, ip, sizeof(ip)));
        ntpc_start_with_list("ntp.aliyun.com;time.cloudflare.com");
    }
out:
    if (loaded) wapi_unload_config(loaded);
    if (rc < 0) printf("Wi-Fi connection failed (%d)\n", rc);
    pthread_mutex_unlock(&wifi_lock);
    return rc;
}
