#pragma once

#include "../cautojson/autojson.h"


struct my_struct_s  {
    int x;
    JSONABLE;
};

struct some_other_struct_s {
    int y;
    JSONABLE;
};

enum bla_e {
    FOO
};


int _rpc_foo(enum bla_e a, int bla, struct my_struct_s s, /* Input parameters */
             int *out_a, struct some_other_struct_s *out_b, struct some_other_struct_s **out_bla2, int *out_bla2_size); /* Output parameters */
