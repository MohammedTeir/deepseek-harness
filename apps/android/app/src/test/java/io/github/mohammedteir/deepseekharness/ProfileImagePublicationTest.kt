package io.github.mohammedteir.deepseekharness

import java.io.File
import java.nio.file.Files
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ProfileImagePublicationTest {
    @Test
    fun publishesExtractedTreeAtStableRootInsteadOfNestingIt() {
        val files = Files.createTempDirectory("profile-image-publish-test").toFile()
        try {
            val staging = File(files, "profile-image-staging-test")
            assertTrue(staging.mkdir())
            val root = File(staging, "tree")
            val runtimeLib = File(root, "runtime/lib")
            assertTrue(runtimeLib.mkdirs())
            File(runtimeLib, "bin.js").writeText("cli entry")
            File(root, ".profile-image-archive-sha256").writeText("a".repeat(64) + "\n")

            val current = File(files, "profile-image-current")
            val published = ProfileImage.publishTree(root, current)

            assertEquals(current.canonicalPath, published.canonicalPath)
            assertTrue(File(current, "runtime/lib/bin.js").isFile)
            assertTrue(File(current, ".profile-image-archive-sha256").isFile)
            assertFalse(File(current, "tree").exists())
            assertFalse(staging.exists())
        } finally {
            files.deleteRecursively()
        }
    }
}
