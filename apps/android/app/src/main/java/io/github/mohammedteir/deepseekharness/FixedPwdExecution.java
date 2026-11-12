package io.github.mohammedteir.deepseekharness;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.concurrent.TimeUnit;

/** Qualification-only fixed pwd execution; no shell string or caller-selected executable. */
public final class FixedPwdExecution implements AutoCloseable {
    /** Actual observed command outputs; stderr is retained even on exit zero. */
    public static final class Result {
        public final String stdout, stderr;
        public final int exitCode;
        private Result(String stdout, String stderr, int exitCode) {
            this.stdout = stdout;
            this.stderr = stderr;
            this.exitCode = exitCode;
        }
    }

    private final CommandGrant.Request request;
    private final CommandGrant grant;
    private final OwnedProcess process = new OwnedProcess();

    /** Configure only from native-owned identity and canonical private workspace. */
    public static FixedPwdExecution android(String sessionId, String callId, File workspace,
                                            int uid, CommandGrant grant) throws IOException {
        if (uid <= 0 || new File("/system/bin/pwd").canWrite()) {
            throw new IOException("Ordinary UID and immutable system executable required");
        }
        return new FixedPwdExecution(sessionId, callId, workspace, uid, grant, "/system/bin/pwd");
    }

    // Host qualification can name its own pwd binary; never exposed on the Android factory or IPC.
    FixedPwdExecution(String sessionId, String callId, File workspace, int uid,
                      CommandGrant grant, String executable) throws IOException {
        if (!workspace.isDirectory()) throw new IOException("Workspace unavailable");
        this.request = new CommandGrant.Request(sessionId, callId, executable,
            Collections.emptyList(), workspace.getCanonicalPath(), uid);
        this.grant = java.util.Objects.requireNonNull(grant);
    }

    /** Consume exact consent before launch. Caller cancellation must close this owner. */
    public Result execute() throws IOException, InterruptedException {
        CommandGrant.Outcome outcome = grant.consume(request);
        if (outcome != CommandGrant.Outcome.CONSUMED) throw new IOException("Command authorization: " + outcome);
        File executable = new File(request.executable);
        if (!executable.isFile() || !executable.canExecute()) throw new IOException("Fixed pwd unavailable");
        // Android installation/system policy owns executable immutability; no writable extraction.
        ProcessBuilder builder = new ProcessBuilder(request.executable);
        builder.directory(new File(request.cwd));
        builder.environment().clear();
        builder.environment().put("PATH", "/system/bin");
        builder.environment().put("PWD", request.cwd);
        try {
            Process child = process.start(builder);
            child.getOutputStream().close();
            if (!child.waitFor(5, TimeUnit.SECONDS)) throw new IOException("Fixed pwd timed out");
            return new Result(readBounded(child.getInputStream()), readBounded(child.getErrorStream()), child.exitValue());
        } finally {
            process.close();
        }
    }

    private static String readBounded(InputStream stream) throws IOException {
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        byte[] chunk = new byte[512];
        int count;
        while ((count = stream.read(chunk)) != -1) {
            if (output.size() + count > 8192) throw new IOException("Fixed pwd output exceeded limit");
            output.write(chunk, 0, count);
        }
        return output.toString(StandardCharsets.UTF_8.name());
    }

    /** Revoke pending consent and terminate/reap the owned process on cancellation. */
    @Override public void close() throws IOException {
        grant.close();
        process.close();
    }
}
