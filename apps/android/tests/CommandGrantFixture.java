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
            default: throw new IllegalArgumentException("Unknown fixture");
        }
        System.out.println(args[0] + " PASS");
    }
}
