#include <stdio.h>
#include <unistd.h>

/* Fixed harmless executable used only to test installer-owned code execution. */
int main(void) {
    return printf("{\"uid\":%ld,\"pid\":%ld,\"pageSize\":%ld}\n",
                  (long)getuid(), (long)getpid(), sysconf(_SC_PAGESIZE)) < 0 ? 1 : 0;
}
