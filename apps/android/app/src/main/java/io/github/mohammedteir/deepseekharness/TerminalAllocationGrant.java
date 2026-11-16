package io.github.mohammedteir.deepseekharness;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.util.List;
import java.util.Objects;
import java.util.function.LongSupplier;

/**
 * Qualification-only native allocation policy. No IPC endpoint or process launcher.
 * Native-owned configuration and registry-issued IDs must be authenticated by the
 * eventual broker before construction; this class cannot establish their origin.
 */
public final class TerminalAllocationGrant implements AutoCloseable {
    public static final String BACKEND = "android-fixed-pty-v1";
    public static final String ROLE = "--tty-child";
    public static final int COLUMNS = 80, ROWS = 24;

    /** Immutable complete allocation binding. This is data, never a human decision. */
    public static final class Request {
        public final String ownerId, terminalId, backend;
        public final int columns, rows;
        public final CommandGrant.Request command;

        public Request(String ownerId, String terminalId, String backend,
                       int columns, int rows, CommandGrant.Request command) {
            this.ownerId = identifier(ownerId);
            this.terminalId = identifier(terminalId);
            this.backend = identifier(backend);
            if (columns < 1 || rows < 1 || columns > 1000 || rows > 1000) {
                throw new IllegalArgumentException("Invalid terminal dimensions");
            }
            this.columns = columns;
            this.rows = rows;
            this.command = Objects.requireNonNull(command);
        }

        private boolean matchesTerminal(Request candidate) {
            return candidate != null && ownerId.equals(candidate.ownerId)
                && terminalId.equals(candidate.terminalId) && backend.equals(candidate.backend)
                && columns == candidate.columns && rows == candidate.rows;
        }
    }

    private final Request request;
    private final File workspace, executable;
    private final Object workspaceKey, executableKey;
    private final BasicFileAttributes executableAttributes;
    private final CommandGrant grant;

    /**
     * Bind one fixed direct-child allocation. Paths and UID come from the native
     * supervisor, not caller claims. Agent/terminal/call ownership is a broker duty.
     * A filesystem without observable file identity is explicitly unsupported.
     */
    public TerminalAllocationGrant(String sessionId, String callId, String ownerId,
                                   String terminalId, File workspace, File executable,
                                   int nativeUid, LongSupplier clock, long lifetimeNanos) throws IOException {
        if (nativeUid <= 0) throw new IllegalArgumentException("Ordinary native UID required");
        this.workspace = canonical(workspace);
        this.executable = canonical(executable);
        if (!this.workspace.isDirectory() || !this.executable.isFile()
            || this.executable.canWrite() || !this.executable.canExecute()
            || !this.executable.getName().equals("libharness_pty_fixture.so")) {
            throw new IOException("Native fixed fixture/workspace unavailable");
        }
        BasicFileAttributes directory = attributes(this.workspace);
        executableAttributes = attributes(this.executable);
        workspaceKey = directory.fileKey();
        executableKey = executableAttributes.fileKey();
        if (workspaceKey == null || executableKey == null) throw new IOException("Native file identity unavailable");
        request = new Request(ownerId, terminalId, BACKEND, COLUMNS, ROWS,
            new CommandGrant.Request(identifier(sessionId), identifier(callId), this.executable.getPath(),
                List.of(ROLE), this.workspace.getPath(), nativeUid));
        grant = new CommandGrant(request.command, clock, lifetimeNanos);
    }

    private static String identifier(String value) {
        if (value == null || value.isEmpty() || value.length() > 256 || value.indexOf('\0') >= 0) {
            throw new IllegalArgumentException("Invalid allocation identity");
        }
        return value;
    }

    private static File canonical(File file) throws IOException {
        Objects.requireNonNull(file);
        if (!file.isAbsolute() || !file.equals(file.getCanonicalFile())) {
            throw new IOException("Explicit canonical native path required");
        }
        return file;
    }

    private static BasicFileAttributes attributes(File file) throws IOException {
        return Files.readAttributes(file.toPath(), BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
    }

    /** Exact snapshot for the native UI; nested arguments are immutable. */
    public Request request() { return request; }

    private void verifyResources() throws IOException {
        try {
            canonical(workspace);
            canonical(executable);
            BasicFileAttributes directory = attributes(workspace), program = attributes(executable);
            if (!directory.isDirectory() || !program.isRegularFile()
                || !workspaceKey.equals(directory.fileKey()) || !executableKey.equals(program.fileKey())
                || program.size() != executableAttributes.size()
                || !program.lastModifiedTime().equals(executableAttributes.lastModifiedTime())
                || executable.canWrite() || !executable.canExecute()) {
                throw new IOException("Native allocation resources changed");
            }
        } catch (IOException failure) {
            grant.close();
            throw failure;
        } catch (SecurityException failure) {
            grant.close();
            throw new IOException("Native allocation resources inaccessible", failure);
        }
    }

    /** Private native human-decision handler only; not an agent or wire method. */
    public synchronized boolean decide(boolean allow) throws IOException {
        verifyResources();
        return grant.decide(allow);
    }

    /**
     * Consume immediately before allocation. Failure to allocate still spends the
     * grant. Additional terminal metadata is checked before command-grant state.
     * This check is not descriptor-based filesystem confinement or plugin isolation.
     */
    public synchronized CommandGrant.Outcome consume(Request candidate) throws IOException {
        verifyResources();
        if (!request.matchesTerminal(candidate)) return CommandGrant.Outcome.REQUEST_CHANGED;
        return grant.consume(candidate.command);
    }

    /** Revoke pending allocation; closing cannot terminate a child allocated elsewhere. */
    @Override public synchronized void close() { grant.close(); }
}
