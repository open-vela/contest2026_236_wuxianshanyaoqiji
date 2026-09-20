/* SPDX-License-Identifier: Apache-2.0
 * LAN transport only. The existing UI worker remains the sole audio owner.
 */
#include <nuttx/config.h>
#include "qiji_duet.h"
#include "infra/config_store.h"
#include "cJSON.h"
#include <arpa/inet.h>
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

static atomic_bool active, stop_requested;
static pthread_mutex_t config_lock = PTHREAD_MUTEX_INITIALIZER;
static unsigned config_epoch;

bool qiji_duet_active(void) { return atomic_load(&active); }
void qiji_duet_stop(void) { atomic_store(&stop_requested, true); }

int qiji_duet_configure(const char *ip, const char *port, const char *token)
{
    struct in_addr address;
    if (!ip) return -EINVAL;
    if (*ip) {
        if (!port || !token || inet_pton(AF_INET, ip, &address) != 1 || strlen(port) > 5 ||
            strlen(token) < 16 || strlen(token) > 80) return -EINVAL;
        for (const char *p = port; *p; ++p) if (!isdigit((unsigned char)*p)) return -EINVAL;
        if (atoi(port) < 1 || atoi(port) > 65535) return -EINVAL;
        for (const char *p = token; *p; ++p) if (!isalnum((unsigned char)*p) && *p != '-' && *p != '_') return -EINVAL;
    }
    pthread_mutex_lock(&config_lock);
    int rc = claw_config_set("duet_host", "");
    if (!rc && *ip) rc = claw_config_set("duet_port", port);
    if (!rc && *ip) rc = claw_config_set("duet_token", token);
    if (!rc && *ip) rc = claw_config_set("duet_host", ip);
    config_epoch++;
    pthread_mutex_unlock(&config_lock);
    atomic_store(&stop_requested, false);
    atomic_store(&active, false);
    return rc;
}

static cJSON *poll_server(const char *ip, int port, const char *token, int ack, bool ok, bool ready, bool stop)
{
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return NULL;
    cJSON *result = NULL;
    char *response = NULL;
    struct timeval timeout = {.tv_sec = 3};
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
    setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
    struct sockaddr_in addr = {.sin_family = AF_INET, .sin_port = htons(port)};
    if (inet_pton(AF_INET, ip, &addr.sin_addr) != 1) goto done;
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags < 0 || fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0) goto done;
    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        if (errno != EINPROGRESS) goto done;
        struct pollfd p = {.fd = fd, .events = POLLOUT};
        int error = 0; socklen_t length = sizeof(error);
        if (poll(&p, 1, 3000) <= 0 || getsockopt(fd, SOL_SOCKET, SO_ERROR, &error, &length) < 0 || error) goto done;
    }
    if (fcntl(fd, F_SETFL, flags) < 0) goto done;
    char body[192], request[640];
    snprintf(body, sizeof(body), "{\"device\":\"qiji\",\"ack\":%d,\"result\":\"%s\",\"ready\":%s,\"action\":\"%s\"}",
        ack, ok ? "ok" : "error", ready ? "true" : "false", stop ? "stop" : "");
    int n = snprintf(request, sizeof(request),
        "POST /v1/poll HTTP/1.0\r\nHost: %s:%d\r\nAuthorization: Bearer %s\r\n"
        "Content-Type: application/json\r\nContent-Length: %u\r\nConnection: close\r\n\r\n%s",
        ip, port, token, (unsigned)strlen(body), body);
    if (n < 0 || n >= sizeof(request)) goto done;
    for (int sent = 0; sent < n;) {
        int k = send(fd, request + sent, n - sent, 0);
        if (k <= 0) goto done;
        sent += k;
    }
    response = malloc(6144);
    if (!response) goto done;
    int used = 0;
    for (;;) {
        if (used == 6143) goto done;
        int k = recv(fd, response + used, 6143 - used, 0);
        if (k < 0) goto done;
        if (!k) break;
        used += k;
    }
    response[used] = 0;
    if (strncmp(response, "HTTP/1.0 200 ", 13) && strncmp(response, "HTTP/1.1 200 ", 13)) goto done;
    char *start = strstr(response, "\r\n\r\n");
    if (!start || used - (start + 4 - response) > 4095) goto done;
    result = cJSON_Parse(start + 4);
done:
    free(response); close(fd);
    return result;
}

static const char *string(cJSON *obj, const char *key)
{
    cJSON *v = cJSON_GetObjectItemCaseSensitive(obj, key);
    return cJSON_IsString(v) ? v->valuestring : "";
}

static void *network(void *arg)
{
    (void)arg;
    int last = 0, ack = 0, outcome = 0;
    unsigned epoch = 0;
    bool pending = false;
    for (;;) {
        char ip[32] = "", port[8] = "", token[96] = "";
        pthread_mutex_lock(&config_lock);
        claw_config_get("duet_host", ip, sizeof(ip));
        claw_config_get("duet_port", port, sizeof(port));
        claw_config_get("duet_token", token, sizeof(token));
        if (epoch != config_epoch) { epoch = config_epoch; last = ack = 0; pending = false; }
        pthread_mutex_unlock(&config_lock);
        if (!*ip || !*token) { atomic_store(&active, false); usleep(1000000); continue; }
        if (pending && (outcome = qiji_chat_duet_result()) != -EINPROGRESS) { ack = last; pending = false; }
        bool stop = atomic_load(&stop_requested);
        cJSON *r = poll_server(ip, atoi(port), token, ack, outcome == 0, qiji_chat_duet_ready(), stop);
        memset(token, 0, sizeof(token));
        if (!r) {
            if (atomic_load(&active)) atomic_store(&stop_requested, true);
            atomic_store(&active, false);
            usleep(1000000); continue;
        }
        if (stop) atomic_store(&stop_requested, false);
        const char *state = string(r, "state");
        bool enabled = !strcmp(state, "generating") || !strcmp(state, "speaking") || !strcmp(state, "summarizing");
        atomic_store(&active, enabled);
        cJSON *id = cJSON_GetObjectItemCaseSensitive(r, "seq");
        if (enabled && cJSON_IsNumber(id) && id->valueint > 0 && id->valueint != last && !pending) {
            int rc = qiji_chat_duet_present(string(r, "text"),
                cJSON_IsTrue(cJSON_GetObjectItemCaseSensitive(r, "speak")),
                !strcmp(string(r, "kind"), "summary"), string(r, "speaker"));
            if (!rc) { last = id->valueint; pending = true; }
            else if (rc != -EBUSY) { last = ack = id->valueint; outcome = rc; }
        }
        cJSON_Delete(r);
        usleep(650000);
    }
    return NULL;
}

void qiji_duet_start(void)
{
    pthread_t thread;
    pthread_attr_t attr;
    pthread_attr_init(&attr); pthread_attr_setstacksize(&attr, 16384);
    int rc = pthread_create(&thread, &attr, network, NULL);
    pthread_attr_destroy(&attr);
    if (!rc) pthread_detach(thread);
    else fprintf(stderr, "qiji_duet: network worker failed (%d)\n", rc);
}
