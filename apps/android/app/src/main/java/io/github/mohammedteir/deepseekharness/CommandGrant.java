package io.github.mohammedteir.deepseekharness;

import java.util.List;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Objects;
import java.util.function.LongSupplier;

/** Per-request approval state owned by the native host; not an IPC authorization API. */
public final class CommandGrant implements AutoCloseable {
    /** Immutable identity of the single operation shown by the native approval surface. */
    public static final class Request {
        public final String sessionId, callId, executable, cwd;
        public final int uid;
        public final List<String> arguments;

        /** Construct from trusted native configuration, never directly from plugin metadata. */
        public Request(String sessionId, String callId, String executable, List<String> arguments,
                       String cwd, int uid) {
            this.sessionId = required(sessionId);
            this.callId = required(callId);
            this.executable = required(executable);
            this.cwd = required(cwd);
            if (!executable.startsWith("/") || !cwd.startsWith("/") || uid < 0) {
                throw new IllegalArgumentException("Absolute paths and ordinary UID required");
            }
            this.uid = uid;
            ArrayList<String> copied = new ArrayList<>(Objects.requireNonNull(arguments));
            for (String argument : copied) Objects.requireNonNull(argument);
            this.arguments = Collections.unmodifiableList(copied);
        }

        private static String required(String value) {
            if (value == null || value.isEmpty() || value.indexOf('\0') >= 0) {
                throw new IllegalArgumentException("Missing or invalid request identity");
            }
            return value;
        }

        private boolean matches(Request other) {
            return other != null && uid == other.uid && sessionId.equals(other.sessionId)
                && callId.equals(other.callId) && executable.equals(other.executable)
                && cwd.equals(other.cwd) && arguments.equals(other.arguments);
        }
    }

    /** Stable denial categories for native broker diagnostics. */
    public enum Outcome { CONSUMED, APPROVAL_REQUIRED, REJECTED, EXPIRED, USED, CLOSED, REQUEST_CHANGED }
    private enum State { PENDING, APPROVED, REJECTED, USED, CLOSED }
    private final Request request;
    private final LongSupplier clock;
    private final long createdAt, lifetimeNanos;
    private State state = State.PENDING;

    /** Use a monotonic clock and a bounded lifetime; instance lifetime is one operation. */
    public CommandGrant(Request request, LongSupplier clock, long lifetimeNanos) {
        if (lifetimeNanos <= 0 || lifetimeNanos > 120_000_000_000L) {
            throw new IllegalArgumentException("Grant lifetime must be within two minutes");
        }
        this.request = Objects.requireNonNull(request);
        this.clock = Objects.requireNonNull(clock);
        this.createdAt = clock.getAsLong();
        this.lifetimeNanos = lifetimeNanos;
    }

    private boolean expired() { return clock.getAsLong() - createdAt >= lifetimeNanos; }

    /** Called only by a native human-decision handler, never exposed on agent IPC. */
    public synchronized boolean decide(boolean allow) {
        if (state != State.PENDING || expired()) return false;
        state = allow ? State.APPROVED : State.REJECTED;
        return true;
    }

    /** Consume before spawning; a failed spawn also consumes the grant and needs new consent. */
    public synchronized Outcome consume(Request candidate) {
        if (state == State.CLOSED) return Outcome.CLOSED;
        if (state == State.USED) return Outcome.USED;
        if (expired()) return Outcome.EXPIRED;
        if (!request.matches(candidate)) return Outcome.REQUEST_CHANGED;
        if (state == State.REJECTED) return Outcome.REJECTED;
        if (state != State.APPROVED) return Outcome.APPROVAL_REQUIRED;
        state = State.USED;
        return Outcome.CONSUMED;
    }

    /** Revoke on owner shutdown; this does not terminate an already owned subprocess. */
    @Override public synchronized void close() { state = State.CLOSED; }
}
