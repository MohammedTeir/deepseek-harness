package io.github.mohammedteir.deepseekharness;

import java.io.File;
import java.io.IOException;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.SimpleFileVisitor;
import java.nio.file.attribute.BasicFileAttributes;

/** Contained image paths and cleanup that deletes symlinks without following them. */
public final class ImageFiles {
    private ImageFiles() {}

    public static File child(File root, String name) throws IOException {
        if (name.isEmpty() || name.startsWith("/") || name.contains("\\")) throw new IOException("Invalid image path");
        for (String part : name.split("/", -1)) {
            if (part.isEmpty() || part.equals(".") || part.equals("..")) throw new IOException("Image path traversal");
        }
        File result = new File(root, name);
        if (!result.getCanonicalPath().startsWith(root.getCanonicalPath() + File.separator)) throw new IOException("Image path escaped root");
        return result;
    }

    public static void remove(File root) throws IOException {
        Files.walkFileTree(root.toPath(), new SimpleFileVisitor<Path>() {
            @Override public FileVisitResult visitFile(Path file, BasicFileAttributes attributes) throws IOException {
                Files.delete(file);
                return FileVisitResult.CONTINUE;
            }
            @Override public FileVisitResult postVisitDirectory(Path directory, IOException error) throws IOException {
                if (error != null) throw error;
                Files.delete(directory);
                return FileVisitResult.CONTINUE;
            }
        });
    }
}
