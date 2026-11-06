package net.osmand.junction.bridge

import com.garmin.monkeybrains.serialization.Serializer
import org.json.JSONArray
import org.junit.Assert.*
import org.junit.Test
import java.io.File

class CompactWireTest {
    @Test(expected=IllegalArgumentException::class)
    fun invalidUnicodeCannotSilentlyChangeLabels() {
        val raw=JSONArray(File("../fixtures/wire/compact.json").readText()).getJSONObject(0).getJSONObject("reply")
        val scene=SnapshotCodec.decode(raw.getJSONObject("scene").toString(),1,0,0,0).toMutableMap()
        scene["roadName"]="\uD800"
        CompactWire.encode(mapOf("version" to 1,"kind" to "junction_snapshot","epoch" to "test","requestId" to 1,"scene" to scene))
    }
    @Test fun matchesIndependentGoldenAndActualSdkByteArray() {
        val fixtures=JSONArray(File("../fixtures/wire/compact.json").readText())
        for(i in 0 until fixtures.length()) {
            val fixture=fixtures.getJSONObject(i);val r=fixture.getJSONObject("reply")
            val scene=SnapshotCodec.decode(r.getJSONObject("scene").toString(),1,0,0,0)
            val reply=mapOf("version" to 1,"kind" to "junction_snapshot","epoch" to r.getString("epoch"),"requestId" to r.getInt("requestId"),"scene" to scene)
            val data=CompactWire.encode(reply)
            assertEquals(fixture.getString("hex"),data.joinToString("") { "%02x".format(it.toInt() and 255) })
            val sdk=Serializer.serialize(data)
            val decoded=Serializer.deserialize(sdk).single()
            assertEquals("MonkeyByteArray",decoded.javaClass.simpleName)
            assertEquals(data.map { it.toInt() and 255 },(decoded.toJava() as List<*>).map { (it as Number).toInt() and 255 })
            assertTrue(sdk.size<600)
        }
    }
}
