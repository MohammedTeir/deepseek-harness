// Fixed OS capability qualification. No caller-selected command, root or terminal server.
#include <cerrno>
#include <chrono>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <iostream>
#include <poll.h>
#include <pty.h>
#include <stdexcept>
#include <string>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>
#include <vector>

namespace {
volatile sig_atomic_t cancelled = 0;
void stop(int) { cancelled = 1; }
using Clock = std::chrono::steady_clock;
std::string quoted(const std::string& s) {
    std::string out = "\"";
    for (unsigned char c : s) {
        if (c == '"' || c == '\\') { out += '\\'; out += static_cast<char>(c); }
        else if (c < 32) { char hex[7]; std::snprintf(hex, sizeof(hex), "\\u%04x", c); out += hex; }
        else out += static_cast<char>(c);
    }
    return out + '"';
}
struct Json {
    std::string body;
    Json& raw(const std::string& key, const std::string& value) { if (!body.empty()) body += ','; body += quoted(key)+':'+value; return *this; }
    Json& text(const std::string& key, const std::string& value) { return raw(key, quoted(value)); }
    Json& number(const std::string& key, long long value) { return raw(key, std::to_string(value)); }
    Json& flag(const std::string& key, bool value) { return raw(key, value ? "true" : "false"); }
    std::string str() const { return '{'+body+'}'; }
};
void require(bool value, const std::string& what) { if (!value) throw std::runtime_error(what); }
struct Fd {
    int value = -1;
    explicit Fd(int fd = -1): value(fd) {}
    ~Fd() { if (value >= 0) ::close(value); }
    Fd(const Fd&) = delete; Fd& operator=(const Fd&) = delete;
    void reset() { if (value >= 0) ::close(value); value = -1; }
};
void write_all(int fd, const std::string& bytes) {
    size_t offset = 0;
    while (offset < bytes.size()) {
        ssize_t n = ::write(fd, bytes.data()+offset, bytes.size()-offset);
        if (n < 0 && errno == EINTR) continue;
        require(n > 0, "write failed errno="+std::to_string(errno)); offset += static_cast<size_t>(n);
    }
}
std::string self_path() { char buf[4096]; ssize_t n = readlink("/proc/self/exe", buf, sizeof(buf)-1); require(n > 0, "self executable unavailable"); return std::string(buf, static_cast<size_t>(n)); }
void bind_parent_death(pid_t expected) {
    if (prctl(PR_SET_PDEATHSIG,SIGKILL,0,0,0) < 0 || getppid()!=expected) {
        dprintf(2,"native worker parent-death setup failed errno=%d\n",errno); _exit(126);
    }
}
struct Child {
    pid_t pid = -1; int status = 0; bool reaped = false;
    bool collect() {
        if (reaped) return true;
        pid_t result = waitpid(pid, &status, WNOHANG);
        if (result == pid) reaped = true;
        else if (result < 0 && errno != EINTR) throw std::runtime_error("waitpid failed errno="+std::to_string(errno));
        return reaped;
    }
    void signal(int sig) {
        if (reaped) return;
        // Only signal the new child's group when the kernel confirms ownership.
        if (getpgid(pid) == pid) { if (kill(-pid, sig) == 0) return; }
        if (kill(pid, sig) < 0 && errno != ESRCH) throw std::runtime_error("signal failed errno="+std::to_string(errno));
    }
    void terminate() {
        if (pid <= 0 || collect()) return;
        signal(SIGTERM);
        auto deadline = Clock::now()+std::chrono::seconds(1);
        while (!collect() && Clock::now() < deadline) poll(nullptr, 0, 10);
        if (!reaped) signal(SIGKILL);
        deadline = Clock::now()+std::chrono::seconds(2);
        while (!collect() && Clock::now() < deadline) poll(nullptr, 0, 10);
        require(reaped, "child did not reap after KILL");
        dprintf(2,"HARNESS_PROCESS_REAPED pid=%d\n",pid);
    }
    ~Child() { if (pid > 0 && !reaped) { try { terminate(); } catch (...) { std::terminate(); } } }
    Child() = default; Child(const Child&) = delete; Child& operator=(const Child&) = delete;
};
void nonblocking(int fd) { int flags = fcntl(fd, F_GETFL); require(flags >= 0 && fcntl(fd, F_SETFL, flags|O_NONBLOCK) == 0, "nonblocking failed"); }
struct Capture { std::string out, err; int outReads = 0, errReads = 0; bool beforeExit = false; bool timedOut = false; };
void drain(int fd, std::string& text, int& reads, bool pty = false) {
    char bytes[1024];
    for (;;) {
        ssize_t n = read(fd, bytes, sizeof(bytes));
        if (n > 0) { require(text.size()+static_cast<size_t>(n) <= 65536, "output exceeded cap"); text.append(bytes, static_cast<size_t>(n)); ++reads; }
        else if (n == 0 || (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK || (pty && errno == EIO)))) return;
        else if (errno != EINTR) throw std::runtime_error("read failed errno="+std::to_string(errno));
    }
}
const char* shell_path() {
#ifdef __ANDROID__
    return "/system/bin/sh";
#else
    return "/bin/sh"; // Host qualification only, never an Android fallback.
#endif
}
void exec_child(const std::string& exe, const char* mode) {
    char* const argv[] = {const_cast<char*>(exe.c_str()), const_cast<char*>(mode), nullptr};
    char* const env[] = {const_cast<char*>("PATH=/system/bin"), nullptr};
    execve(exe.c_str(), argv, env);
    const int failure = errno;
    dprintf(STDERR_FILENO, "exec errno=%d\n", failure); _exit(127);
}
Json pipe_case(const std::string& exe, const char* mode, int milliseconds, bool explicitCancel = false) {
    int output[2], error[2], input[2];
    require(pipe2(output, O_CLOEXEC) == 0, "stdout pipe failed"); Fd outRead(output[0]), outWrite(output[1]);
    require(pipe2(error, O_CLOEXEC) == 0, "stderr pipe failed"); Fd errRead(error[0]), errWrite(error[1]);
    require(pipe2(input, O_CLOEXEC) == 0, "stdin pipe failed"); Fd inRead(input[0]), inWrite(input[1]);
    pid_t parent=getpid(); Child child; child.pid = fork(); require(child.pid >= 0, "fork failed");
    if (child.pid == 0) {
        bind_parent_death(parent);
        if (setpgid(0, 0) < 0 || dup2(inRead.value, STDIN_FILENO) < 0 || dup2(outWrite.value, STDOUT_FILENO) < 0 || dup2(errWrite.value, STDERR_FILENO) < 0) _exit(126);
        exec_child(exe, mode);
    }
    outWrite.reset(); errWrite.reset(); inRead.reset(); nonblocking(outRead.value); nonblocking(errRead.value);
    Capture data; bool ack = false; bool ready = false; const bool needsReady = std::string(mode)=="--ignore-term";
    auto deadline = Clock::now()+(needsReady ? std::chrono::milliseconds(4000) : std::chrono::milliseconds(milliseconds));
    while (!child.collect()) {
        if (cancelled) throw std::runtime_error("suite cancelled");
        struct pollfd fds[] = {{outRead.value,POLLIN,0},{errRead.value,POLLIN,0}};
        require(poll(fds, 2, 20) >= 0 || errno == EINTR, "poll failed");
        drain(outRead.value, data.out, data.outReads); drain(errRead.value, data.err, data.errReads);
        if (!ack && data.out.find("OUT-1\n") != std::string::npos) {
            data.beforeExit = !child.collect(); write_all(inWrite.value, "ack\n"); ack = true;
        }
        if (needsReady && !ready && data.out.find("READY\n") != std::string::npos) { ready = true; deadline = Clock::now()+std::chrono::milliseconds(milliseconds); dprintf(2,"HARNESS_PROCESS_READY pid=%d mode=--ignore-term\n",child.pid); }
        if (explicitCancel && data.out.find("READY\n") != std::string::npos) { child.terminate(); break; }
        if (Clock::now() >= deadline) { require(!needsReady || ready,"worker startup deadline before readiness"); data.timedOut = true; child.terminate(); break; }
    }
    drain(outRead.value, data.out, data.outReads); drain(errRead.value, data.err, data.errReads);
    int exitCode = WIFEXITED(child.status) ? WEXITSTATUS(child.status) : -1;
    int sig = WIFSIGNALED(child.status) ? WTERMSIG(child.status) : 0;
    Json summary; summary.number("pid",child.pid).number("exitCode",exitCode).number("signal",sig).flag("reaped",child.reaped)
        .flag("timedOut",data.timedOut).flag("explicitCancellation",explicitCancel).number("stdoutReads",data.outReads).number("stderrReads",data.errReads)
        .flag("streamObservedBeforeAckAndExit",data.beforeExit);
    auto case_require = [&](bool value, const std::string& reason) { require(value, reason+"; actual="+summary.str()); };
    if (std::string(mode) == "--burst") {
        case_require(data.out == std::string(16384,'A') && data.err == std::string(16384,'B') && exitCode == 9, "backpressure data/exit mismatch");
        summary.number("stdoutBytes",data.out.size()).number("stderrBytes",data.err.size()).flag("completeBytesVerified",true);
    } else {
        summary.text("stdout",data.out).text("stderr",data.err);
        if (std::string(mode) == "--emit") case_require(data.out == "OUT-1\nOUT-2\n" && data.err == "ERR-1\nERR-2\n" && exitCode == 7 && data.beforeExit, "streaming/result mismatch");
        if (std::string(mode) == "--missing") case_require(exitCode == 127 && data.err.find("exec errno=2") != std::string::npos, "missing executable error mismatch");
        if (std::string(mode) == "--ignore-term") case_require(data.timedOut && sig == SIGKILL, "KILL escalation not observed");
        if (explicitCancel && std::string(mode) != "--tree-child") case_require(sig == SIGTERM && !data.timedOut, "explicit TERM cancellation failed");
        if (std::string(mode) == "--tree-child") {
            auto start = data.out.find("GRANDCHILD:"); case_require(start != std::string::npos, "grandchild identity missing");
            pid_t grand = static_cast<pid_t>(std::stol(data.out.substr(start+11)));
            case_require(exitCode == 0 && data.out.find("GRANDCHILD-REAPED") != std::string::npos, "child did not acknowledge descendant reap");
            errno = 0; case_require(kill(grand,0) < 0 && errno == ESRCH, "descendant remains observable");
            summary.number("grandchildPid",grand).flag("descendantReaped",true);
        }
        if (std::string(mode) == "--shell") case_require(data.out.find("SH-OUT\n") == 0 && data.err == "SH-ERR\n" && exitCode == 7, "system shell result mismatch");
    }
    return summary;
}
struct PtyResult { Json report; bool passed; bool available; };
PtyResult pty_case(const std::string& exe) {
    int master = -1, slave = -1; struct winsize initial{}; initial.ws_row = 24; initial.ws_col = 80;
    if (openpty(&master, &slave, nullptr, nullptr, &initial) < 0) { int code=errno; return {Json().text("status","UNAVAILABLE").text("stage","openpty").number("errno",code),false,false}; }
    Fd masterFd(master), slaveFd(slave); pid_t parent=getpid(); Child child; child.pid = fork(); require(child.pid >= 0, "PTY fork failed");
    if (child.pid == 0) {
        bind_parent_death(parent);
        close(master);
        if (setsid() < 0 || ioctl(slave,TIOCSCTTY,0) < 0 || dup2(slave,0) < 0 || dup2(slave,1) < 0 || dup2(slave,2) < 0) _exit(126);
        // openpty descriptors do not necessarily have CLOEXEC.
        if (slave > 2) close(slave);
        exec_child(exe,"--tty-child");
    }
    slaveFd.reset(); nonblocking(master); std::string output; int reads = 0; bool sent = false;
    const auto deadline = Clock::now()+std::chrono::seconds(4);
    while (!child.collect()) {
        if (cancelled) throw std::runtime_error("suite cancelled");
        struct pollfd fd = {master,POLLIN,0}; require(poll(&fd,1,20)>=0 || errno==EINTR,"PTY poll failed");
        drain(master,output,reads,true);
        if (!sent && output.find("TTY-READY") != std::string::npos) {
            struct winsize resized{}; resized.ws_row = 40; resized.ws_col = 100;
            require(ioctl(master,TIOCSWINSZ,&resized)==0,"PTY resize failed"); write_all(master,"pty-input\n"); sent = true;
        }
        if (Clock::now() >= deadline) { child.terminate(); return {Json().text("status","FAIL").text("stage","pty-deadline").text("output",output),false,true}; }
    }
    drain(master,output,reads,true);
    bool passed = WIFEXITED(child.status) && WEXITSTATUS(child.status)==0 && sent && output.find("TTY-INPUT:pty-input ROWS:40 COLS:100")!=std::string::npos && output.find("TTY-STDERR")!=std::string::npos;
    return {Json().text("status",passed?"PASS":"FAIL").number("pid",child.pid).flag("reaped",child.reaped)
        .number("exitCode",WIFEXITED(child.status)?WEXITSTATUS(child.status):-1).text("combinedOutput",output)
        .flag("stdinStdoutStderrAreTty",passed).flag("resizeAndInputVerified",passed).flag("stderrMergedByPty",true),passed,true};
}
int worker(const std::string& mode) {
    if (mode == "--emit") { write_all(1,"OUT-1\n"); write_all(2,"ERR-1\n"); char input[8]; require(read(0,input,sizeof(input))>0,"missing stream ack"); write_all(1,"OUT-2\n"); write_all(2,"ERR-2\n"); return 7; }
    if (mode == "--burst") { for (int i=0;i<32;++i) { write_all(1,std::string(512,'A')); write_all(2,std::string(512,'B')); } return 9; }
    if (mode == "--wait" || mode == "--ignore-term") { if (mode == "--ignore-term") signal(SIGTERM,SIG_IGN); write_all(1,"READY\n"); for (;;) pause(); }
    if (mode == "--missing") { char cwd[4096]; require(getcwd(cwd,sizeof(cwd))!=nullptr,"missing-case cwd unavailable"); exec_child(std::string(cwd)+"/missing-uncreated-executable","unused"); }
    if (mode == "--shell") {
        const char* command="printf 'SH-OUT\\n'; printf 'SH-ERR\\n' >&2; pwd; exit 7";
        execl(shell_path(),shell_path(),"-c",command,static_cast<char*>(nullptr)); dprintf(2,"shell exec errno=%d\n",errno); return 127;
    }
    if (mode == "--tree-child") {
        pid_t parent=getpid(); pid_t grand=fork(); require(grand>=0,"grandchild fork failed");
        if (grand==0) { bind_parent_death(parent); for (;;) pause(); }
        struct sigaction action{}; action.sa_handler=stop; sigemptyset(&action.sa_mask); sigaction(SIGTERM,&action,nullptr);
        write_all(1,"GRANDCHILD:"+std::to_string(grand)+"\nREADY\n");
        int status=0; pid_t observed;
        do { observed=waitpid(grand,&status,0); } while (observed<0 && errno==EINTR);
        require(observed==grand && WIFSIGNALED(status) && WTERMSIG(status)==SIGTERM,"grandchild TERM/reap mismatch");
        write_all(1,"GRANDCHILD-REAPED\n"); return 0;
    }
    if (mode == "--tty-child") {
        if (!isatty(0)||!isatty(1)||!isatty(2)) return 20;
        write_all(1,"TTY-READY\n"); char line[64]; if (!fgets(line,sizeof(line),stdin)) return 21;
        std::string input(line); if (!input.empty() && input.back()=='\n') input.pop_back();
        struct winsize dimensions{}; if (ioctl(0,TIOCGWINSZ,&dimensions)<0) return 22;
        write_all(1,"TTY-INPUT:"+input+" ROWS:"+std::to_string(dimensions.ws_row)+" COLS:"+std::to_string(dimensions.ws_col)+"\n");
        write_all(2,"TTY-STDERR\n"); return 0;
    }
    return 125;
}
}
int main(int argc, char** argv) {
    try {
        signal(SIGPIPE,SIG_IGN);
        if (argc==2) return worker(argv[1]);
        require(argc==3 && std::string(argv[1])=="--suite", "Only fixed worker roles or --suite workspace accepted");
        struct stat st{}; char canonical[4096]; require(realpath(argv[2],canonical)!=nullptr && std::string(canonical)==argv[2],"Canonical workspace required");
        require(stat(canonical,&st)==0 && S_ISDIR(st.st_mode) && st.st_uid==getuid() && (st.st_mode&0077)==0,"Private owned workspace required");
        require(chdir(canonical)==0,"workspace chdir failed");
        struct sigaction action{}; action.sa_handler=stop; sigemptyset(&action.sa_mask); sigaction(SIGTERM,&action,nullptr); sigaction(SIGINT,&action,nullptr);
        const std::string exe=self_path();
#ifdef __ANDROID__
        require(access(exe.c_str(),W_OK)!=0,"Native executable must be installer-owned and not writable");
#endif
        Json cases;
        cases.raw("streaming",pipe_case(exe,"--emit",4000).str()).raw("backpressure",pipe_case(exe,"--burst",4000).str())
            .raw("missingExecutable",pipe_case(exe,"--missing",4000).str()).raw("cancellation",pipe_case(exe,"--wait",4000,true).str())
            .raw("timeoutAndKill",pipe_case(exe,"--ignore-term",200).str()).raw("descendantGroup",pipe_case(exe,"--tree-child",4000,true).str());
        struct stat shell{};
        bool shellAvailable=stat(shell_path(),&shell)==0 && access(shell_path(),X_OK)==0 && (shell.st_mode&(S_ISUID|S_ISGID))==0 && access(shell_path(),W_OK)!=0;
        if (shellAvailable) cases.raw("systemShell",pipe_case(exe,"--shell",4000).str());
        else cases.raw("systemShell",Json().text("status","UNAVAILABLE").text("reason","System shell missing, inaccessible, set-ID or writable; no fallback").number("errno",errno).str());
        Json discovery;
        for (const char* name : {"sh","pwd","printf","cat","sleep","echo","stty","toybox","git","curl","python3","ssh"}) {
            const std::string path="/system/bin/"+std::string(name); errno=0; bool available=access(path.c_str(),X_OK)==0; int code=available?0:errno;
            discovery.raw(name,Json().text("path",path).flag("executable",available).number("errno",code).str());
        }
        PtyResult pty=pty_case(exe); struct utsname system{}; require(uname(&system)==0,"uname failed");
        bool ptyPassed=pty.passed;
        Json result; result.number("schemaVersion",1).text("platform",
#ifdef __ANDROID__
            "android"
#else
            "linux-host-only"
#endif
        ).text("suite","android-process-capability-v1").text("status",(ptyPassed && shellAvailable)?"PASS":(pty.available && !ptyPassed)?"FAIL":"PARTIAL")
            .number("uid",getuid()).number("pid",getpid()).number("parentPid",getppid()).text("kernel",system.release).text("architecture",system.machine)
            .text("execPath",exe).text("cwd",canonical).raw("cases",cases.str()).raw("discovery",discovery.str()).raw("pty",pty.report.str()).text("shellTestPath",shell_path())
            .flag("nativeWorkersRequireParentDeathKill",true).flag("generalShellProviderImplemented",false).flag("originalTerminalIntegrated",false).flag("descendantTreeCleanupTested",true).text("descendantCleanupScope","cooperative native worker group; not arbitrary trees or OS process death").flag("gate3Passed",false);
        std::cout<<result.str()<<std::endl; return pty.available && !ptyPassed ? 1 : 0;
    } catch (const std::exception& error) {
        std::cout<<Json().number("schemaVersion",1).text("suite","android-process-capability-v1").text("status",cancelled?"CANCELLED":"FAIL").text("failure",error.what()).number("errno",errno).flag("gate3Passed",false).str()<<std::endl;
        return 1;
    }
}
