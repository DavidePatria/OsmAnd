package net.osmand.junction.bridge

import org.junit.Assert.*
import org.junit.Test
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.nio.file.Files

class DiagnosticLogTest {
    @Test fun rotationKeepsNewestEventsAndExportNote() {
        val dir = Files.createTempDirectory("junction-log-test").toFile()
        try {
            val log = RollingDiagnosticFiles(dir, 32)
            log.append("one-123456")
            log.append("two-123456")
            log.append("three-123456")
            log.append("four-123456")
            val output = ByteArrayOutputStream()
            log.export(output, "stopped near the junction")
            val lines = output.toString("UTF-8").lines().filter { it.isNotEmpty() }
            assertEquals("stopped near the junction", JSONObject(lines.first()).getString("note"))
            assertEquals(listOf("one-123456", "two-123456", "three-123456", "four-123456"), lines.drop(1))
            log.append("five-123456")
            log.append("six-123456")
            val latest = ByteArrayOutputStream()
            log.export(latest, "")
            assertFalse(latest.toString("UTF-8").contains("one-123456"))
            assertTrue(latest.toString("UTF-8").contains("six-123456"))
            assertTrue(dir.listFiles()!!.all { it.length() <= 32 })
            log.clear()
            assertFalse(log.exists())
        } finally { dir.deleteRecursively() }
    }
}
