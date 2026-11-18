package io.github.mohammedteir.deepseekharness

import android.content.res.AssetManager
import java.io.File
import java.nio.file.Files
import java.nio.file.Paths
import java.security.MessageDigest
import java.util.UUID
import java.util.zip.ZipInputStream
import org.json.JSONObject

/** APK-owned interpreted data only; native libraries remain in the installer directory. */
object ProfileImage {
    private const val PROFILE_MANIFEST = "image-manifest.json"
    private const val WEB_RUNTIME_MANIFEST = "web-runtime-image-manifest.json"
    private const val WEB_RUNTIME_KIND = "original-web-runtime-candidate"
    private const val MAX_ENTRIES = 40_000
    private const val MAX_UNCOMPRESSED_BYTES = 512L * 1024 * 1024

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
                    check(!entry.isDirectory && names.add(entry.name) && names.size <= MAX_ENTRIES) {
                        "Unexpected image entry"
                    }
                    val destination = child(root, entry.name)
                    check(destination.parentFile!!.mkdirs() || destination.parentFile!!.isDirectory)
                    destination.outputStream().use { output ->
                        val buffer = ByteArray(16384)
                        while (true) {
                            val count = zip.read(buffer)
                            if (count < 0) break
                            total += count
                            check(total <= MAX_UNCOMPRESSED_BYTES) { "Interpreted image exceeds limit" }
                            output.write(buffer, 0, count)
                        }
                    }
                    zip.closeEntry()
                }
            }

            val manifestNames = listOf(PROFILE_MANIFEST, WEB_RUNTIME_MANIFEST)
                .filter { File(root, it).isFile }
            check(manifestNames.size == 1) { "Interpreted image manifest missing or ambiguous" }
            val manifestName = manifestNames.single()
            val manifest = JSONObject(File(root, manifestName).readText())
            val webRuntimeImage = manifest.optString("imageKind") == WEB_RUNTIME_KIND
            check((manifestName == WEB_RUNTIME_MANIFEST) == webRuntimeImage) { "Image kind and manifest disagree" }
            check(manifest.getInt("schemaVersion") == 1)
            val entries = manifest.getJSONObject("files")
            val fileNames = entries.keys().asSequence().toSet()
            val links = manifest.optJSONObject("links") ?: JSONObject()
            val linkNames = links.keys().asSequence().toSet()
            val expectedNames = fileNames + manifestName + if (webRuntimeImage) linkNames else emptySet()
            check(names == expectedNames) { "Image entries differ from manifest" }

            val fileBytes = manifest.optJSONObject("fileBytes")
            for (name in fileNames) {
                val file = child(root, name)
                check(file.isFile && hash(file) == entries.getString(name)) { "Interpreted file hash mismatch: $name" }
                if (fileBytes != null) {
                    check(file.length() == fileBytes.getLong(name)) { "Interpreted file size mismatch: $name" }
                }
                file.inputStream().use { input ->
                    val prefix = ByteArray(4)
                    val count = input.read(prefix)
                    check(count < 4 || !prefix.contentEquals(byteArrayOf(127, 69, 76, 70))) {
                        "Native binary in interpreted image"
                    }
                }
            }

            manifest.optJSONArray("directories")?.let { directories ->
                for (index in 0 until directories.length()) {
                    val directory = child(root, directories.getString(index))
                    check(directory.mkdirs() || directory.isDirectory)
                }
            }

            // Image v9 stores root-relative link targets in its manifest. The full
            // production image stores relative symlink entries in the ZIP itself.
            for (name in linkNames) {
                check(fileNames.none { it == name || it.startsWith("$name/") }) { "Alias shadows image file" }
                val link = child(root, name)
                val parent = link.parentFile!!
                check(parent.mkdirs() || parent.isDirectory)
                check(parent.canonicalPath == parent.absolutePath) { "Alias parent is not canonical" }
                val targetText = links.getString(name)
                if (webRuntimeImage) {
                    check(link.isFile && link.readText() == targetText) { "Packaged symlink target mismatch: $name" }
                    check(!targetText.contains('\\')) { "Invalid packaged symlink target" }
                    val targetPath = Paths.get(targetText)
                    check(!targetPath.isAbsolute) { "Absolute packaged symlink target" }
                    val rootPath = root.toPath().toAbsolutePath().normalize()
                    val resolved = parent.toPath().resolve(targetPath).normalize()
                    check(resolved.startsWith(rootPath)) { "Packaged symlink escapes image" }
                    check(link.delete()) { "Cannot prepare packaged symlink: $name" }
                    val relative = parent.toPath().relativize(resolved)
                    Files.createSymbolicLink(link.toPath(), relative)
                } else {
                    val target = child(root, targetText)
                    val relative = parent.toPath().relativize(target.toPath())
                    Files.createSymbolicLink(link.toPath(), relative)
                }
            }
            if (webRuntimeImage) {
                for (name in linkNames) {
                    check(File(root, name).exists()) { "Broken packaged symlink: $name" }
                }
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
