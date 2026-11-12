package io.github.mohammedteir.deepseekharness;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.util.concurrent.TimeUnit;

/** Real host child-process lifecycle checks; not Android execution evidence. */
public final class OwnedProcessFixture {
    private static ProcessBuilder builder(String mode) {
        return new ProcessBuilder(System.getProperty("java.home") + "/bin/java", "-cp",
            System.getProperty("java.class.path"), OwnedProcessFixture.class.getName(), "child", mode);
    }
    public static void main(String[] args) throws Exception {
        if (args[0].equals("child")) {
            System.out.println("ready");
            System.out.flush();
            if (args[1].equals("exit")) System.exit(7);
            Thread.sleep(60000);
            return;
        }
        if (args[0].equals("preclosed")) {
            OwnedProcess owner = new OwnedProcess();
            owner.close();
            Process unexpected = null;
            try {
                unexpected = owner.start(builder("sleep"));
                throw new AssertionError("Closed owner launched a child");
            } catch (IOException expected) {
                System.out.println("launch rejected");
            } finally {
                if (unexpected != null) { unexpected.destroyForcibly(); unexpected.waitFor(5, TimeUnit.SECONDS); }
            }
            return;
        }
        try (OwnedProcess owner = new OwnedProcess()) {
            Process process = owner.start(builder(args[0].equals("normal") ? "exit" : "sleep"));
            if (!"ready".equals(new BufferedReader(new InputStreamReader(process.getInputStream())).readLine())) {
                throw new AssertionError("Child never became ready");
            }
            if (args[0].equals("normal")) {
                if (!process.waitFor(5, TimeUnit.SECONDS) || process.exitValue() != 7) {
                    throw new AssertionError("Expected actual child exit 7");
                }
            }
            boolean interrupt = args[0].equals("interrupted");
            if (interrupt) Thread.currentThread().interrupt();
            owner.close();
            if (process.isAlive()) throw new AssertionError("Child still alive after close");
            if (interrupt && !Thread.currentThread().isInterrupted()) throw new AssertionError("Interruption lost");
            Thread.interrupted();
            owner.close();
            System.out.println("child reaped");
        }
    }
}
