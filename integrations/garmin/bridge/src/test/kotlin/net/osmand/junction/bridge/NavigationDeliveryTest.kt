package net.osmand.junction.bridge

import org.junit.Assert.*
import org.junit.Test
import org.json.JSONObject

class NavigationDeliveryTest {
    @Test fun layeredDrawingMetadataIsOwnedAndForwarded() {
        val raw=JSONObject(scene());raw.put("geometryMode","layer_context")
        val selected=raw.getJSONArray("paths").getJSONObject(0)
        selected.put("layer",0).put("segmentLayers",org.json.JSONArray(listOf(0,1)))
        val decoded=SnapshotCodec.decode(raw.toString(),1,0,0,0)
        selected.getJSONArray("segmentLayers").put(0,9)
        val path=(decoded["paths"] as List<*>)[0] as Map<*, *>
        assertEquals(listOf(0,1),path["segmentLayers"]);assertEquals(0,path["layer"])
    }
    @Test fun layerMetadataCannotBeIgnoredOrMisSized() {
        val raw=JSONObject(scene());val path=raw.getJSONArray("paths").getJSONObject(0);path.put("layer",1)
        assertThrows(IllegalArgumentException::class.java) { SnapshotCodec.decode(raw.toString(),1,0,0,0) }
        raw.put("geometryMode","layer_context");path.put("segmentLayers",org.json.JSONArray(listOf(0)))
        assertThrows(IllegalArgumentException::class.java) { SnapshotCodec.decode(raw.toString(),1,0,0,0) }
    }
    private fun request(id:Int=1,epoch:String="watch")=mapOf("version" to 1,"kind" to "junction_request","epoch" to epoch,"requestId" to id)
    private fun scene()="""{"version":1,"session":"test","generation":1,"seq":1,"state":"active","geometryMode":"route_only","reason":"test","distanceM":120,"roadName":"Test","maneuver":"TR","radiusDm":800,"sourceAgeMs":50,"fixAgeMs":100,"progressAgeMs":100,"speedDmps":0,"anchors":[{"id":"a","point":[0,0],"routeIndex":1}],"paths":[{"id":"route","role":"selected","points":[[0,-100],[0,0],[100,0]],"anchorRefs":[["a",1]]}]}"""
    @Test fun oneSlotAndOldCallbackCannotReleaseLaterRequest() {
        val gate=NavigationDelivery();val first=gate.begin(request(),0)!!
        assertNull(gate.begin(request(2),100));gate.finish(first)
        val second=gate.begin(request(2),100)!!;gate.finish(first)
        assertNull(gate.begin(request(3),200));assertNotNull(gate.response(second,emptyMap(),200));gate.finish(second)
    }
    @Test fun connectionChangesAndDeadlinesRejectOldWork() {
        val gate=NavigationDelivery();val first=gate.begin(request(),0)!!
        assertNull(gate.response(first,emptyMap(),3000));assertNull(gate.response(first,emptyMap(),-1))
        gate.connectionChanged();assertNull(gate.response(first,emptyMap(),100));assertNull(gate.begin(request(2),100))
        gate.finish(first);assertNotNull(gate.begin(request(2),101))
    }
    @Test fun replayedRetiredAndMalformedRequestsAreRejected() {
        val gate=NavigationDelivery();val first=gate.begin(request(),0)!!;gate.finish(first)
        assertNull(gate.begin(request(),100));val second=gate.begin(request(1,"new-watch"),100)!!;gate.finish(second)
        assertNull(gate.begin(request(2),200));assertNull(gate.begin(request(0,"invalid"),200))
        assertNull(gate.begin(mapOf("kind" to "junction_request","version" to 1,"epoch" to "x","requestId" to 1.0),200))
    }
    @Test fun codecAddsActualApiAgeAndKeepsUnknownFieldsOffWire() {
        val raw=JSONObject(scene()).put("futureField","unused")
        val result=SnapshotCodec.decode(raw.toString(),1,1000,50,1250)
        assertEquals(300,result["sourceAgeMs"]);assertEquals(350,result["fixAgeMs"]);assertEquals(350,result["progressAgeMs"])
        assertFalse(result.containsKey("futureField"));assertEquals(0,result["speedDmps"])
    }
    @Test fun codecRejectsOldWrapperBadGeometryAndFakeAge() {
        for (test in listOf<()->Unit>(
            { SnapshotCodec.decode(scene(),2,1000,0,1000) },
            { SnapshotCodec.decode(scene(),1,1001,0,1000) },
            { SnapshotCodec.decode(JSONObject(scene()).put("fixAgeMs",-1).toString(),1,0,0,0) },
            { SnapshotCodec.decode(scene().replace("[100,0]","[799,799]"),1,0,0,0) },
            { SnapshotCodec.decode(scene().replace("[\"a\",1]","[\"missing\",1]"),1,0,0,0) })) {
            try { test();fail("invalid snapshot accepted") } catch (_:IllegalArgumentException) { }
        }
    }
    @Test fun unavailableReplyIsScopedAndCannotOutliveRequest() {
        val gate=NavigationDelivery();val ticket=gate.begin(request(),0)!!
        val reply=gate.unavailable(ticket,"source_busy",100)!!
        assertEquals("junction_unavailable",reply["kind"]);assertEquals("watch",reply["epoch"])
        assertFalse(reply.containsKey("scene"));assertNull(gate.unavailable(ticket,"source_busy",3000))
        gate.connectionChanged();assertNull(gate.unavailable(ticket,"source_busy",200))
    }
    @Test fun drawingAckMustBeCompleteAndTyped() {
        val gate=NavigationDelivery()
        assertNull(gate.begin(request()+mapOf("displayedSeq" to 1),0))
        val ack=mapOf("displayedSession" to "source","displayedGeneration" to 1,"displayedSeq" to 1,"displayedState" to "active")
        val ticket=gate.begin(request()+ack,1)!!;gate.finish(ticket)
        assertNull(gate.begin(request(2)+ack+mapOf("displayedGeneration" to 1.0),2))
    }
}
