// Fixed benign child fixtures. Not a shell, terminal broker or execution provider.
#include <sys/prctl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <signal.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
int main(int argc, char** argv) {
  if (argc != 2 || getuid() == 0) return 120;
  const char* owner = getenv("HARNESS_PTY_OWNER_PID");
  char* end = nullptr; const long expected = owner ? strtol(owner, &end, 10) : 0;
  if (expected <= 1 || !end || *end || prctl(PR_SET_PDEATHSIG,SIGKILL,0,0,0) || getppid() != expected) return 121;
  if (!isatty(0) || !isatty(1) || !isatty(2)) return 122;
  if (!strcmp(argv[1],"--ignore-term")) signal(SIGTERM,SIG_IGN);
  printf("IDENTITY:{\"uid\":%u,\"pid\":%d,\"parentPid\":%d}\n",getuid(),getpid(),getppid());
  if (!strcmp(argv[1],"--tty-child")) {
    winsize initial{}; if (ioctl(0,TIOCGWINSZ,&initial) || initial.ws_row!=24 || initial.ws_col!=80) return 123;
    printf("TTY-READY\n"); fflush(stdout);
    char input[64]; if (!fgets(input,sizeof(input),stdin)) return 124;
    input[strcspn(input,"\r\n")]=0;
    winsize size{}; if(ioctl(0,TIOCGWINSZ,&size)) return 125;
    printf("TTY-INPUT:%s ROWS:%u COLS:%u\n",input,size.ws_row,size.ws_col);
    fprintf(stderr,"TTY-STDERR\n");
    return strcmp(input,"pty-input") || size.ws_row!=40 || size.ws_col!=100 ? 126 : 0;
  }
  if (!strcmp(argv[1],"--exit-seven")) { printf("EXIT-SEVEN\n"); return 7; }
  if (strcmp(argv[1],"--wait") && strcmp(argv[1],"--ignore-term")) return 127;
  printf("READY\n"); fflush(stdout); for (;;) pause();
}
