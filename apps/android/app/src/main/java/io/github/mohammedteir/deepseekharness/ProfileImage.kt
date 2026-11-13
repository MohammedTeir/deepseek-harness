package io.github.mohammedteir.deepseekharness

import android.content.res.AssetManager
import java.io.File
import java.nio.file.Files
import java.security.MessageDigest
import java.util.UUID
import java.util.zip.ZipInputStream
import org.json.JSONObject

/** APK-owned interpreted data only; native libraries remain in the installer directory. */
object ProfileImage {
    private fun hash(file: File): String = file.inputStream().use { input ->
        val digest = MessageDigest.getInstance("SHA-256")
        val buffer = ByteArray(16384)
        while (true) {
            val count = input.read(buffer)
            if (count < 0) break
            digest.update(buffer, 0, count)
        }
        digest.digest().joinToString("") { "%02x".format(it.toInt() and 255) }
    }
    private fun child(root: File, name: String): File = ImageFiles.child(root, name)
    fun remove(root: File) = ImageFiles.remove(root)
    fun install(assets: AssetManager, files: File): File {
        val staging = File(files, "profile-image-${UUID.randomUUID()}").canonicalFile
        check(staging.mkdir()) { "Cannot create interpreted image directory" }
        try {
            val archive = File(staging, "payload.zip")
            assets.open("runtime/profile-image.zip").use { source -> archive.outputStream().use(source::copyTo) }
            val expected = assets.open("runtime/profile-image.sha256").bufferedReader().use { it.readText().trim() }
            check(hash(archive) == expected) { "APK image hash mismatch" }
            val root = File(staging, "tree").apply { check(mkdir()) }
            val names = mutableSetOf<String>()
            var total = 0L
            ZipInputStream(archive.inputStream()).use { zip ->
                while (true) {
                    check(!Thread.currentThread().isInterrupted) { "Image installation cancelled" }
                    val entry = zip.nextEntry ?: break
                    check(!entry.isDirectory && names.add(entry.name) && names.size <= 5000) { "Unexpected image entry" }
                    val destination = child(root, entry.name)
                    check(destination.parentFile!!.mkdirs() || destination.parentFile!!.isDirectory)
                    destination.outputStream().use { output ->
                        val buffer = ByteArray(16384)
                        while (true) {
                            val count = zip.read(buffer)
                            if (count < 0) break
                            total += count
                            check(total <= 64L * 1024 * 1024) { "Interpreted image exceeds limit" }
                            output.write(buffer, 0, count)
                        }
                    }
                    zip.closeEntry()
                }
            }
            val manifest = JSONObject(File(root, "image-manifest.json").readText())
            check(manifest.getInt("schemaVersion") == 1)
            val entries = manifest.getJSONObject("files")
            val expectedNames = entries.keys().asSequence().toSet() + "image-manifest.json"
            check(names == expectedNames) { "Image entries differ from manifest" }
            for (name in entries.keys()) {
                val file = child(root, name)
                check(hash(file) == entries.getString(name)) { "Interpreted file hash mismatch: $name" }
                file.inputStream().use { input ->
                    val prefix = ByteArray(4)
                    val count = input.read(prefix)
                    check(count < 4 || !prefix.contentEquals(byteArrayOf(127, 69, 76, 70))) { "Native binary in interpreted image" }
                }
            }
            val directories = manifest.getJSONArray("directories")
            for (index in 0 until directories.length()) {
                val directory = child(root, directories.getString(index))
                check(directory.mkdirs() || directory.isDirectory)
            }
            val links = manifest.getJSONObject("links")
            // All symlink parents must be physical directories. No image file may
            // live below an alias; it already has its canonical manifest path.
            for (name in links.keys()) {
                check(expectedNames.none { it == name || it.startsWith("$name/") }) { "Alias shadows image file" }
                val link = child(root, name)
                val target = child(root, links.getString(name))
                check(link.parentFile!!.mkdirs() || link.parentFile!!.isDirectory)
                check(link.parentFile!!.canonicalPath == link.parentFile!!.absolutePath) { "Alias parent is not canonical" }
                val relative = link.parentFile!!.toPath().relativize(target.toPath())
                Files.createSymbolicLink(link.toPath(), relative)
            }
            check(archive.delete())
            return root
        } catch (error: Exception) {
            try { remove(staging) }
            catch (cleanup: Exception) { error.addSuppressed(cleanup) }
            throw error
        }
    }
}
