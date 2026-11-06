package junction;

import com.google.gson.*;
import net.osmand.router.junction.*;
import net.osmand.router.junction.JunctionGeometry.*;
import java.nio.file.Path;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.io.InputStream;
import java.util.*;

/** Desktop adapter only. Geometry and map reads execute the Android-side Java code. */
public final class JunctionCaptureRunner {
    private static String hash(Path file) throws Exception {
        MessageDigest digest=MessageDigest.getInstance("SHA-256");
        try (InputStream in=Files.newInputStream(file)) {
            byte[] buffer=new byte[65536];for (int n;(n=in.read(buffer))!=-1;) digest.update(buffer,0,n);
        }
        return HexFormat.of().formatHex(digest.digest());
    }
    public static void main(String[] args) throws Exception {
        if (args.length<4 || args.length>5 || (args.length==5 && !args[4].equals("--input-fixtures"))) throw new IllegalArgumentException("map capture maneuver[,maneuver] output-directory [--input-fixtures]");
        Path map=Path.of(args[0]),capture=Path.of(args[1]),out=Path.of(args[3]);Files.createDirectories(out);
        JsonObject raw=JsonParser.parseString(Files.readString(capture)).getAsJsonObject();
        if (!raw.get("status").getAsString().equals("captured") || !raw.get("coherent").getAsBoolean()) throw new IllegalArgumentException("Complete coherent capture required");
        List<Geo> points=new ArrayList<>();List<Decision> decisions=new ArrayList<>();
        for (JsonElement e:raw.getAsJsonArray("locationsLatLon")) {
            JsonArray p=e.getAsJsonArray();points.add(new Geo(p.get(0).getAsDouble(),p.get(1).getAsDouble()));
        }
        for (JsonElement e:raw.getAsJsonArray("directions")) {
            JsonObject d=e.getAsJsonObject();JsonElement name=d.get("streetName");
            decisions.add(new Decision(d.get("routePointOffset").getAsInt(),d.get("turn").getAsString(),name==null||name.isJsonNull()?"":name.getAsString(),d.get("roundaboutExit").getAsInt()));
        }
        Map<String,String> segmentRoadIds=new HashMap<>();
        for (JsonElement item:raw.getAsJsonArray("segments")) {
            JsonObject segment=item.getAsJsonObject();segmentRoadIds.put(segment.get("id").getAsString(),segment.get("roadId").getAsString());
        }
        String captureHash=hash(capture),mapHash=hash(map);
        for (String selected:args[2].split(",")) {
            int index=Integer.parseInt(selected);long started=System.nanoTime();
            Context context=new JunctionRoadReader().read(Collections.singletonList(map.toFile()),points.get(decisions.get(index).routeIndex),()->false);
            Map<String,Road> byId=new HashMap<>();for (Road road:context.roads) byId.put(road.id,road);
            List<Geo> leveled=new ArrayList<>();
            JsonArray references=raw.getAsJsonArray("locationSegmentIds");
            for (int i=0;i<points.size();i++) {
                Geo p=points.get(i);Road road=byId.get(segmentRoadIds.get(references.get(i).getAsString()));
                int level=road==null?0:JunctionLayers.level(road.tags.get("layer"),road.tags.get("bridge"),road.tags.get("tunnel"));
                leveled.add(new Geo(p.lat,p.lon,p.node,level));
            }
            Route route=new Route(leveled,decisions);
            Scene full=new JunctionCompiler().compile(route,index,context);
            Route window=JunctionWindow.copy(leveled.size(),decisions.size(),index,leveled::get,decisions::get);
            Scene scene=new JunctionCompiler().compile(window,0,context);
            if (!scene.toMap("compare",1,1,120,0,0).equals(full.toMap("compare",1,1,120,0,0))) throw new IllegalStateException("Window/full geometry differs");
            Map<String,Object> provenance=new LinkedHashMap<>();
            provenance.put("kind","actual_osmand_capture");provenance.put("captureSha256",captureHash);provenance.put("mapSha256",mapHash);
            provenance.put("applicationMode",raw.get("applicationMode").getAsString());provenance.put("maneuverIndex",index);
            provenance.put("routePointOffset",decisions.get(index).routeIndex);provenance.put("conversion","production Java JunctionWindow + JunctionCompiler + JunctionRoadReader");
            provenance.put("windowMatchesFullRoute",true);
            if (args.length==5) {
                Map<String,Object> input=new LinkedHashMap<>();input.put("provenance",provenance);input.put("route",window);input.put("context",context);
                Files.writeString(out.resolve("input-"+index+".json"),new GsonBuilder().setPrettyPrinting().create().toJson(input)+"\n");
            }
            Map<String,Object> result=new LinkedHashMap<>();result.put("provenance",provenance);result.put("scene",scene.toMap("recorded-"+captureHash.substring(0,16),1,1,120,0,0));
            Files.writeString(out.resolve("scene-"+index+".json"),new GsonBuilder().setPrettyPrinting().create().toJson(result)+"\n");
            int total=0;for (JunctionGeometry.Path p:scene.paths) total+=p.points.size();
            System.out.println("JUNCTION_JAVA maneuver="+index+" mode="+scene.mode+" paths="+scene.paths.size()+" points="+total+" elapsedMs="+(System.nanoTime()-started)/1000000);
        }
    }
}
