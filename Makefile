
.PHONY: all
all: v8c

libv8_g.so: include/v8c.h src/v8c.cc
	scons mode=debug library=shared -j2

v8c: include/v8c.h v8c-test.c libv8_g.so
	gcc -g -o v8c-test v8c-test.c -L. -lv8_g
