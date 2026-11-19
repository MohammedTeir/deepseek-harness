package io.github.mohammedteir.deepseekharness

import java.io.File
import java.nio.file.Files
import org.junit.Assert.assertEquals
import org.junit.Test

class AndroidDefaultWorkspacePathTest {
    @Test
    fun usesTheAndroidPrivateDefaultWorkspacePath() {
        val root = Files.createTempDirectory("android-default-workspace-test").toFile()
        try {
            val documents = File(root, "harness-documents")
            val expected = File(documents, "deepseek-harness/default").canonicalFile

            assertEquals(expected.path, androidDefaultWorkspaceDirectory(documents).path)
        } finally {
            root.deleteRecursively()
        }
    }
}
