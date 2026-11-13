package io.github.mohammedteir.deepseekharness;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/** Actual host filesystem rejection and symlink cleanup; not Android OS qualification. */
public final class ImageFilesFixture {
    public static void main(String[] args) throws Exception {
        Path base = Files.createTempDirectory("harness-image-files-");
        try {
            Path root=Files.createDirectory(base.resolve("root"));
            Path outside=Files.createDirectory(base.resolve("outside"));
            Files.writeString(outside.resolve("keep"),"keep");
            Files.createSymbolicLink(root.resolve("cycle"),root);
            Files.createSymbolicLink(root.resolve("external"),outside);
            for (String name : new String[]{"../outside/keep", "/outside", "part/../../outside", "part\\outside", "external/keep"}) {
                try {
                    ImageFiles.child(root.toFile(),name);
                    throw new AssertionError("Unsafe path admitted: "+name);
                } catch (IOException expected) { /* Required rejection. */ }
            }
            if (!ImageFiles.child(root.toFile(),"safe/file.js").toPath().startsWith(root)) throw new AssertionError();
            ImageFiles.remove(root.toFile());
            if (Files.exists(root) || !Files.readString(outside.resolve("keep")).equals("keep")) throw new AssertionError("Cleanup followed an alias");
            System.out.println("Contained paths rejected; cycles removed; outside file retained");
        } finally { ImageFiles.remove(base.toFile()); }
    }
}
