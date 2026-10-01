#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int *p = malloc(sizeof *p);
    *p = 42;
    free(p);
    printf("%d\n", *p);
    return 0;
}
