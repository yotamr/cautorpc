#include "cautorpc.h"
#include "example.h"
#include "debug.h"

int main(void)
{
    int rc;
    rc = crpc_client_init();
    if (0 != rc) {
        DEBUG("Error initializing crpc client (rc = %d)", rc);
        return 1;
    }

    struct my_struct_s a = {.x = 5};
    int out1;
    struct some_other_struct_s out2;
    struct some_other_struct_s *bla1;
    int bla1_size;
    _rpc_foo(FOO, 5, a, &out1, &out2, &bla1, &bla1_size);
    printf("out1 = %d, out2.y == %d, bla1_size = %d\n", out1, out2.y, bla1_size);
    for (int i = 0; i < bla1_size; i++) {
        printf("%d: %d\n", i, bla1[i].y);
    }
    return 0;
}
