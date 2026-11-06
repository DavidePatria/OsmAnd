package net.osmand.junction.bridge

import com.garmin.monkeybrains.serialization.MonkeyArray
import com.garmin.monkeybrains.serialization.MonkeyHash
import com.garmin.monkeybrains.serialization.MonkeyType
import com.garmin.monkeybrains.serialization.Serializer
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.io.File

/** Actual SDK 2.4.0 wire encoding; no Bluetooth, Android mocks or substitute codec. */
class SdkSerializationTest {
    private fun scene(): MutableMap<String, Any> {
        val raw=JSONObject(File("../fixtures/contract/snapshot.json").readText()).getJSONObject("scene")
        return SnapshotCodec.decode(raw.toString(),1,0,0,0).toMutableMap()
    }

    @Test fun nestedSceneRoundTripsAsSdkIntegerContainers() {
        val packet=SdkWireProbe.envelope(scene())
        assertTrue(SdkWireProbe.roundTrip(packet)<16_384)
    }

    @Test fun unicodeRoadNameSurvivesActualSdkWireEncoding() {
        val scene=scene();scene["roadName"]="Via dell'Unità – 🏍"
        assertTrue(SdkWireProbe.roundTrip(SdkWireProbe.envelope(scene))<16_384)
    }

    @Test fun maximumGeometryAndStringBudgetsHaveWireHeadroom() {
        val scene=scene()
        scene["session"]="界".repeat(64);scene["roadName"]="路".repeat(80)
        scene["reason"]="景".repeat(80);scene["maneuver"]="向".repeat(80)
        scene["geometryMode"]="map_context"
        val anchors=(0..3).map { i -> mapOf("id" to "節".repeat(31)+(0x4E00+i).toChar(),"routeIndex" to 999_997+i,"point" to listOf(i*10,0)) }
        scene["anchors"]=anchors
        scene["paths"]=(0..31).map { i -> mapOf(
            "id" to "路".repeat(31)+(0x4E00+i).toChar(),"role" to if(i==0)"selected" else "context",
            "points" to (0..15).map { n -> listOf(n*10,i) },
            "anchorRefs" to if(i==0)anchors.mapIndexed { n,a -> listOf(a["id"],n) } else emptyList<Any>()) }
        SnapshotCodec.validate(scene)
        val bytes=SdkWireProbe.roundTrip(SdkWireProbe.envelope(scene))
        println("SDK_WIRE_MAX_GEOMETRY bytes=$bytes limit=16384")
        assertTrue("Maximum valid bounded packet exceeds SDK limit: $bytes",bytes<16_384)
        scene["geometryMode"]="layer_context"
        scene["paths"]=(0..39).map { i ->
            val count=if(i==0)48 else if(i<=35)12 else 11
            linkedMapOf<String,Any>("id" to "路".repeat(23)+(0x4E00+i).toChar(),"role" to if(i==0)"selected" else "context",
                "points" to (0 until count).map { n -> listOf(n*10,i) },"layer" to i%2,
                "anchorRefs" to if(i==0)anchors.mapIndexed { n,a -> listOf(a["id"],n) } else emptyList<Any>()).apply {
                if(i==0)put("segmentLayers",List(count-1) { it%2 })
            }
        }
        SnapshotCodec.validate(scene)
        val layeredBytes=SdkWireProbe.roundTrip(SdkWireProbe.envelope(scene))
        println("SDK_WIRE_MAX_LAYERED bytes=$layeredBytes limit=16384")
        assertTrue(layeredBytes<16_384)
        val compact=SdkWireProbe.compactRoundTrip(SdkWireProbe.envelope(scene))
        println("SDK_WIRE_MAX_LAYERED_COMPACT bytes=$compact limit=16384")
        assertTrue(compact<8192+32)
    }

    @Test fun unavailableReplyRoundTripsThroughActualSdk() {
        val gate=NavigationDelivery();val ticket=gate.begin(mapOf("version" to 1,"kind" to "junction_request","epoch" to "watch","requestId" to 1),0)!!
        val packet=checkNotNull(gate.unavailable(ticket,"source_disconnected",1))
        assertTrue(SdkWireProbe.roundTrip(packet)<1024)
        assertTrue(SdkWireProbe.compactRoundTrip(packet)<600)
    }
}

/** Optional private JSONL measurement, invoked by verifySdkSamples (not a skipped test). */
object SdkWireProbe {
    fun compactRoundTrip(packet: Map<String,Any>): Int {
        val compact=CompactWire.encode(packet)
        val wire=Serializer.serialize(compact)
        val value=Serializer.deserialize(wire).single()
        check(value.javaClass.simpleName=="MonkeyByteArray")
        check((value.toJava() as List<*>).map { (it as Number).toInt() and 255 }==compact.map { it.toInt() and 255 })
        return wire.size
    }
    fun envelope(scene: Map<String, Any>): Map<String, Any> {
        val gate=NavigationDelivery();val ticket=checkNotNull(gate.begin(mapOf("version" to 1,"kind" to "junction_request","epoch" to "時".repeat(64),"requestId" to 1_000_000),0))
        return checkNotNull(gate.response(ticket,scene,1))
    }
    private fun javaValue(value: MonkeyType<*>): Any? = when(value) {
        is MonkeyHash -> value.toJava().entries.associate { javaValue(it.key) to javaValue(it.value) }
        is MonkeyArray -> value.toJava().map { javaValue(it) }
        else -> value.toJava()
    }
    fun roundTrip(packet: Map<String, Any>): Int {
        val wire=Serializer.serialize(packet)
        val values=Serializer.deserialize(wire)
        check(values.size==1 && javaValue(values.single())==packet) { "Actual SDK wire changed values or numeric/container types" }
        return wire.size
    }
    @JvmStatic fun main(args: Array<String>) {
        require(args.size==2);val sizes=mutableListOf<Int>();val compactSizes=mutableListOf<Int>()
        File(args[0]).useLines { lines -> lines.forEach { line ->
            val api=JSONObject(line).getJSONObject("api")
            check(api.getString("status")=="decoded") { "Input contains an undecoded sample" }
            val scene=SnapshotCodec.decode(api.getJSONObject("scene").toString(),1,0,0,0)
            sizes.add(roundTrip(envelope(scene)))
            compactSizes.add(compactRoundTrip(envelope(scene)))
        } }
        check(sizes.isNotEmpty() && sizes.max()<16_384)
        val report=JSONObject().put("status","pass").put("serializer","actual companion SDK 2.4.0")
            .put("headerMode","maximum-length test epoch/request; actual scene preserved")
            .put("samples",sizes.size).put("maximumBytes",sizes.max()).put("minimumBytes",sizes.min())
            .put("compactMaximumBytes",compactSizes.max()).put("compactMinimumBytes",compactSizes.min())
            .put("sdkLimitBytes",16_384).put("minimumHeadroomBytes",16_384-sizes.max())
            .put("scope","real SDK wire serialization/round trip; not Bluetooth or native simulator receipt")
        File(args[1]).apply { parentFile?.mkdirs();writeText(report.toString(2)+"\n") }
        println(report.toString())
    }
}
