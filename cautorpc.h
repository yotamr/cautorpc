#ifndef __AUTOJSON_H__
#define __AUTOJSON_H__

#include <jansson.h>
#include <czmq.h>

#define CRPC_SUCCESS (1)

typedef void (*PNOTIF_CALLBACK)(json_t *res);
void register_notif_callback(PNOTIF_CALLBACK cb);

int crpc_client_init(char *uri, char *uri_notif);
json_t *crpc_make_request(json_t *request);
void crpc_client_fini(void);

#endif
