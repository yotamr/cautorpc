#include "cautorpc.h"
#include <jansson.h>
#include "debug.h"
#include <stdlib.h>
#include <pthread.h>
#include <unistd.h>

static struct {
    zsock_t *zsock;
    zsock_t *zsock_notification;
    pthread_t thread;
} g_client_state;

#define DEFAULT_URI "tcp://127.0.0.1:9000"
#define DEFAULT_NOTIFICATION_URI "tcp://127.0.0.1:9001"

#define NOTIF_TYPE "N"

PNOTIF_CALLBACK g_notif_cb = NULL;

void register_notif_callback(PNOTIF_CALLBACK cb)
{
    g_notif_cb = cb;
}

void *listener_thread(void *arg)
{
    while (1) {
        json_error_t err;
        char *response = zstr_recv(g_client_state.zsock_notification);
        if (!response) {
            fprintf(stderr, "Received NULL notification, exiting\n");
            return NULL;
        }

        if (!strcmp(response, NOTIF_TYPE))
            continue;

        json_t *result = json_loads(response, 0, &err);
        if (NULL == result) {
            DEBUG("Error parsing result %d", 1);
            continue;
        }

        if (g_notif_cb)
            g_notif_cb(result);
    }
}

int crpc_client_init(char *uri, char *uri_notif)
{
    int ret;
    pthread_attr_t attr;

    if (uri == NULL) {
        uri = DEFAULT_URI;
    }

    if (uri_notif == NULL) {
        uri_notif = DEFAULT_NOTIFICATION_URI;
    }

    g_client_state.zsock = zsock_new_req(uri);
    if (NULL == g_client_state.zsock)  {
        return -1;
    }

    g_client_state.zsock_notification = zsock_new_sub(uri_notif, NOTIF_TYPE);
    if (NULL == g_client_state.zsock_notification) {
        //TODO: Cleanups...
        return -1;
    }

    zsocket_connect(g_client_state.zsock_notification, NULL);

    if (pthread_attr_init(&attr) != 0) {
        //TODO: Cleanups...
        return -1;
    }

    ret = pthread_create(&g_client_state.thread, &attr, listener_thread, NULL);
    if (ret < 0) {
        /* Cleanups.. */
        return -1;
    }

    return 0;
}

json_t *crpc_make_request(json_t *request)
{
    char *json_str = json_dumps(request, 0);
    json_error_t err;
    if (NULL == json_str) {
        DEBUG("Could not serialized json request %p to string", request);
        return NULL;
    }

    int rc = zstr_send(g_client_state.zsock, json_str);
    free(json_str);
    DEBUG("zstr_send_rc = %d", rc);
    if (0 != rc) {
        return NULL;
    }

    char *response = zstr_recv(g_client_state.zsock);
    if (NULL == response) {
        DEBUG("Error receiving response from remote end. %d", 1);
        return NULL;
    }

    json_t *result = json_loads(response, 0, &err);
    if (NULL == result) {
        DEBUG("Error parsing result %d", 1);
    }

    return result;
}

void crpc_client_fini(void)
{
    pthread_cancel(g_client_state.thread);
    pthread_join(g_client_state.thread, NULL);
    zsock_destroy(&g_client_state.zsock);
    zsock_destroy(&g_client_state.zsock_notification);
}
