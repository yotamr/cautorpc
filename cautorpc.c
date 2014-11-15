#include "cautorpc.h"
#include <jansson.h>
#include "debug.h"
#include <stdlib.h>

static struct {
    zsock_t *zsock;
} g_client_state;

int crpc_client_init(void)
{
    g_client_state.zsock = zsock_new_req("tcp://127.0.0.1:9000");
    if (NULL == g_client_state.zsock)  {
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
    zsock_destroy(&g_client_state.zsock);
}
