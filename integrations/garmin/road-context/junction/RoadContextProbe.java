package junction;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.osmand.ResultMatcher;
import net.osmand.binary.BinaryMapIndexReader;
import net.osmand.binary.BinaryMapRouteReaderAdapter.RouteRegion;
import net.osmand.binary.RouteDataObject;
import net.osmand.util.MapUtils;

import java.io.InputStream;
import java.io.RandomAccessFile;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;

/** Read-only diagnostic of the SAME OBF, before profile and one-way filtering.
 * This is road context, not proof that intersecting lines are connected.
 */
public final class RoadContextProbe {
    private static String sha256(Path path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream in = Files.newInputStream(path)) {
            byte[] buffer = new byte[65536];
            for (int count; (count = in.read(buffer)) != -1;) digest.update(buffer, 0, count);
        }
        return HexFormat.of().formatHex(digest.digest());
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 4) throw new IllegalArgumentException("map.obf capture.json maneuver output.json");
        if (args[2].contains(",")) {
            for (String index : args[2].split(",")) {
                main(new String[]{args[0],args[1],index,Path.of(args[3]).resolve("context-"+Integer.parseInt(index)+".json").toString()});
            }
            return;
        }
        Path map = Path.of(args[0]), capture = Path.of(args[1]), output = Path.of(args[3]);
        JsonObject route = JsonParser.parseString(Files.readString(capture)).getAsJsonObject();
        if (!"captured".equals(route.get("status").getAsString()) || !route.get("coherent").getAsBoolean()) {
            throw new IllegalArgumentException("A complete coherent capture is required");
        }
        int maneuver = Integer.parseInt(args[2]);
        JsonArray locations = route.getAsJsonArray("locationsLatLon");
        int index = route.getAsJsonArray("directions").get(maneuver).getAsJsonObject().get("routePointOffset").getAsInt();
        JsonArray center = locations.get(index).getAsJsonArray();
        double lat = center.get(0).getAsDouble(), lon = center.get(1).getAsDouble();
        if (!Double.isFinite(lat) || !Double.isFinite(lon) || Math.abs(lat) > 80 || Math.abs(lon) > 180) {
            throw new IllegalArgumentException("Unsupported query coordinates");
        }
        // Bounded local query. Whole road objects may extend beyond this box;
        // the scene compiler clips their geometry to its smaller display circle.
        double dy = 200.0 / 111000, dx = dy / Math.cos(Math.toRadians(lat));
        int left = MapUtils.get31TileNumberX(lon-dx), right = MapUtils.get31TileNumberX(lon+dx);
        int top = MapUtils.get31TileNumberY(lat+dy), bottom = MapUtils.get31TileNumberY(lat-dy);
        Map<Long, RouteDataObject> roads = new LinkedHashMap<>();
        boolean[] truncated = {false};
        int[] pointCount = {0};
        ResultMatcher<RouteDataObject> matcher = new ResultMatcher<>() {
            public boolean publish(RouteDataObject road) {
                if (road.getHighway() == null || roads.containsKey(road.getId())) return false;
                boolean intersects = false;
                for (int i=1; i<road.getPointsLength(); i++) {
                    int ax=road.getPoint31XTile(i-1), ay=road.getPoint31YTile(i-1);
                    int bx=road.getPoint31XTile(i), by=road.getPoint31YTile(i);
                    if (Math.max(ax,bx)>=left && Math.min(ax,bx)<=right && Math.max(ay,by)>=top && Math.min(ay,by)<=bottom) {
                        intersects=true;break;
                    }
                }
                if (!intersects) return false;
                if (roads.size()>=512 || pointCount[0]+road.getPointsLength()>50000) {
                    truncated[0]=true;return false;
                }
                roads.put(road.getId(),road);pointCount[0]+=road.getPointsLength();return false;
            }
            public boolean isCancelled() { return truncated[0]; }
        };
        try (RandomAccessFile file = new RandomAccessFile(map.toFile(),"r")) {
            BinaryMapIndexReader reader = new BinaryMapIndexReader(file, map.toFile());
            for (RouteRegion region : reader.getRoutingIndexes()) {
                var request = BinaryMapIndexReader.buildSearchRouteRequest(left,right,top,bottom,null);
                reader.loadRouteIndexData(reader.searchRouteIndexTree(request,region.getSubregions()),matcher);
                if (truncated[0]) break;
            }
        }
        JsonObject result = new JsonObject();
        result.addProperty("version",1);result.addProperty("kind","same_obf_unfiltered_routing_roads");
        result.addProperty("accessTagsVersion",1);
        result.addProperty("captureSha256",sha256(capture));result.addProperty("mapSha256",sha256(map));
        result.addProperty("maneuver",maneuver);result.add("centerLatLon",center.deepCopy());
        result.addProperty("queryHalfWidthM",200);result.addProperty("truncated",truncated[0]);
        JsonArray objects = new JsonArray();
        for (RouteDataObject road : roads.values()) {
            JsonObject object = new JsonObject();
            object.addProperty("roadId",Long.toString(road.getId()));object.addProperty("highway",road.getHighway());
            object.addProperty("name",road.getName());object.addProperty("oneway",road.getOneway());
            for (String tag : new String[]{"layer","bridge","tunnel","access","vehicle","motor_vehicle","motorcycle","junction"}) {
                object.addProperty(tag,road.getValue(tag));
            }
            JsonArray points = new JsonArray();
            for (int i=0; i<road.getPointsLength(); i++) {
                int x=road.getPoint31XTile(i), y=road.getPoint31YTile(i);
                JsonArray p = new JsonArray();p.add(x);p.add(y);p.add(MapUtils.get31LatitudeY(y));p.add(MapUtils.get31LongitudeX(x));points.add(p);
            }
            object.add("points31LatLon",points);objects.add(object);
        }
        result.add("roads",objects);
        Files.createDirectories(output.toAbsolutePath().getParent());
        Files.writeString(output,new GsonBuilder().setPrettyPrinting().serializeNulls().create().toJson(result)+"\n");
        System.out.println("JUNCTION_CONTEXT roads="+roads.size()+" points="+pointCount[0]+" truncated="+truncated[0]);
    }
}
