// Fixed filesystem qualification only. No Harness persistence or arbitrary
// execution API.
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fcntl.h>
#include <functional>
#include <iostream>
#include <poll.h>
#include <signal.h>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/prctl.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/syscall.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>

namespace {
constexpr unsigned noReplace =
    1; // Linux UAPI RENAME_NOREPLACE; no Bionic API-30 wrapper.
constexpr int publishers = 8;
constexpr int rounds = 16;
std::string quote(const std::string &s) {
  std::ostringstream out;
  out << '"';
  for (unsigned char c : s) {
    if (c == '"' || c == '\\')
      out << '\\' << c;
    else if (c < 32) {
      const char *hex = "0123456789abcdef";
      out << "\\u00" << hex[c >> 4] << hex[c & 15];
    } else
      out << c;
  }
  return out.str() + '"';
}
std::string code(int e) {
  switch (e) {
  case 0:
    return "OK";
  case EEXIST:
    return "EEXIST";
  case ENOENT:
    return "ENOENT";
  case EACCES:
    return "EACCES";
  case EPERM:
    return "EPERM";
  case EINVAL:
    return "EINVAL";
  case ENOSYS:
    return "ENOSYS";
  case EOPNOTSUPP:
    return "EOPNOTSUPP";
  case EBADF:
    return "EBADF";
  case ELOOP:
    return "ELOOP";
  case EIO:
    return "EIO";
  default:
    return "ERRNO_" + std::to_string(e);
  }
}
struct Failure : std::runtime_error {
  int number;
  Failure(const std::string &s, int e) : std::runtime_error(s), number(e) {}
};
void require(bool ok, const std::string &why) {
  if (!ok)
    throw Failure(why, 0);
}
void check(int rc, const std::string &op) {
  if (rc < 0) {
    const int e = errno;
    throw Failure(op + ": " + std::strerror(e), e);
  }
}
struct Fd {
  int n;
  explicit Fd(int fd) : n(fd) { check(fd, "open/pipe descriptor"); }
  ~Fd() { close(n); }
  Fd(const Fd &) = delete;
  Fd &operator=(const Fd &) = delete;
};
void writeAll(int fd, const void *data, size_t len) {
  auto p = static_cast<const char *>(data);
  while (len) {
    ssize_t n = write(fd, p, len);
    if (n < 0 && errno == EINTR)
      continue;
    check(static_cast<int>(n), "write");
    require(n > 0, "short write");
    len -= n;
    p += n;
  }
}
void readAll(int fd, void *data, size_t len) {
  auto p = static_cast<char *>(data);
  while (len) {
    struct pollfd watched {
      fd, POLLIN, 0
    };
    int available;
    do {
      available = poll(&watched, 1, 10000);
    } while (available < 0 && errno == EINTR);
    check(available, "poll child evidence");
    require(available > 0, "child evidence deadline exceeded");
    ssize_t n = read(fd, p, len);
    if (n < 0 && errno == EINTR)
      continue;
    check(static_cast<int>(n), "read barrier");
    require(n > 0, "child barrier closed before evidence");
    len -= n;
    p += n;
  }
}
struct Pipe {
  int fds[2];
  Pipe() { check(pipe2(fds, O_CLOEXEC), "pipe2"); }
  ~Pipe() {
    close(fds[0]);
    close(fds[1]);
  }
};
// Own every child until waitpid confirms exit, including exception/timeout
// paths.
struct Children {
  std::vector<pid_t> ids;
  ~Children() {
    for (pid_t id : ids)
      if (id > 0) {
        kill(id, SIGKILL);
        while (waitpid(id, nullptr, 0) < 0 && errno == EINTR) {
        }
      }
  }
  pid_t start() {
    pid_t parent = getpid();
    pid_t id = fork();
    check(id, "fork");
    if (id == 0) {
      if (prctl(PR_SET_PDEATHSIG, SIGKILL) < 0 || getppid() != parent)
        _exit(121);
      alarm(30);
    } else
      ids.push_back(id);
    return id;
  }
  int wait(pid_t id) {
    int status = 0;
    pid_t r;
    do {
      r = waitpid(id, &status, 0);
    } while (r < 0 && errno == EINTR);
    check(r, "waitpid");
    for (auto &stored : ids)
      if (stored == id)
        stored = 0;
    return status;
  }
};
bool basenameOnly(const std::string &name) {
  if (name.empty() || name == "." || name == ".." || name.size() > 120)
    return false;
  for (char c : name)
    if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-' ||
          c == '.'))
      return false;
  return true;
}
using RenameCall = long (*)(int, const char *, int, const char *, unsigned);
long nativeRename(int a, const char *b, int c, const char *d, unsigned flags) {
#ifdef SYS_renameat2
  return syscall(SYS_renameat2, a, b, c, d, flags);
#else
  errno = ENOSYS;
  return -1;
#endif
}
// Consumes a regular staging name on success. Both names are fixed basenames in
// one pinned dirfd. Caller owns trusted staging names; this is not isolation
// from malicious same-UID mutation.
int publish(int dir, const std::string &source, const std::string &target,
            RenameCall call = nativeRename) {
  if (!basenameOnly(source) || !basenameOnly(target) || source == target) {
    errno = EINVAL;
    return -1;
  }
  struct stat st {};
  if (fstatat(dir, source.c_str(), &st, AT_SYMLINK_NOFOLLOW) < 0)
    return -1;
  if (!S_ISREG(st.st_mode)) {
    errno = EINVAL;
    return -1;
  }
  return static_cast<int>(
      call(dir, source.c_str(), dir, target.c_str(), noReplace));
}
void syncFd(int fd) { check(fsync(fd), "fsync"); }
Fd subdir(int root, const std::string &name) {
  check(mkdirat(root, name.c_str(), 0700), "mkdirat unique test");
  syncFd(root);
  return Fd(openat(root, name.c_str(),
                   O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
}
struct stat info(int dir, const std::string &name) {
  struct stat st {};
  check(fstatat(dir, name.c_str(), &st, AT_SYMLINK_NOFOLLOW),
        "fstatat " + name);
  return st;
}
bool exists(int dir, const std::string &name) {
  struct stat st {};
  if (fstatat(dir, name.c_str(), &st, AT_SYMLINK_NOFOLLOW) == 0)
    return true;
  if (errno == ENOENT)
    return false;
  check(-1, "inspect existence");
  return false;
}
std::string content(int dir, const std::string &name) {
  Fd fd(openat(dir, name.c_str(), O_RDONLY | O_NOFOLLOW | O_CLOEXEC));
  std::string out;
  char buffer[4096];
  for (;;) {
    ssize_t n = read(fd.n, buffer, sizeof(buffer));
    if (n < 0 && errno == EINTR)
      continue;
    check(static_cast<int>(n), "read file");
    if (!n)
      break;
    out.append(buffer, n);
    require(out.size() <= 131072, "diagnostic file too large");
  }
  return out;
}
void stage(int dir, const std::string &name, const std::string &bytes,
           bool sync = true) {
  Fd fd(openat(dir, name.c_str(),
               O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600));
  writeAll(fd.n, bytes.data(), bytes.size());
  if (sync)
    syncFd(fd.n);
}
void remove(int dir, const std::string &name) {
  check(unlinkat(dir, name.c_str(), 0), "unlinkat " + name);
}
std::string metadata(const struct stat &st) {
  return "{\"inode\":" + quote(std::to_string(st.st_ino)) +
         ",\"device\":" + quote(std::to_string(st.st_dev)) +
         ",\"mode\":" + std::to_string(st.st_mode) +
         ",\"uid\":" + std::to_string(st.st_uid) +
         ",\"gid\":" + std::to_string(st.st_gid) +
         ",\"size\":" + std::to_string(st.st_size) +
         ",\"links\":" + std::to_string(st.st_nlink) +
         ",\"mtimeSeconds\":" + quote(std::to_string(st.st_mtim.tv_sec)) +
         ",\"mtimeNanos\":" + std::to_string(st.st_mtim.tv_nsec) +
         ",\"ctimeSeconds\":" + quote(std::to_string(st.st_ctim.tv_sec)) +
         ",\"ctimeNanos\":" + std::to_string(st.st_ctim.tv_nsec) + "}";
}
std::string success(int root) {
  Fd dir = subdir(root, "success");
  const std::string bytes = "atomic native publication\n";
  stage(dir.n, "pending", bytes);
  auto before = info(dir.n, "pending");
  check(publish(dir.n, "pending", "published"), "renameat2 RENAME_NOREPLACE");
  syncFd(dir.n);
  auto after = info(dir.n, "published");
  require(before.st_ino == after.st_ino && before.st_dev == after.st_dev,
          "inode identity changed");
  require(content(dir.n, "published") == bytes, "published bytes differ");
  require(!exists(dir.n, "pending"), "staging name not consumed");
  remove(dir.n, "published");
  syncFd(dir.n);
  require(!exists(dir.n, "published"), "cleanup failed");
  return "{\"fileFsync\":true,\"directoryFsync\":true,\"sameInode\":true,"
         "\"sourceConsumed\":true,\"cleanupSynced\":true,"
         "\"publishedIdentity\":" +
         metadata(after) + "}";
}
std::string collision(int root) {
  Fd dir = subdir(root, "collision");
  const std::string original = "existing destination must survive\n";
  stage(dir.n, "published", original);
  syncFd(dir.n);
  auto before = info(dir.n, "published");
  stage(dir.n, "pending", "replacement forbidden\n");
  errno = 0;
  int rc = publish(dir.n, "pending", "published");
  int e = errno;
  require(rc == -1 && e == EEXIST,
          "collision did not return EEXIST: " + code(e));
  auto after = info(dir.n, "published");
  const auto afterBytes = content(dir.n, "published");
  require(metadata(before) == metadata(after) && afterBytes == original,
          "existing file content or metadata changed");
  require(content(dir.n, "pending") == "replacement forbidden\n",
          "collision consumed stage");
  remove(dir.n, "pending");
  syncFd(dir.n);
  // Destination symlink is also an occupied name; never follow or replace it.
  check(symlinkat("published", dir.n, "alias"), "symlinkat target");
  stage(dir.n, "second", "second");
  rc = publish(dir.n, "second", "alias");
  e = errno;
  require(rc == -1 && e == EEXIST && S_ISLNK(info(dir.n, "alias").st_mode),
          "destination symlink was replaced");
  remove(dir.n, "second");
  remove(dir.n, "alias");
  syncFd(dir.n);
  return "{\"errno\":" + std::to_string(EEXIST) +
         ",\"code\":\"EEXIST\",\"beforeContent\":" + quote(original) +
         ",\"afterContent\":" + quote(afterBytes) +
         ",\"before\":" + metadata(before) + ",\"after\":" + metadata(after) +
         ",\"destinationSymlinkProtected\":true,\"loserCleanupSynced\":true}";
}
std::string concurrency(int root) {
  Fd group = subdir(root, "concurrency");
  std::ostringstream results;
  results << '[';
  for (int round = 0; round < rounds; ++round) {
    Fd dir = subdir(group.n, "round-" + std::to_string(round));
    Pipe ready, gate, done;
    Children children;
    std::vector<pid_t> pids;
    std::vector<std::string> values;
    for (int i = 0; i < publishers; ++i)
      values.push_back("publisher-" + std::to_string(i) + ":" +
                       std::string(32768, static_cast<char>('a' + i)) + "\n");
    struct Reply {
      int pid;
      int error;
    };
    for (int i = 0; i < publishers; ++i) {
      pid_t pid = children.start();
      if (pid == 0) {
        try {
          stage(dir.n, "pending-" + std::to_string(i), values[i]);
          const char marker = 'r';
          writeAll(ready.fds[1], &marker, 1);
          char go;
          readAll(gate.fds[0], &go, 1);
          int rc = publish(dir.n, "pending-" + std::to_string(i), "published");
          int e = rc == 0 ? 0 : errno;
          if (rc == 0)
            syncFd(dir.n);
          Reply reply{static_cast<int>(getpid()), e};
          writeAll(done.fds[1], &reply, sizeof(reply));
          _exit(0);
        } catch (...) {
          _exit(122);
        }
      }
      pids.push_back(pid);
    }
    for (int i = 0; i < publishers; ++i) {
      char marker;
      readAll(ready.fds[0], &marker, 1);
      require(marker == 'r', "bad ready marker");
    }
    Pipe observerReady, observerStop, observerDone;
    const pid_t observer = children.start();
    if (observer == 0) {
      try {
        const char readyMarker = 'r';
        writeAll(observerReady.fds[1], &readyMarker, 1);
        int completeReads = 0;
        for (;;) {
          struct pollfd stop {
            observerStop.fds[0], POLLIN, 0
          };
          int stopped = poll(&stop, 1, 1);
          check(stopped, "observer stop poll");
          try {
            const auto bytes = content(dir.n, "published");
            bool complete = false;
            for (const auto &value : values)
              if (bytes == value)
                complete = true;
            require(complete, "independent observer saw partial final bytes");
            ++completeReads;
          } catch (const Failure &failure) {
            if (failure.number != ENOENT)
              throw;
          }
          if (stopped > 0)
            break;
        }
        require(completeReads > 0, "independent observer saw no final file");
        writeAll(observerDone.fds[1], &completeReads, sizeof(completeReads));
        _exit(0);
      } catch (...) {
        _exit(124);
      }
    }
    char observerMarker;
    readAll(observerReady.fds[0], &observerMarker, 1);
    require(observerMarker == 'r', "observer did not start");
    for (int i = 0; i < publishers; ++i) {
      const char go = 'g';
      writeAll(gate.fds[1], &go, 1);
    }
    int won = 0, lost = 0, observations = 0;
    std::string winning;
    std::ostringstream pidList;
    pidList << '[';
    for (int i = 0; i < publishers; ++i) {
      Reply reply{};
      readAll(done.fds[0], &reply, sizeof(reply));
      bool known = false;
      for (pid_t p : pids)
        if (p == reply.pid)
          known = true;
      require(known, "unexpected publisher PID");
      if (i)
        pidList << ',';
      pidList << reply.pid;
      if (reply.error == 0)
        ++won;
      else if (reply.error == EEXIST)
        ++lost;
      else
        throw Failure("concurrent publication", reply.error);
      const auto bytes = content(dir.n, "published");
      bool complete = false;
      for (const auto &value : values)
        if (bytes == value)
          complete = true;
      require(complete, "observer saw partial or foreign final file");
      if (!winning.empty())
        require(winning == bytes, "winner overwritten");
      winning = bytes;
      ++observations;
    }
    pidList << ']';
    for (pid_t pid : pids) {
      int status = children.wait(pid);
      require(WIFEXITED(status) && WEXITSTATUS(status) == 0,
              "publisher exit failed");
    }
    require(won == 1 && lost == publishers - 1,
            "incorrect independent-process winners");
    const char stopObserver = 's';
    writeAll(observerStop.fds[1], &stopObserver, 1);
    int observerReads = 0;
    readAll(observerDone.fds[0], &observerReads, sizeof(observerReads));
    const int observerStatus = children.wait(observer);
    require(WIFEXITED(observerStatus) && WEXITSTATUS(observerStatus) == 0 &&
                observerReads > 0,
            "independent observer failed");
    for (int i = 0; i < publishers; ++i) {
      const auto name = "pending-" + std::to_string(i);
      if (exists(dir.n, name))
        remove(dir.n, name);
    }
    syncFd(dir.n);
    const auto preserved = info(dir.n, "published");
    stage(dir.n, "late", "late replacement");
    int rc = publish(dir.n, "late", "published");
    int e = errno;
    require(rc == -1 && e == EEXIST &&
                metadata(info(dir.n, "published")) == metadata(preserved) &&
                content(dir.n, "published") == winning,
            "late publisher replaced winner");
    remove(dir.n, "late");
    syncFd(dir.n);
    if (round)
      results << ',';
    results << "{\"round\":" << round << ",\"pids\":" << pidList.str()
            << ",\"successes\":" << won << ",\"collisions\":" << lost
            << ",\"completeReadObservations\":" << observations
            << ",\"independentObserverPid\":" << observer
            << ",\"independentObserverCompleteReads\":" << observerReads
            << ",\"lateCollisionProtected\":true}";
  }
  results << ']';
  return "{\"processesPerRound\":" + std::to_string(publishers) +
         ",\"rounds\":" + std::to_string(rounds) +
         ",\"totalPublishers\":" + std::to_string(publishers * rounds) +
         ",\"totalIndependentObservers\":" + std::to_string(rounds) +
         ",\"roundResults\":" + results.str() + "}";
}
std::string interruptions(int root) {
  Fd group = subdir(root, "interruptions");
  std::ostringstream results;
  results << '[';
  const char *names[] = {"before-file-sync", "after-file-sync",
                         "after-publish-before-directory-sync",
                         "after-directory-sync", "during-cleanup"};
  const std::string bytes = "complete interrupted publication\n";
  for (int boundary = 0; boundary < 5; ++boundary)
    for (int iteration = 0; iteration < 2; ++iteration) {
      Fd dir = subdir(group.n, "case-" + std::to_string(boundary) + "-" +
                                   std::to_string(iteration));
      Pipe ready;
      Children children;
      pid_t pid = children.start();
      if (pid == 0) {
        try {
          stage(dir.n, "pending", bytes, false);
          if (boundary >= 1) {
            Fd file(
                openat(dir.n, "pending", O_RDONLY | O_NOFOLLOW | O_CLOEXEC));
            syncFd(file.n);
          }
          if (boundary >= 2)
            check(publish(dir.n, "pending", "published"),
                  "interrupt publication");
          if (boundary >= 3)
            syncFd(dir.n);
          if (boundary == 4) {
            stage(dir.n, "orphan-a", "unused stage a");
            stage(dir.n, "orphan-b", "unused stage b");
            syncFd(dir.n);
            remove(dir.n, "orphan-a");
          }
          const char marker = 'k';
          writeAll(ready.fds[1], &marker, 1);
          for (;;)
            pause();
        } catch (...) {
          _exit(123);
        }
      }
      char marker;
      readAll(ready.fds[0], &marker, 1);
      require(marker == 'k', "interrupt checkpoint missing");
      check(kill(pid, SIGKILL), "SIGKILL checkpoint child");
      const int status = children.wait(pid);
      require(WIFSIGNALED(status) && WTERMSIG(status) == SIGKILL,
              "child not killed at checkpoint");
      // Reopen by directory name to inspect state after child death, not
      // through its file handle.
      Fd reopened(openat(
          group.n,
          ("case-" + std::to_string(boundary) + "-" + std::to_string(iteration))
              .c_str(),
          O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
      const bool published = exists(reopened.n, "published");
      require(published == (boundary >= 2), "unexpected post-kill final state");
      require(exists(reopened.n, "pending") == !published,
              "unexpected post-kill stage state");
      require(content(reopened.n, published ? "published" : "pending") == bytes,
              "post-kill bytes incomplete");
      if (boundary == 4)
        require(!exists(reopened.n, "orphan-a") &&
                    exists(reopened.n, "orphan-b"),
                "cleanup boundary differs");
      for (const auto &name : {"pending", "orphan-a", "orphan-b"})
        if (exists(reopened.n, name))
          remove(reopened.n, name);
      syncFd(reopened.n);
      if (boundary || iteration)
        results << ',';
      results << "{\"boundary\":" << quote(names[boundary])
              << ",\"iteration\":" << iteration << ",\"pid\":" << pid
              << ",\"signal\":9,\"published\":"
              << (published ? "true" : "false") << ",\"fileFsyncAcknowledged\":"
              << (boundary >= 1 ? "true" : "false")
              << ",\"directoryFsyncAcknowledged\":"
              << (boundary >= 3 ? "true" : "false") << ",\"classification\":"
              << quote(boundary < 2 ? "unpublished-temporary"
                       : boundary == 2
                           ? "published-durability-unconfirmed"
                           : "published-directory-sync-acknowledged")
              << ",\"recoveryCleanupSynced\":true}";
    }
  results << ']';
  return "{\"iterationsPerBoundary\":2,\"cases\":" + results.str() +
         ",\"powerLossTested\":false}";
}
long missingSyscall(int, const char *, int, const char *, unsigned) {
  errno = ENOSYS;
  return -1;
}
long invalidSyscall(int, const char *, int, const char *, unsigned) {
  errno = EINVAL;
  return -1;
}
long unsupportedSyscall(int, const char *, int, const char *, unsigned) {
  errno = EOPNOTSUPP;
  return -1;
}
std::string errors(int root) {
  Fd dir = subdir(root, "errors");
  stage(dir.n, "pending", "error source");
  for (const auto &name : {"../escape", "a/b", "..", ".", ""}) {
    int rc = publish(dir.n, "pending", name);
    int e = errno;
    require(rc == -1 && e == EINVAL, "unsafe basename accepted");
  }
  int rc = publish(dir.n, "missing", "published");
  int e = errno;
  require(rc == -1 && e == ENOENT, "missing source not propagated");
  rc = publish(-1, "pending", "published");
  e = errno;
  require(rc == -1 && e == EBADF, "bad descriptor not propagated");
  check(symlinkat("pending", dir.n, "source-alias"), "symlinkat source");
  rc = publish(dir.n, "source-alias", "published");
  e = errno;
  require(rc == -1 && e == EINVAL, "source symlink accepted");
  bool syncRejected = false;
  try {
    syncFd(-1);
  } catch (const Failure &failure) {
    syncRejected = failure.number == EBADF;
  }
  require(syncRejected, "fsync failure was suppressed");
  check(fchmod(dir.n, 0500), "make test directory read-only");
  rc = publish(dir.n, "pending", "published");
  e = errno;
  check(fchmod(dir.n, 0700), "restore test directory mode");
  require(rc == -1 && e == EACCES && !exists(dir.n, "published"),
          "read-only directory did not reject publication");
  rc = unlinkat(dir.n, "missing", 0);
  e = errno;
  require(rc == -1 && e == ENOENT, "cleanup error not returned");
  // Explicit error injection tests propagation only, not real kernel support.
  RenameCall failures[] = {missingSyscall, invalidSyscall, unsupportedSyscall};
  int expected[] = {ENOSYS, EINVAL, EOPNOTSUPP};
  for (int i = 0; i < 3; ++i) {
    rc = publish(dir.n, "pending", "published", failures[i]);
    e = errno;
    require(rc == -1 && e == expected[i] && !exists(dir.n, "published") &&
                content(dir.n, "pending") == "error source",
            "unsupported syscall error swallowed");
  }
  // A visible publication is retained when directory sync fails, never rolled
  // back.
  Fd postSync = subdir(root, "sync-failure");
  stage(postSync.n, "pending", "published before sync failure");
  check(publish(postSync.n, "pending", "published"),
        "sync-failure publication");
  bool postPublishSyncRejected = false;
  try {
    syncFd(-1);
  } catch (const Failure &failure) {
    postPublishSyncRejected = failure.number == EBADF;
  }
  require(postPublishSyncRejected &&
              content(postSync.n, "published") ==
                  "published before sync failure" &&
              !exists(postSync.n, "pending"),
          "post-publication sync failure lost visible file");
  // A later recovery sync acknowledges the retained entry, not the failed call.
  syncFd(postSync.n);
  remove(dir.n, "source-alias");
  remove(dir.n, "pending");
  syncFd(dir.n);
  return "{\"traversalRejected\":true,\"sourceSymlinkRejected\":true,"
         "\"missingSourceErrno\":" +
         std::to_string(ENOENT) +
         ",\"invalidDescriptorErrno\":" + std::to_string(EBADF) +
         ",\"fsyncFailurePropagated\":true,\"readOnlyDirectoryErrno\":" +
         std::to_string(EACCES) +
         ",\"cleanupMissingErrno\":" + std::to_string(ENOENT) +
         ",\"injectedUnsupportedErrors\":[\"ENOSYS\",\"EINVAL\",\"EOPNOTSUPP\"]"
         ",\"postPublicationSyncFailureRetainsFile\":true,"
         "\"syncFailureDescriptorIsInjected\":true"
         ",\"unsupportedErrorsAreSimulated\":true,\"fallbackUsed\":false}";
}
std::string optionalRead(const char *path) {
  int raw = open(path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
  if (raw < 0) {
    const int e = errno;
    return "{\"available\":false,\"errno\":" + std::to_string(e) +
           ",\"code\":" + quote(code(e)) + "}";
  }
  Fd fd(raw);
  char data[512];
  ssize_t n = read(fd.n, data, sizeof(data));
  if (n < 0) {
    const int e = errno;
    return "{\"available\":false,\"errno\":" + std::to_string(e) + "}";
  }
  return "{\"available\":true,\"value\":" +
         quote(std::string(data, static_cast<size_t>(n))) + "}";
}
} // namespace

int main(int argc, char **argv) {
  // Watchdog bounds barrier failures; children receive SIGKILL if this parent
  // exits.
  alarm(75);
  bool passed = true;
  std::ostringstream results;
  bool first = true;
  try {
    require(argc == 2,
            "Expected one trusted existing app-private test directory");
    require(getuid() != 0, "Refusing root test identity");
    Fd base(open(argv[1], O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
    auto owner = info(base.n, ".");
    require(owner.st_uid == getuid(),
            "Test root is not owned by ordinary process UID");
    require((owner.st_mode & 0077) == 0, "Test root permissions must be 0700");
    struct statfs filesystem {};
    check(fstatfs(base.n, &filesystem), "fstatfs");
    struct utsname kernel {};
    check(uname(&kernel), "uname");
    auto run = [&](const std::string &name,
                   const std::function<std::string(int)> &test) {
      if (!first)
        results << ',';
      first = false;
      results << "{\"name\":" << quote(name);
      try {
        const auto evidence = test(base.n);
        results << ",\"status\":\"PASS\",\"evidence\":" << evidence;
      } catch (const Failure &e) {
        passed = false;
        results << ",\"status\":\"FAIL\",\"error\":" << quote(e.what())
                << ",\"errno\":" << e.number
                << ",\"code\":" << quote(code(e.number));
      }
      results << '}';
    };
    run("A-publication", success);
    run("B-existing-destination", collision);
    run("C-independent-processes", concurrency);
    run("D-interruption", interruptions);
    run("E-errors-and-boundaries", errors);
    std::cout
        << "{\"schemaVersion\":1,\"suite\":\"atomic-noreplace-native-v1\","
           "\"status\":"
        << quote(passed ? "PASS" : "FAIL") << ",\"uid\":" << getuid()
        << ",\"pid\":" << getpid() << ",\"parentPid\":" << getppid()
        << ",\"syscall\":\"renameat2\",\"flags\":\"RENAME_NOREPLACE\","
           "\"kernel\":"
        << quote(kernel.release)
        << ",\"architecture\":" << quote(kernel.machine)
        << ",\"filesystemType\":"
        << quote(std::to_string(static_cast<unsigned long>(filesystem.f_type)))
        << ",\"selinuxContext\":" << optionalRead("/proc/self/attr/current")
        << ",\"selinuxEnforce\":" << optionalRead("/sys/fs/selinux/enforce")
        << ",\"denialAuditRead\":\"not-requested; capture permitted AVC "
           "diagnostics with adb\",\"tests\":["
        << results.str()
        << "],\"powerLossTested\":false,\"harnessPersistenceModified\":false,"
           "\"gate2Passed\":false}"
        << std::endl;
    return passed ? 0 : 1;
  } catch (const Failure &e) {
    std::cout << "{\"schemaVersion\":1,\"status\":\"BLOCKED\",\"error\":"
              << quote(e.what()) << ",\"errno\":" << e.number
              << ",\"code\":" << quote(code(e.number))
              << ",\"gate2Passed\":false}" << std::endl;
    return 2;
  }
}
