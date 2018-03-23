typedef struct {
    float x;
    float y;
} Point;

typedef enum {
    FOO_A = 1,
    FOO_B = 2,
    FOO_C = 3
} Foo;

Point example_get_origin(void);
void example_print_foo(Foo *);
