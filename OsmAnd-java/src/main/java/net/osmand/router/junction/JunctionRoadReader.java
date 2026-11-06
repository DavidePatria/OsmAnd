package net.osmand.router.junction;

import net.osmand.ResultMatcher;
import net.osmand.binary.BinaryMapIndexReader;
import net.osmand.binary.BinaryMapRouteReaderAdapter.RouteRegion;
import net.osmand.binary.RouteDataObject;
import net.osmand.router.junction.JunctionGeometry.*;
import net.osmand.util.MapUtils;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.BooleanSupplier;

/** Dedicated worker-owned map streams; never use ResourceManager's shared reader. */
public final class JunctionRoadReader {
    public Context read(List<File> files,Geo center,BooleanSupplier cancelled) throws IOException {
        if (files.isEmpty()) return Context.unavailable();
        if (files.size()>32) return new Context(Collections.emptyList(),false,true);
        double dy=200.0/111000,dx=dy/Math.cos(Math.toRadians(center.lat));
        // Dateline wrapping needs two queries; explicit limited data until supported.
        if (center.lon-dx < -180 || center.lon+dx > 180) return Context.unavailable();
        int left=MapUtils.get31TileNumberX(center.lon-dx),right=MapUtils.get31TileNumberX(center.lon+dx);
        int top=MapUtils.get31TileNumberY(center.lat+dy),bottom=MapUtils.get31TileNumberY(center.lat-dy);
        List<Road> roads=new ArrayList<>();Set<String> identities=new HashSet<>();
        boolean[] truncated={false};int[] total={0};
        ResultMatcher<RouteDataObject> matcher=new ResultMatcher<RouteDataObject>() {
            @Override public boolean publish(RouteDataObject road) {
                if (cancelled.getAsBoolean()) { truncated[0]=true;return false; }
                if (road.getHighway()==null || road.getPointsLength()<2) return false;
                boolean intersects=false;
                for (int i=1;i<road.getPointsLength();i++) {
                    int ax=road.getPoint31XTile(i-1),ay=road.getPoint31YTile(i-1),bx=road.getPoint31XTile(i),by=road.getPoint31YTile(i);
                    if (Math.max(ax,bx)>=left && Math.min(ax,bx)<=right && Math.max(ay,by)>=top && Math.min(ay,by)<=bottom) { intersects=true;break; }
                }
                if (!intersects) return false;
                if (roads.size()>=512 || total[0]+road.getPointsLength()>50000) { truncated[0]=true;return false; }
                // Same road ID with differing geometry in overlapping maps is retained.
                StringBuilder identity=new StringBuilder(Long.toString(road.getId()));
                for (int i=0;i<road.getPointsLength();i++) identity.append(':').append(road.getPoint31XTile(i)).append(',').append(road.getPoint31YTile(i));
                if (!identities.add(identity.toString())) return false;
                Map<String,String> tags=new LinkedHashMap<>();tags.put("highway",road.getHighway());
                for (String tag:new String[]{"layer","bridge","tunnel","access","vehicle","motor_vehicle","motorcycle","junction"}) tags.put(tag,road.getValue(tag));
                List<Geo> points=new ArrayList<>();
                for (int i=0;i<road.getPointsLength();i++) {
                    int x=road.getPoint31XTile(i),y=road.getPoint31YTile(i);
                    points.add(new Geo(MapUtils.get31LatitudeY(y),MapUtils.get31LongitudeX(x),x+":"+y));
                }
                total[0]+=points.size();roads.add(new Road(Long.toString(road.getId()),points,tags));return false;
            }
            @Override public boolean isCancelled() { return truncated[0] || cancelled.getAsBoolean(); }
        };
        for (File map:files) {
            if (matcher.isCancelled()) { truncated[0]=true;break; }
            try (RandomAccessFile stream=new RandomAccessFile(map,"r")) {
                BinaryMapIndexReader reader=new BinaryMapIndexReader(stream,map);
                for (RouteRegion region:reader.getRoutingIndexes()) {
                    var request=BinaryMapIndexReader.buildSearchRouteRequest(left,right,top,bottom,null);
                    reader.loadRouteIndexData(reader.searchRouteIndexTree(request,region.getSubregions()),matcher);
                    if (matcher.isCancelled()) { truncated[0]=true;break; }
                }
            }
        }
        return new Context(roads,true,truncated[0]);
    }
}
