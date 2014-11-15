all: libcrpc.a libcrpc.so

CFLAGS:=-Wall $(__DEBUG) -fPIC -c -g -Werror -std=c99
TEST_FILES:=test_client
TEST_OBJS=$(TEST_FILES:%=%.o)
SO_LIBS=-lczmq -ljansson
LIBCRPC_FILES:=cautorpc
LIBCRPC_OBJS=$(LIBCRPC_FILES:%=%.o)

libcrpc.a: $(LIBCRPC_OBJS)
	 ar cr libcrpc.a $(LIBCRPC_OBJS)

libcrpc.so: $(LIBCRPC_OBJS)
	gcc -shared $^ $(SO_LIBS) -o $@

example_structs.h example_structs.c:
	python /home/yotam/Code/cautojson/autojson.py example.h example_structs.h example_structs.c

example.c: example_structs.h
	python cautorpc.py example.h example_structs.h example.c

test_client: $(TEST_OBJS) libcrpc example.o example_structs.o
	gcc libcrpc.a $(TEST_OBJS) example.o -ljansson example_structs.o libcrpc.a -lczmq -o ./test_client

clean:
	rm -f *.o test_client *.a example.c example_structs.c example_structs.h
