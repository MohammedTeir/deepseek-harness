package io.github.mohammedteir.deepseekharness;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.PosixFilePermissions;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

/** Host JVM policy checks only: no Android UI, peer authentication or process proof. */
public final class TerminalAllocationGrantFixture {
    private static void require(boolean value) { if (!value) throw new AssertionError(); }
    private static TerminalAllocationGrant.Request candidate(TerminalAllocationGrant.Request base,
                                                            String field) {
        CommandGrant.Request c = base.command;
        return new TerminalAllocationGrant.Request(
            field.equals("owner") ? "other-owner" : base.ownerId,
            field.equals("terminal") ? "other-terminal" : base.terminalId,
            field.equals("backend") ? "other-backend" : base.backend,
            field.equals("columns") ? 81 : base.columns,
            field.equals("rows") ? 25 : base.rows,
            new CommandGrant.Request(field.equals("session") ? "other-session" : c.sessionId,
                field.equals("call") ? "other-call" : c.callId,
                field.equals("executable") ? "/system/bin/sh" : c.executable,
                field.equals("arguments") ? List.of("--wait") : c.arguments,
                field.equals("cwd") ? "/" : c.cwd, field.equals("uid") ? 0 : c.uid));
    }
    private static void expected(TerminalAllocationGrant grant, TerminalAllocationGrant.Request request,
                                 CommandGrant.Outcome outcome) throws IOException {
        require(grant.consume(request) == outcome);
    }
    private static TerminalAllocationGrant create(Path root, AtomicLong clock) throws IOException {
        return new TerminalAllocationGrant("session", "call", "agent", "terminal",
            root.resolve("workspace").toFile(), root.resolve("libharness_pty_fixture.so").toFile(),
            1000, clock::get, 100);
    }
    public static void main(String[] args) throws Exception {
        Path root = Path.of(args[1]);
        Files.createDirectory(root.resolve("workspace"));
        Path program = root.resolve("libharness_pty_fixture.so");
        Files.writeString(program, "policy fixture only; never executed\n");
        Files.setPosixFilePermissions(program, PosixFilePermissions.fromString("r-x------"));
        AtomicLong clock = new AtomicLong();
        try (TerminalAllocationGrant grant = create(root, clock)) {
            TerminalAllocationGrant.Request exact = grant.request();
            switch (args[0]) {
                case "approval":
                    expected(grant, exact, CommandGrant.Outcome.APPROVAL_REQUIRED);
                    require(grant.decide(true));
                    expected(grant, exact, CommandGrant.Outcome.CONSUMED);
                    expected(grant, exact, CommandGrant.Outcome.USED);
                    require(!grant.decide(true));
                    break;
                case "denial":
                    require(grant.decide(false)); require(!grant.decide(true));
                    expected(grant, exact, CommandGrant.Outcome.REJECTED);
                    break;
                case "bindings":
                    require(grant.decide(true));
                    for (String field : List.of("owner", "terminal", "backend", "columns", "rows", "session",
                                                "call", "executable", "arguments", "cwd", "uid")) {
                        expected(grant, candidate(exact, field), CommandGrant.Outcome.REQUEST_CHANGED);
                    }
                    expected(grant, null, CommandGrant.Outcome.REQUEST_CHANGED);
                    expected(grant, exact, CommandGrant.Outcome.CONSUMED);
                    break;
                case "revocation":
                    require(grant.decide(true)); grant.close();
                    expected(grant, exact, CommandGrant.Outcome.CLOSED);
                    require(!grant.decide(true));
                    break;
                case "expiry":
                    require(grant.decide(true)); clock.set(100);
                    expected(grant, exact, CommandGrant.Outcome.EXPIRED);
                    require(!grant.decide(true));
                    break;
                case "immutable":
                    try { exact.command.arguments.clear(); throw new AssertionError(); }
                    catch (UnsupportedOperationException expected) { /* native snapshot is immutable */ }
                    require(exact.command.arguments.equals(List.of("--tty-child")));
                    for (String invalid : new String[] { "", "bad\0id", "x".repeat(257) }) {
                        try {
                            new TerminalAllocationGrant.Request(invalid, "terminal", exact.backend,
                                80, 24, exact.command); throw new AssertionError();
                        } catch (IllegalArgumentException expected) { /* bounded native binding */ }
                    }
                    for (int invalid : new int[] { 0, -1, 1001 }) {
                        try {
                            new TerminalAllocationGrant.Request("owner", "terminal", exact.backend,
                                invalid, 24, exact.command); throw new AssertionError();
                        } catch (IllegalArgumentException expected) { /* bounded initial geometry */ }
                    }
                    List<String> mutable = new ArrayList<>(exact.command.arguments);
                    CommandGrant.Request copy = new CommandGrant.Request("session", "call", exact.command.executable,
                        mutable, exact.command.cwd, exact.command.uid);
                    mutable.clear(); require(copy.arguments.equals(exact.command.arguments));
                    break;
                case "concurrency": {
                    require(grant.decide(true));
                    CountDownLatch ready = new CountDownLatch(32), start = new CountDownLatch(1);
                    AtomicInteger winners = new AtomicInteger(), used = new AtomicInteger();
                    AtomicReference<Throwable> failure = new AtomicReference<>();
                    List<Thread> workers = new ArrayList<>();
                    try {
                        for (int i = 0; i < 32; i++) {
                            Thread thread = new Thread(() -> {
                                ready.countDown();
                                try {
                                    start.await();
                                    CommandGrant.Outcome result = grant.consume(exact);
                                    if (result == CommandGrant.Outcome.CONSUMED) winners.incrementAndGet();
                                    else if (result == CommandGrant.Outcome.USED) used.incrementAndGet();
                                    else throw new AssertionError(result);
                                } catch (Throwable error) { failure.compareAndSet(null, error); }
                            });
                            workers.add(thread); thread.start();
                        }
                        require(ready.await(5, java.util.concurrent.TimeUnit.SECONDS));
                        start.countDown();
                    } finally {
                        start.countDown();
                        for (Thread thread : workers) { thread.join(5000); require(!thread.isAlive()); }
                    }
                    require(failure.get() == null && winners.get() == 1 && used.get() == 31);
                    break;
                }
                case "workspace-replacement":
                case "workspace-symlink": {
                    require(grant.decide(true));
                    Path workspace = root.resolve("workspace"), old = root.resolve("old-workspace");
                    Files.move(workspace, old);
                    if (args[0].equals("workspace-symlink")) Files.createSymbolicLink(workspace, old);
                    else Files.createDirectory(workspace);
                    try { grant.consume(exact); throw new AssertionError(); }
                    catch (IOException expected) { /* no allocation may proceed */ }
                    Files.delete(workspace); Files.move(old, workspace);
                    expected(grant, exact, CommandGrant.Outcome.CLOSED);
                    break;
                }
                case "executable-replacement":
                case "executable-writable": {
                    require(grant.decide(true));
                    Path old = root.resolve("old-program");
                    if (args[0].equals("executable-replacement")) {
                        Files.move(program, old); Files.copy(old, program);
                    } else Files.setPosixFilePermissions(program, PosixFilePermissions.fromString("rwx------"));
                    try { grant.consume(exact); throw new AssertionError(); }
                    catch (IOException expected) { /* changed native file fails closed */ }
                    if (Files.exists(old)) { Files.delete(program); Files.move(old, program); }
                    Files.setPosixFilePermissions(program, PosixFilePermissions.fromString("r-x------"));
                    expected(grant, exact, CommandGrant.Outcome.CLOSED);
                    break;
                }
                case "constructor": {
                    for (int uid : new int[] { 0, -1 }) {
                        try {
                            new TerminalAllocationGrant("s", "c", "a", "t", root.resolve("workspace").toFile(),
                                program.toFile(), uid, clock::get, 100); throw new AssertionError();
                        } catch (IllegalArgumentException expected) { /* no root or negative identity */ }
                    }
                    File alias = root.resolve("alias").toFile(); Files.createSymbolicLink(alias.toPath(), root.resolve("workspace"));
                    try {
                        new TerminalAllocationGrant("s", "c", "a", "t", alias, program.toFile(),
                            1000, clock::get, 100); throw new AssertionError();
                    } catch (IOException expected) { /* explicit canonical native paths only */ }
                    break;
                }
                default: throw new IllegalArgumentException("Unknown mode");
            }
        }
        System.out.println(args[0] + " PASS");
    }
}
