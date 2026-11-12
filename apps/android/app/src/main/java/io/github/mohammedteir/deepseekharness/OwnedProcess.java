package io.github.mohammedteir.deepseekharness;

import java.io.Closeable;
import java.io.IOException;
import java.io.InterruptedIOException;
import java.util.concurrent.TimeUnit;

/** One child owner. Closing waits for exit; concurrent closes await the same cleanup. */
public final class OwnedProcess implements AutoCloseable {
    private final long termSeconds;

    public OwnedProcess() { this(2); }

    /** Allow the original SDK time to reap its own profile children on TERM. */
    public OwnedProcess(long termSeconds) {
        if (termSeconds < 1 || termSeconds > 20) throw new IllegalArgumentException("Invalid TERM grace");
        this.termSeconds = termSeconds;
    }

    private Process child;
    private boolean closed;

    /** Start once, unless cancellation has already closed this owner. */
    public synchronized Process start(ProcessBuilder builder) throws IOException {
        if (closed || child != null) throw new IOException("Process owner is closed or already used");
        if (Thread.currentThread().isInterrupted()) throw new InterruptedIOException("Launch interrupted");
        child = builder.start();
        return child;
    }

    private static boolean await(Process process, long seconds, boolean[] interrupted) {
        long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(seconds);
        while (true) {
            long remaining = deadline - System.nanoTime();
            if (remaining <= 0) return !process.isAlive();
            try { return process.waitFor(remaining, TimeUnit.NANOSECONDS); }
            catch (InterruptedException error) { interrupted[0] = true; }
        }
    }

    /** TERM, bounded wait, then KILL and bounded reap; restore caller interruption. */
    @Override public synchronized void close() throws IOException {
        if (closed) return;
        closed = true;
        if (child == null) return;
        boolean[] interrupted = {Thread.interrupted()};
        IOException failure = null;
        try {
            if (child.isAlive()) {
                child.destroy();
                if (!await(child, termSeconds, interrupted)) {
                    child.destroyForcibly();
                    if (!await(child, 3, interrupted)) failure = new IOException("Child did not exit after KILL");
                }
            }
        } finally {
            for (Closeable stream : new Closeable[]{child.getOutputStream(), child.getInputStream(), child.getErrorStream()}) {
                try { stream.close(); }
                catch (IOException error) {
                    if (failure == null) failure = error;
                    else failure.addSuppressed(error);
                }
            }
            if (interrupted[0]) Thread.currentThread().interrupt();
        }
        if (failure != null) throw failure;
    }
}
