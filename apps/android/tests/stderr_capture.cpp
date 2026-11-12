#include "stderr_capture.h"
#include <cstdio>
#include <cstring>

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    {
        StderrCapture capture(argv[1]);
        if (std::strcmp(argv[2], "failure") == 0) {
            if (capture.active()) return 3;
            std::fputs("capture unavailable\n", stderr);
            return 0;
        }
        if (!capture.active()) return 4;
        std::fputs("startup failed before JS\n", stderr);
        if (std::strcmp(argv[2], "explicit") == 0 && !capture.restore()) return 5;
    }
    std::fputs("original stderr restored\n", stderr);
    return 0;
}
