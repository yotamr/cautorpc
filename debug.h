#pragma once
#include <stdio.h>

#ifdef __DEBUG
#define DEBUG(fmt, ...) do { fprintf(stderr, "%s:%d:%s():" fmt "\n", __FILE__, __LINE__, __func__, __VA_ARGS__); } while (0)
#else
#define DEBUG(...)
#endif
