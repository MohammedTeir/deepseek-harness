#define _GNU_SOURCE
/* Fixed-directory prepared-file publication. Async ownership follows the atomic publication binding. */
#include <node_api.h>
#include <errno.h>
#include <limits.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <fcntl.h>
#include <unistd.h>
#include <string.h>

/* Linux UAPI flag; the API-30 Bionic renameat2 wrapper is never imported. */
enum { publish_noreplace = 1 };

typedef struct {
  napi_env env;
  napi_ref callback;
  napi_async_work work;
  napi_async_cleanup_hook_handle cleanup;
  char parent[PATH_MAX];
  char source[121];
  char target[121];
  const char *operation;
  int error;
  bool closing;
} publish_request;

static void check_status(napi_status status, const char *message) {
  if (status != napi_ok) {
    napi_fatal_error("atomic publication", NAPI_AUTO_LENGTH, message, NAPI_AUTO_LENGTH);
  }
}

static void release_request(publish_request *request) {
  if (request->callback != NULL) {
    (void)napi_delete_reference(request->env, request->callback);
  }
  if (request->work != NULL) {
    (void)napi_delete_async_work(request->env, request->work);
  }
  if (request->cleanup != NULL) {
    (void)napi_remove_async_cleanup_hook(request->cleanup);
  }
  free(request);
}

static napi_value throw_setup_error(napi_env env, napi_status status,
                                   const char *message) {
  if (status != napi_pending_exception) {
    status = napi_throw_error(env, "ERR_ATOMIC_PUBLISH_ASYNC_WORK", message);
    bool pending;
    /* Error construction can fail with both generic_failure and a JS exception. */
    check_status(napi_is_exception_pending(env, &pending), "Cannot inspect atomic publication setup exception");
    if (!pending && status != napi_pending_exception) check_status(status, message);
  }
  return NULL;
}

static bool valid_name(const char *name) {
  const size_t length = strlen(name);
  if (length == 0 || length > 120 || strcmp(name, ".") == 0 || strcmp(name, "..") == 0) return false;
  for (const char *p = name; *p; ++p) {
    if (!((*p >= 'a' && *p <= 'z') || (*p >= '0' && *p <= '9') || *p == '-' || *p == '.')) return false;
  }
  return true;
}

static bool valid_parent(const char *path) {
  if (path[0] != '/') return false;
  if (strcmp(path, "/") == 0) return true;
  const char *component = path + 1;
  for (const char *p = component;; ++p) {
    if (*p != '/' && *p != '\0') continue;
    const size_t length = (size_t)(p - component);
    if (length == 0 || (length == 1 && component[0] == '.') ||
        (length == 2 && component[0] == '.' && component[1] == '.')) return false;
    if (*p == '\0') return true;
    component = p + 1;
  }
}

