package io.github.mohammedteir.deepseekharness;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

/** Executes the real grant implementation on a host JVM; no Android execution claim. */
public final class CommandGrantFixture {
    private static final CommandGrant.Request REQUEST = request("session", "call", "/system/bin/pwd", List.of(), "/private/workspace", 10751);
    private static CommandGrant.Request request(String session, String call, String executable,
                                                 List<String> args, String cwd, int uid) {
        return new CommandGrant.Request(session, call, executable, args, cwd, uid);
    }
    private static void require(boolean value) { if (!value) throw new AssertionError(); }
    private static void result(CommandGrant grant, CommandGrant.Request request, CommandGrant.Outcome expected) {
        require(grant.consume(request) == expected);
    }
    public static void main(String[] args) throws Exception {
        AtomicLong clock = new AtomicLong(0);
        switch (args[0]) {
            case "approval": {
                try (CommandGrant grant = new CommandGrant(REQUEST, clock::get, 100)) {
                    result(grant, REQUEST, CommandGrant.Outcome.APPROVAL_REQUIRED);
                    require(grant.decide(true));
                    result(grant, REQUEST, CommandGrant.Outcome.CONSUMED);
                    result(grant, REQUEST, CommandGrant.Outcome.USED);
                    require(!grant.decide(true));
                }
                break;
            }
            case "mutation": {
                try (CommandGrant grant = new CommandGrant(REQUEST, clock::get, 100)) {
                    require(grant.decide(true));
                    List<CommandGrant.Request> changed = List.of(
                        request("other", "call", "/system/bin/pwd", List.of(), "/private/workspace", 10751),
                        request("session", "other", "/system/bin/pwd", List.of(), "/private/workspace", 10751),
                        request("session", "call", "/system/bin/sh", List.of(), "/private/workspace", 10751),
                        request("session", "call", "/system/bin/pwd", List.of("-P"), "/private/workspace", 10751),
                        request("session", "call", "/system/bin/pwd", List.of(), "/other", 10751),
                        request("session", "call", "/system/bin/pwd", List.of(), "/private/workspace", 0));
                    for (CommandGrant.Request candidate : changed) result(grant, candidate, CommandGrant.Outcome.REQUEST_CHANGED);
                    result(grant, null, CommandGrant.Outcome.REQUEST_CHANGED);
                    result(grant, REQUEST, CommandGrant.Outcome.CONSUMED);
                }
                break;
            }
            case "expiry": {
                clock.set(Long.MAX_VALUE - 50);
                try (CommandGrant grant = new CommandGrant(REQUEST, clock::get, 100)) {
                    require(grant.decide(true));
                    clock.addAndGet(100); // monotonic nanoTime wraparound
                    result(grant, REQUEST, CommandGrant.Outcome.EXPIRED);
                }
                try (CommandGrant grant = new CommandGrant(REQUEST, clock::get, 100)) {
                    clock.addAndGet(100);
                    require(!grant.decide(true));
                    result(grant, REQUEST, CommandGrant.Outcome.EXPIRED);
                }
                break;
            }
            case "revocation": {
                CommandGrant grant = new CommandGrant(REQUEST, clock::get, 100);
                require(grant.decide(false));
                require(!grant.decide(true));
                result(grant, REQUEST, CommandGrant.Outcome.REJECTED);
                grant.close();
                result(grant, REQUEST, CommandGrant.Outcome.CLOSED);
                CommandGrant approved = new CommandGrant(REQUEST, clock::get, 100);
                require(approved.decide(true));
                approved.close();
                result(approved, REQUEST, CommandGrant.Outcome.CLOSED);
                break;
            }
            case "concurrency": {
                try (CommandGrant grant = new CommandGrant(REQUEST, clock::get, 100)) {
                    require(grant.decide(true));
                    AtomicInteger winners = new AtomicInteger();
                    AtomicInteger replays = new AtomicInteger();
                    CountDownLatch start = new CountDownLatch(1);
                    List<Thread> threads = new ArrayList<>();
                    for (int i = 0; i < 32; i++) {
                        Thread thread = new Thread(() -> {
                            try { start.await(); } catch (InterruptedException error) { throw new AssertionError(error); }
                            CommandGrant.Outcome outcome = grant.consume(REQUEST);
                            if (outcome == CommandGrant.Outcome.CONSUMED) winners.incrementAndGet();
                            if (outcome == CommandGrant.Outcome.USED) replays.incrementAndGet();
                        });
                        threads.add(thread);
                        thread.start();
                    }
                    start.countDown();
                    for (Thread thread : threads) thread.join();
                    require(winners.get() == 1 && replays.get() == 31);
                }
                break;
            }
            case "immutable": {
                List<String> mutable = new ArrayList<>(List.of("a"));
                CommandGrant.Request snapshot = request("session", "call", "/system/bin/pwd", mutable, "/private/workspace", 10751);
                mutable.clear();
                require(snapshot.arguments.equals(List.of("a")));
                try { snapshot.arguments.clear(); throw new AssertionError(); }
                catch (UnsupportedOperationException expected) { /* immutable */ }
                break;
            }
            case "process": {
                java.io.File workspace = new java.io.File(args[1]).getCanonicalFile();
                CommandGrant.Request host = request("session", "call", "/usr/bin/pwd", List.of(), workspace.getPath(), 1000);
                try (CommandGrant grant = new CommandGrant(host, System::nanoTime, 10_000_000_000L);
                     FixedPwdExecution execution = new FixedPwdExecution("session", "call", workspace, 1000, grant, "/usr/bin/pwd")) {
                    try { execution.execute(); throw new AssertionError(); }
                    catch (java.io.IOException expected) { require(expected.getMessage().contains("APPROVAL_REQUIRED")); }
                    require(grant.decide(true));
                    FixedPwdExecution.Result result = execution.execute();
                    require(result.exitCode == 0);
                    require(result.stdout.equals(workspace.getPath() + "\n"));
                    require(result.stderr.isEmpty());
                    try { execution.execute(); throw new AssertionError(); }
                    catch (java.io.IOException expected) { require(expected.getMessage().contains("USED")); }
                }
                break;
            }
            case "failed-launch": {
                java.io.File workspace = new java.io.File(args[1]).getCanonicalFile();
                String missing = workspace.getPath() + "/missing-pwd";
                CommandGrant.Request host = request("session", "call", missing, List.of(), workspace.getPath(), 1000);
                try (CommandGrant grant = new CommandGrant(host, System::nanoTime, 10_000_000_000L);
                     FixedPwdExecution execution = new FixedPwdExecution("session", "call", workspace, 1000, grant, missing)) {
                    require(grant.decide(true));
                    try { execution.execute(); throw new AssertionError(); }
                    catch (java.io.IOException expected) { require(expected.getMessage().contains("unavailable")); }
                    result(grant, host, CommandGrant.Outcome.USED);
                }
                break;
            }
            case "stderr":
            case "timeout":
            case "cancel": {
                java.nio.file.Path root = java.nio.file.Path.of(args[1]);
                java.nio.file.Path script = root.resolve("host-" + args[0]);
                String body = args[0].equals("stderr") ? "#!/bin/sh\nprintf 'out\\n'\nprintf 'err\\n' >&2\nexit 7\n" : "#!/bin/sh\nwhile :; do :; done\n";
                java.nio.file.Files.writeString(script, body);
                require(script.toFile().setExecutable(true, true));
                CommandGrant.Request host = request("session", "call", script.toString(), List.of(), root.toString(), 1000);
                try (CommandGrant grant = new CommandGrant(host, System::nanoTime, 30_000_000_000L);
                     FixedPwdExecution execution = new FixedPwdExecution("session", "call", root.toFile(), 1000, grant, script.toString())) {
                    require(grant.decide(true));
                    if (args[0].equals("stderr")) {
                        FixedPwdExecution.Result value = execution.execute();
                        require(value.exitCode == 7 && value.stdout.equals("out\n") && value.stderr.equals("err\n"));
                    } else if (args[0].equals("timeout")) {
                        try { execution.execute(); throw new AssertionError(); }
                        catch (java.net.SocketTimeoutException expected) { /* real five-second deadline */ }
                    } else {
                        java.util.concurrent.atomic.AtomicReference<Throwable> failure = new java.util.concurrent.atomic.AtomicReference<>();
                        Thread thread = new Thread(() -> { try { execution.execute(); } catch (Throwable error) { failure.set(error); } });
                        thread.start();
                        try {
                            long deadline = System.nanoTime() + 5_000_000_000L;
                            while (execution.processLaunches() == 0 && System.nanoTime() < deadline) Thread.sleep(5);
                            require(execution.processLaunches() == 1);
                            execution.close();
                            thread.join(10000);
                            require(!thread.isAlive());
                            require(failure.get() instanceof java.io.InterruptedIOException);
                        } finally { execution.close(); thread.join(10000); }
                    }
                    require(execution.processLaunches() == 1);
                }
                break;
            }
            case "workspace": {
                java.nio.file.Path root = java.nio.file.Path.of(args[1]);
                java.nio.file.Path workspace = java.nio.file.Files.createDirectory(root.resolve("guarded"));
                String executable = "/usr/bin/pwd";
                CommandGrant.Request host = request("session", "call", executable, List.of(), workspace.toString(), 1000);
                try (CommandGrant grant = new CommandGrant(host, System::nanoTime, 10_000_000_000L);
                     FixedPwdExecution execution = new FixedPwdExecution("session", "call", workspace.toFile(), 1000, grant, executable)) {
                    require(grant.decide(true));
                    java.nio.file.Files.move(workspace, root.resolve("moved"));
                    java.nio.file.Files.createSymbolicLink(workspace, root.resolve("moved"));
                    try { execution.execute(); throw new AssertionError(); }
                    catch (java.io.IOException expected) { require(expected.getMessage().contains("workspace changed")); }
                    require(execution.processLaunches() == 0);
                }
                break;
            }
            default: throw new IllegalArgumentException("Unknown fixture");
        }
        System.out.println(args[0] + " PASS");
    }
}
