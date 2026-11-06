package net.osmand.router.junction;

import com.google.gson.*;
import net.osmand.router.junction.JunctionGeometry.*;
import org.junit.Test;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import static org.junit.Assert.*;

/** Real OBF/native-route input; assertions follow independently captured native turns. */
public class RecordedJunctionTest {
    private static Geo geo(JsonObject p) {
        return new Geo(p.get("lat").getAsDouble(),p.get("lon").getAsDouble(),p.has("node")?p.get("node").getAsString():null);
    }
    private static List<Geo> points(JsonArray input) {
        List<Geo> result=new ArrayList<>();for (JsonElement p:input) result.add(geo(p.getAsJsonObject()));return result;
    }
    private static Scene compile(String name) throws IOException {
        InputStream input=RecordedJunctionTest.class.getResourceAsStream("/junction/"+name+".json");assertNotNull(input);
        try (Reader reader=new InputStreamReader(input,StandardCharsets.UTF_8)) {
            JsonObject raw=JsonParser.parseReader(reader).getAsJsonObject();JsonObject r=raw.getAsJsonObject("route");
            assertEquals("motorcycle",raw.getAsJsonObject("provenance").get("applicationMode").getAsString());
            List<Decision> decisions=new ArrayList<>();
            for (JsonElement value:r.getAsJsonArray("decisions")) {
                JsonObject d=value.getAsJsonObject();decisions.add(new Decision(d.get("routeIndex").getAsInt(),d.get("turn").getAsString(),d.get("roadName").getAsString(),d.get("roundaboutExit").getAsInt()));
            }
            Route route=new Route(points(r.getAsJsonArray("points")),decisions,r.get("indexBase").getAsInt());
            JsonObject c=raw.getAsJsonObject("context");List<Road> roads=new ArrayList<>();
            for (JsonElement value:c.getAsJsonArray("roads")) {
                JsonObject road=value.getAsJsonObject();Map<String,String> tags=new LinkedHashMap<>();
                for (Map.Entry<String,JsonElement> entry:road.getAsJsonObject("tags").entrySet()) tags.put(entry.getKey(),entry.getValue().isJsonNull()?null:entry.getValue().getAsString());
                roads.add(new Road(road.get("id").getAsString(),points(road.getAsJsonArray("points")),tags));
            }
            Scene scene=new JunctionCompiler().compile(route,0,new Context(roads,c.get("available").getAsBoolean(),c.get("truncated").getAsBoolean()));
            assertEquals("map_context",scene.mode);assertTrue(scene.paths.size()>1);assertTrue(scene.paths.size()<=32);
            int total=0;
            for (JunctionGeometry.Path path:scene.paths) {
                total+=path.points.size();assertTrue(path.points.size()<=48);
                if (path.role.equals("context")) assertTrue(path.anchorIndexes.isEmpty());
                for (Point p:path.points) assertTrue(p.x*p.x+p.y*p.y<=800*800);
            }
            assertTrue(total<=512);return scene;
        }
    }
    @Test public void actualCloseRightTurnsRetainBothOriginalAnchors() throws IOException {
        Scene scene=compile("public-double-turn");assertEquals("TR",scene.maneuver);
        assertEquals(2,scene.anchors.size());assertEquals(75,scene.anchors.get(0).routeIndex);assertEquals(82,scene.anchors.get(1).routeIndex);
        JunctionGeometry.Path selected=scene.paths.get(0);
        int first=selected.anchorIndexes.get(0),second=selected.anchorIndexes.get(1);
        assertTrue(first<second);assertTrue(selected.points.get(first+1).x>scene.anchors.get(0).point.x);
        Point before=selected.points.get(second-1),at=selected.points.get(second),after=selected.points.get(second+1);
        assertTrue((at.x-before.x)*(after.y-at.y)-(at.y-before.y)*(after.x-at.x)<0);
    }
    @Test public void actualSlightLeftForkRetainsNativeIndexAndSelectedSide() throws IOException {
        Scene scene=compile("public-fork");assertEquals("TSLL",scene.maneuver);
        assertEquals(219,scene.anchors.get(0).routeIndex);
        JunctionGeometry.Path selected=scene.paths.get(0);
        assertTrue(selected.points.get(selected.points.size()-1).x<scene.anchors.get(0).point.x);
    }
}