static void execute_publish(napi_env env, void *data) {
  (void)env;
  publish_request *request = data;
  request->operation = "open";
  const int fd = open(request->parent, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
  if (fd < 0) { request->error = errno; return; }
  struct stat owner;
  request->operation = "fstat";
  if (fstat(fd, &owner) < 0) request->error = errno;
  else if (owner.st_uid != getuid() || (owner.st_mode & 0077) != 0) {
    request->operation = "validate-private-parent";
    request->error = EACCES;
  }
  if (request->error == 0) {
    struct stat source;
    request->operation = "fstatat";
    if (fstatat(fd, request->source, &source, AT_SYMLINK_NOFOLLOW) < 0) request->error = errno;
    else if (!S_ISREG(source.st_mode)) {
      request->operation = "validate-staging";
      request->error = EINVAL;
    }
  }
  if (request->error == 0) {
    request->operation = "renameat2";
#ifdef SYS_renameat2
    if (syscall(SYS_renameat2, fd, request->source, fd, request->target, publish_noreplace) < 0) request->error = errno;
#else
    request->error = ENOSYS;
#endif
  }
  // Do not remove a published destination if a later operation reports failure.
  if (close(fd) < 0 && request->error == 0) { request->operation = "close"; request->error = errno; }
}

static void complete_publish(napi_env env, napi_status status, void *data) {
  publish_request *request = data;
  if (env != NULL && !request->closing) {
    napi_value callback;
    napi_value receiver;
    napi_value result[2];
    check_status(status, "atomic publication async work did not complete");
    check_status(napi_get_reference_value(env, request->callback, &callback),
                 "Cannot retrieve atomic publication callback");
    check_status(napi_get_undefined(env, &receiver), "Cannot create atomic publication receiver");
    check_status(napi_create_int32(env, request->error, &result[0]),
                 "Cannot create atomic publication result");
    check_status(napi_create_string_utf8(env, request->operation, NAPI_AUTO_LENGTH, &result[1]),
                 "Cannot create publication operation");
    status = napi_call_function(env, receiver, callback, 2, result, NULL);
  } else {
    status = napi_ok;
  }
  release_request(request);
  /* Node's async-work dispatcher reports callback exceptions and handles termination. */
  if (status != napi_pending_exception) {
    check_status(status, "Cannot invoke atomic publication callback");
  }
}

static void cleanup_publish(napi_async_cleanup_hook_handle handle, void *data) {
  (void)handle;
  publish_request *request = data;
  request->closing = true;
  /*
   * Running work cannot be cancelled. The hook keeps the environment alive
   * until completion releases both the work and this hook; it never frees
   * memory that the execution thread can still access.
   */
  (void)napi_cancel_async_work(request->env, request->work);
}

static bool read_string(napi_env env, napi_value value, char *output, size_t capacity) {
  size_t length = 0;
  if (napi_get_value_string_utf8(env, value, NULL, 0, &length) != napi_ok || length == 0 || length >= capacity) return false;
  if (napi_get_value_string_utf8(env, value, output, capacity, &length) != napi_ok) return false;
  return strlen(output) == length;
}

static napi_value publish_file(napi_env env, napi_callback_info info) {
  size_t argc = 4;
  napi_value argv[4];
  napi_status status = napi_get_cb_info(env, info, &argc, argv, NULL, NULL);
  if (status != napi_ok) return throw_setup_error(env, status, "Cannot read publication arguments");
  napi_valuetype callback_type;
  if (argc != 4 || napi_typeof(env, argv[3], &callback_type) != napi_ok || callback_type != napi_function) {
    (void)napi_throw_type_error(env, NULL, "Expected parent, staging basename, destination basename and callback");
    return NULL;
  }
  publish_request *request = calloc(1, sizeof(*request));
  if (request == NULL) { (void)napi_throw_error(env, "ENOMEM", "Cannot allocate publication work"); return NULL; }
  request->env = env;
  request->operation = "renameat2";
  if (!read_string(env, argv[0], request->parent, sizeof(request->parent)) ||
      !read_string(env, argv[1], request->source, sizeof(request->source)) ||
      !read_string(env, argv[2], request->target, sizeof(request->target)) ||
      !valid_parent(request->parent) || !valid_name(request->source) || !valid_name(request->target) ||
      strcmp(request->source, request->target) == 0) {
    free(request);
    (void)napi_throw_error(env, "EINVAL", "Publication requires a normalized absolute parent and distinct safe basenames");
    return NULL;
  }
  status = napi_create_reference(env, argv[3], 1, &request->callback);
  if (status != napi_ok) {
    release_request(request);
    return throw_setup_error(env, status, "Cannot retain atomic publication callback");
  }
  napi_value name;
  status = napi_create_string_utf8(env, "atomic publication", NAPI_AUTO_LENGTH, &name);
  if (status == napi_ok) {
    status = napi_create_async_work(env, NULL, name, execute_publish, complete_publish,
                                   request, &request->work);
  }
  if (status != napi_ok) {
    release_request(request);
    return throw_setup_error(env, status, "Cannot create atomic publication async work");
  }
  status = napi_add_async_cleanup_hook(env, cleanup_publish, request, &request->cleanup);
  if (status != napi_ok) {
    release_request(request);
    return throw_setup_error(env, status, "Cannot register atomic publication environment cleanup");
  }
  status = napi_queue_async_work(env, request->work);
  if (status != napi_ok) {
    /* Queue failure schedules no completion callback. */
    release_request(request);
    return throw_setup_error(env, status, "Cannot queue atomic publication async work");
  }
  return NULL;
}

NAPI_MODULE_INIT() {
  napi_value function;
  if (napi_create_function(env, "publish", NAPI_AUTO_LENGTH, publish_file,
                           NULL, &function) != napi_ok ||
      napi_set_named_property(env, exports, "publish", function) != napi_ok) {
    return NULL;
  }
  return exports;
}
