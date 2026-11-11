#include <jni.h>
#include <dlfcn.h>
#include <string>
#include <vector>

// Resolve only from the application's packaged library search path.
extern "C" JNIEXPORT jstring JNICALL
Java_io_github_mohammedteir_deepseekharness_RuntimeService_probeNode(JNIEnv* env, jobject) {
    void* library = dlopen("libnode.so", RTLD_NOW | RTLD_GLOBAL);
    if (!library) return env->NewStringUTF("BLOCKED: Android libnode.so is not packaged or could not link. Harness has not started.");
    void* entry = dlsym(library, "_ZN4node5StartEiPPc");
    const char* result = entry
        ? "Node entry symbol found. Runtime API and Harness execution remain NOT VERIFIED."
        : "BLOCKED: libnode.so does not export the required Node entry symbol.";
    dlclose(library);
    return env->NewStringUTF(result);
}

// Called once on a worker thread in the dedicated Android runtime process.
extern "C" JNIEXPORT jint JNICALL
Java_io_github_mohammedteir_deepseekharness_RuntimeService_runNode(JNIEnv* env, jobject, jstring script, jstring output) {
    void* library = dlopen("libnode.so", RTLD_NOW | RTLD_GLOBAL);
    if (!library) return -1;
    auto start = reinterpret_cast<int (*)(int, char**)>(dlsym(library, "_ZN4node5StartEiPPc"));
    if (!start) return -2;
    const char* script_chars = env->GetStringUTFChars(script, nullptr);
    if (!script_chars) return -3;
    std::string script_path(script_chars);
    env->ReleaseStringUTFChars(script, script_chars);
    const char* output_chars = env->GetStringUTFChars(output, nullptr);
    if (!output_chars) return -3;
    std::string output_path(output_chars);
    env->ReleaseStringUTFChars(output, output_chars);
    // Node/libuv may rewrite argv storage; use one contiguous mutable allocation.
    std::string arguments = std::string("node") + '\0' + script_path + '\0' + output_path + '\0';
    std::vector<char> storage(arguments.begin(), arguments.end());
    char* argv[] = {storage.data(), storage.data() + 5, storage.data() + 6 + script_path.size(), nullptr};
    // Keep libnode loaded until process teardown; V8 retains process-global state.
    return start(3, argv);
}
