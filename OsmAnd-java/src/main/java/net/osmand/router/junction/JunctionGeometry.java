package net.osmand.router.junction;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Immutable boundary between routing/map reads and background geometry work. */
public final class JunctionGeometry {
    private JunctionGeometry() { }

    private static <T> List<T> copy(List<T> list) {
        return Collections.unmodifiableList(new ArrayList<>(list));
    }

    public static final class Geo {
        public final double lat, lon;
        public final String node;
        /** Drawing layer of the outgoing route edge; ordinary 2D inputs use zero. */
        public final int layer;
        public Geo(double lat, double lon) { this(lat, lon, null); }
        public Geo(double lat, double lon, String node) {
            this(lat,lon,node,0);
        }
        public Geo(double lat, double lon, String node,int layer) {
            if (!Double.isFinite(lat) || !Double.isFinite(lon) || Math.abs(lat)>80 || Math.abs(lon)>180) {
                throw new IllegalArgumentException("Unsupported junction coordinates");
            }
            if (layer < -10 || layer > 10) throw new IllegalArgumentException("Unsupported road layer");
            this.lat=lat;this.lon=lon;this.node=node;this.layer=layer;
        }
    }

    public static final class Decision {
        public final int routeIndex, roundaboutExit;
        public final String turn, roadName;
        public Decision(int routeIndex, String turn, String roadName, int roundaboutExit) {
            this.routeIndex=routeIndex;this.turn=shortText(turn);this.roadName=shortText(roadName);
            this.roundaboutExit=Math.max(0,roundaboutExit);
        }
    }

    public static final class Route {
        public final List<Geo> points;
        public final List<Decision> decisions;
        public final int indexBase;
        public final int destinationIndex;
        public Route(List<Geo> points, List<Decision> decisions) {
            this(points,decisions,0,points.size()-1);
        }
        /** Windowed input retains the original native route point indexes. */
        public Route(List<Geo> points, List<Decision> decisions,int indexBase) {
            this(points,decisions,indexBase,-1);
        }
        public Route(List<Geo> points, List<Decision> decisions,int indexBase,int destinationIndex) {
            if (points.size()<2 || points.size()>10000 || decisions.size()>2000 || indexBase<0 || indexBase>1000000) {
                throw new IllegalArgumentException("Route input bounds");
            }
            int previous=-1;
            for (Decision d:decisions) {
                if (d.routeIndex>1000000 || d.routeIndex<previous || d.routeIndex<indexBase || d.routeIndex-indexBase>=points.size()) {
                    throw new IllegalArgumentException("Original decision index/order");
                }
                previous=d.routeIndex;
            }
            if (destinationIndex < -1 || destinationIndex>1000000 || (destinationIndex>=0 && destinationIndex<indexBase+points.size()-1)) throw new IllegalArgumentException("Destination index");
            this.points=copy(points);this.decisions=copy(decisions);this.indexBase=indexBase;this.destinationIndex=destinationIndex;
        }
    }

    public static final class Road {
        public final String id;
        public final List<Geo> points;
        public final Map<String,String> tags;
        public Road(String id, List<Geo> points, Map<String,String> tags) {
            this.id=id;this.points=copy(points);
            this.tags=Collections.unmodifiableMap(new LinkedHashMap<>(tags));
        }
    }

    public static final class Context {
        public final List<Road> roads;
        public final boolean available, truncated;
        public Context(List<Road> roads, boolean available, boolean truncated) {
            int points=0;
            for (Road r:roads) points+=r.points.size();
            if (roads.size()>512 || points>50000) throw new IllegalArgumentException("Road input bounds");
            this.roads=copy(roads);this.available=available;this.truncated=truncated;
        }
        public static Context unavailable() { return new Context(Collections.emptyList(),false,false); }
    }

    public static final class Point {
        public final int x,y;
        public Point(int x,int y) { this.x=x;this.y=y; }
        public List<Integer> pair() {
            List<Integer> p=new ArrayList<>();p.add(x);p.add(y);return p;
        }
    }

