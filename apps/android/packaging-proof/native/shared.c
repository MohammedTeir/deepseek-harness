#include <jni.h>
#include <stdio.h>
#include <unistd.h>

/* Actual OS calls: this fixture does not implement any Node or Harness API. */
JNIEXPORT jstring JNICALL
Java_io_github_mohammedteir_deepseekharness_packaging_PackagingNative_sharedInfo(JNIEnv *env, jobject instance) {
    (void)instance;
    char output[160];
    snprintf(output, sizeof(output), "{\"uid\":%ld,\"pid\":%ld,\"pageSize\":%ld}",
             (long)getuid(), (long)getpid(), sysconf(_SC_PAGESIZE));
    return (*env)->NewStringUTF(env, output);
}
