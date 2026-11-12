#pragma once

#include <fcntl.h>
#include <unistd.h>

// Process-wide redirection is confined to the one-shot Android :runtime process.
class StderrCapture {
    int previous_ = -1;
public:
    explicit StderrCapture(const char* path) {
        int log = open(path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
        if (log < 0) return;
        int previous = fcntl(STDERR_FILENO, F_DUPFD_CLOEXEC, 3);
        if (previous >= 0 && dup2(log, STDERR_FILENO) >= 0) previous_ = previous;
        else if (previous >= 0) close(previous);
        close(log);
    }
    StderrCapture(const StderrCapture&) = delete;
    StderrCapture& operator=(const StderrCapture&) = delete;
    bool active() const { return previous_ >= 0; }
    bool restore() {
        if (!active()) return false;
        int previous = previous_;
        previous_ = -1;
        int result = dup2(previous, STDERR_FILENO);
        close(previous);
        return result >= 0;
    }
    ~StderrCapture() { if (active()) restore(); }
};