    public static final class Anchor {
        public final String id;
        public final int routeIndex;
        public final Point point;
        public Anchor(String id,int routeIndex,Point point) { this.id=id;this.routeIndex=routeIndex;this.point=point; }
    }

    public static final class Path {
        public final String id,role;
        public final List<Point> points;
        public final List<Integer> anchorIndexes;
        public final int layer;
        public final List<Integer> segmentLayers;
        public Path(String id,String role,List<Point> points,List<Integer> anchorIndexes) {
            this(id,role,points,anchorIndexes,0,Collections.emptyList());
        }
        public Path(String id,String role,List<Point> points,List<Integer> anchorIndexes,int layer,List<Integer> segmentLayers) {
            this.id=id;this.role=role;this.points=copy(points);this.anchorIndexes=copy(anchorIndexes);
            this.layer=layer;this.segmentLayers=copy(segmentLayers);
        }
    }

    public static final class Scene {
        public final String mode,reason,roadName,maneuver;
        public final int radiusDm,roundaboutExit;
        public final List<Anchor> anchors;
        public final List<Path> paths;
        public final Point destination;
        public Scene(String mode,String reason,Decision decision,int radiusDm,List<Anchor> anchors,List<Path> paths) {
            this.mode=mode;this.reason=shortText(reason);this.roadName=decision.roadName;this.maneuver=decision.turn;
            this.roundaboutExit=decision.roundaboutExit;this.radiusDm=radiusDm;this.anchors=copy(anchors);this.paths=copy(paths);
            this.destination=null;
        }
        private Scene(Scene source,Point destination) {
            this.mode=source.mode;this.reason=source.reason;this.roadName=source.roadName;this.maneuver=source.maneuver;
            this.radiusDm=source.radiusDm;this.roundaboutExit=source.roundaboutExit;this.anchors=source.anchors;this.paths=source.paths;this.destination=destination;
        }
        public Scene withDestination(Point point) { return new Scene(this,point); }

        /** Fresh scalar/list/map copy; serialization cannot mutate the cached scene. */
        public Map<String,Object> toMap(String session,int generation,int seq,int distanceM,int sourceAgeMs,int fixAgeMs) {
            Map<String,Object> value=new LinkedHashMap<>();
            value.put("version",1);value.put("session",session);value.put("generation",generation);value.put("seq",seq);
            value.put("state","active");value.put("geometryMode",mode);value.put("reason",reason);
            value.put("roadName",roadName);value.put("maneuver",maneuver);value.put("roundaboutExit",roundaboutExit);
            value.put("radiusDm",radiusDm);value.put("distanceM",distanceM);value.put("sourceAgeMs",sourceAgeMs);value.put("fixAgeMs",fixAgeMs);
            List<Object> aa=new ArrayList<>(),pp=new ArrayList<>();
            for (Anchor a:anchors) {
                Map<String,Object> item=new LinkedHashMap<>();item.put("id",a.id);item.put("routeIndex",a.routeIndex);item.put("point",a.point.pair());aa.add(item);
            }
            for (Path p:paths) {
                Map<String,Object> item=new LinkedHashMap<>();item.put("id",p.id);item.put("role",p.role);
                List<Object> points=new ArrayList<>(),links=new ArrayList<>();
                for (Point point:p.points) points.add(point.pair());
                for (int i=0;i<p.anchorIndexes.size();i++) {
                    List<Object> link=new ArrayList<>();link.add(anchors.get(i).id);link.add(p.anchorIndexes.get(i));links.add(link);
                }
                item.put("points",points);item.put("anchorRefs",links);pp.add(item);
                if (mode.equals("layer_context")) {
                    item.put("layer",p.layer);
                    if (p.role.equals("selected")) item.put("segmentLayers",new ArrayList<>(p.segmentLayers));
                }
            }
            value.put("anchors",aa);value.put("paths",pp);
            if (destination!=null) value.put("destination",destination.pair());
            return value;
        }
    }

    private static String shortText(String text) { return text==null?"":text.substring(0,Math.min(80,text.length())); }
}
