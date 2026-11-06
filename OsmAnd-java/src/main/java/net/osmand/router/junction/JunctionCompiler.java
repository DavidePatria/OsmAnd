package net.osmand.router.junction;

import net.osmand.router.junction.JunctionGeometry.*;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.BitSet;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Bounded, Android-independent implementation of the approved fixed diagram. */
public final class JunctionCompiler {
    public static final int MAX_PATHS=32,MAX_LAYER_PATHS=40,MAX_PATH_POINTS=48,MAX_POINTS=512;
    private static final double EARTH=6371000,RADIUS=75;
    private static final Set<String> NON_MOTOR=new HashSet<>(Arrays.asList("footway","cycleway","path","pedestrian","steps","bridleway","corridor","platform"));
    private static final Set<String> MOTOR_ACCESS=new HashSet<>(Arrays.asList("yes","permissive","designated","destination","delivery","customers","private","permit","agricultural","forestry","discouraged"));

    public static String nonMotorReason(Map<String,String> tags) {
        for (String key:new String[]{"motorcycle","motor_vehicle","vehicle","access"}) {
            String value=tags.get(key);
            if ("no".equals(value) || "dismount".equals(value) || "use_sidepath".equals(value)) return key+"="+value;
            if (MOTOR_ACCESS.contains(value)) return null;
        }
        return NON_MOTOR.contains(tags.get("highway"))?"non-motor highway="+tags.get("highway"):null;
    }

    private static double delta(double degrees) { return Math.atan2(Math.sin(Math.toRadians(degrees)),Math.cos(Math.toRadians(degrees))); }
    public static double distance(Geo a,Geo b) {
        return EARTH*Math.hypot(delta(b.lon-a.lon)*Math.cos(Math.toRadians((a.lat+b.lat)/2)),Math.toRadians(b.lat-a.lat));
    }
    private static final class XY {
        final double x,y;
        XY(double x,double y) { this.x=x;this.y=y; }
        XY between(XY b,double t) { return new XY(x+(b.x-x)*t,y+(b.y-y)*t); }
        double norm() { return Math.hypot(x,y); }
    }
    private static final class Frame {
        final Geo origin;
        final double sin,cos;
        Frame(Geo origin,Geo approach) {
            this.origin=origin;XY a=eastNorth(approach);double bearing=Math.atan2(-a.x,-a.y);
            sin=Math.sin(bearing);cos=Math.cos(bearing);
        }
        XY eastNorth(Geo p) { return new XY(delta(p.lon-origin.lon)*EARTH*Math.cos(Math.toRadians(origin.lat)),Math.toRadians(p.lat-origin.lat)*EARTH); }
        XY project(Geo p) { XY a=eastNorth(p);return new XY(a.x*cos-a.y*sin,a.x*sin+a.y*cos); }
    }

    public Scene compile(Route route,int maneuver,Context context) {
        Scene scene=compileGeometry(route,maneuver,context);
        if (!scene.paths.isEmpty() && route.destinationIndex==route.indexBase+route.points.size()-1) {
            int anchor=route.decisions.get(maneuver).routeIndex-route.indexBase;double remaining=0;
            for(int i=anchor+1;i<route.points.size();i++) remaining+=distance(route.points.get(i-1),route.points.get(i));
            if (remaining<=RADIUS) {
                Path selected=scene.paths.get(0);
                return scene.withDestination(selected.points.get(selected.points.size()-1));
            }
        }
        return scene;
    }

    private Scene compileGeometry(Route route,int maneuver,Context context) {
        if (maneuver<0 || maneuver>=route.decisions.size()) throw new IllegalArgumentException("Decision index");
        Decision d=route.decisions.get(maneuver);int offset=d.routeIndex-route.indexBase;
        double[] cumulative=new double[route.points.size()];
        // Sum outwards from this decision so a cropped route window gives the
        // same frame/interpolation as the full route, without prefix rounding.
        for (int i=offset+1;i<cumulative.length;i++) cumulative[i]=cumulative[i-1]+distance(route.points.get(i-1),route.points.get(i));
        for (int i=offset-1;i>=0;i--) cumulative[i]=cumulative[i+1]-distance(route.points.get(i),route.points.get(i+1));
        int approach=offset>0?offset-1:0;
        while (approach>0 && cumulative[offset]-cumulative[approach]<30) approach--;
        if (cumulative[offset]-cumulative[approach]<.1) return unavailable(d,"approach tangent unavailable");
        Frame frame=new Frame(route.points.get(offset),route.points.get(approach));
        List<Integer> indexes=new ArrayList<>();indexes.add(offset);
        for (int i=maneuver+1;i<route.decisions.size();i++) {
            int next=route.decisions.get(i).routeIndex-route.indexBase;
            if (cumulative[next]-cumulative[offset]>RADIUS) break;
            if (next>indexes.get(indexes.size()-1)) {
                if (indexes.size()==4) return unavailable(d,"decision anchor capacity exceeded");
                indexes.add(next);
            }
        }
        int first=offset,last=offset;
        while (first>0 && cumulative[offset]-cumulative[first-1]<=RADIUS) first--;
        while (last+1<cumulative.length && cumulative[last+1]-cumulative[offset]<=RADIUS) last++;
        List<XY> selected=new ArrayList<>();int prefix=0;
        if (first>0) {
            double t=(cumulative[offset]-RADIUS-cumulative[first-1])/(cumulative[first]-cumulative[first-1]);
            selected.add(frame.project(route.points.get(first-1)).between(frame.project(route.points.get(first)),t));prefix=1;
        }
        for (int i=first;i<=last;i++) selected.add(frame.project(route.points.get(i)));
        if (last+1<cumulative.length) {
            double t=(cumulative[offset]+RADIUS-cumulative[last])/(cumulative[last+1]-cumulative[last]);
            selected.add(frame.project(route.points.get(last)).between(frame.project(route.points.get(last+1)),t));
        }
        BitSet fixed=new BitSet();
        List<Integer> selectedLevels=new ArrayList<>();
        if (prefix==1) selectedLevels.add(route.points.get(first-1).layer);
        for (int i=first;i<last;i++) selectedLevels.add(route.points.get(i).layer);
        if (last+1<cumulative.length) selectedLevels.add(route.points.get(last).layer);
        for (int i=1;i<selectedLevels.size();i++) {
            if (!selectedLevels.get(i-1).equals(selectedLevels.get(i))) fixed.set(i);
        }
        List<Anchor> anchors=new ArrayList<>();
        for (int i=0;i<indexes.size();i++) {
            int k=indexes.get(i);fixed.set(k-first+prefix);anchors.add(new Anchor("j"+i,k+route.indexBase,quantize(frame.project(route.points.get(k)))));
        }
        BitSet kept=simplify(selected,fixed);List<Integer> links=new ArrayList<>();
        for (int k:indexes) links.add(kept.get(0,k-first+prefix).cardinality());
        List<Integer> simplifiedLevels=new ArrayList<>();
        for (int i=kept.nextSetBit(0),j=kept.nextSetBit(i+1);j>=0;i=j,j=kept.nextSetBit(j+1)) simplifiedLevels.add(selectedLevels.get(i));
        Path chosen=new Path("selected","selected",points(selected,kept),links,simplifiedLevels.get(0),simplifiedLevels);
        if (chosen.points.size()<2 || chosen.points.size()>MAX_PATH_POINTS) return unavailable(d,"selected-route capacity exceeded");
        if (!context.available || context.truncated) return limited(d,anchors,chosen,context.truncated?"road context truncated":"road context unavailable");
        Map<String,Integer> shared=new HashMap<>();
        for (Road r:context.roads) for (Geo p:r.points) if (p.node!=null) shared.put(p.node,shared.getOrDefault(p.node,0)+1);
        List<Path> paths=new ArrayList<>();paths.add(chosen);int total=chosen.points.size();
        boolean layered=false;for (int level:simplifiedLevels) if (level!=0) layered=true;
        for (Road road:context.roads) {
            if (nonMotorReason(road.tags)!=null) continue;
            List<XY> raw=new ArrayList<>();Set<XY> critical=Collections.newSetFromMap(new java.util.IdentityHashMap<XY,Boolean>());
            for (Geo p:road.points) {
                XY xy=frame.project(p);raw.add(xy);if (p.node!=null && shared.get(p.node)>1) critical.add(xy);
            }
            List<List<XY>> pieces=clip(raw,RADIUS);
            if (pieces.isEmpty()) continue;
            int layer;
            try { layer=JunctionLayers.level(road.tags.get("layer"),road.tags.get("bridge"),road.tags.get("tunnel")); }
            catch (IllegalArgumentException error) { return limited(d,anchors,chosen,"unsupported road layer metadata"); }
            for (List<XY> piece:pieces) {
                BitSet preserve=new BitSet();for (int i=0;i<piece.size();i++) if (critical.contains(piece.get(i))) preserve.set(i);
                List<Point> ps=points(piece,simplify(piece,preserve));
                boolean distinct=false;
                for (Point p:ps) if (p.x!=ps.get(0).x || p.y!=ps.get(0).y) distinct=true;
                if (!distinct) continue;
                total+=ps.size();
                if (ps.size()>MAX_PATH_POINTS) return limited(d,anchors,chosen,"road vertex capacity exceeded: "+ps.size());
                if (paths.size()>=128 || total>MAX_POINTS) return limited(d,anchors,chosen,"context capacity exceeded: "+paths.size()+" paths / "+total+" points");
                paths.add(new Path("c"+paths.size(),"context",ps,Collections.emptyList(),layer,Collections.emptyList()));
                if (layer!=0) layered=true;
            }
        }
        int pathLimit=layered?MAX_LAYER_PATHS:MAX_PATHS;
        if (paths.size()>pathLimit) compactContext(paths,pathLimit);
        if (paths.size()>pathLimit) return limited(d,anchors,chosen,"map context path capacity exceeded: "+paths.size());
        return paths.size()==1?limited(d,anchors,chosen,"no local motor roads available"):
                new Scene(layered?"layer_context":"map_context",layered?"motorcycle road context with level ordering":"motorcycle road context; intersections do not imply connectivity",d,800,anchors,paths);
    }

    /** Join only degree-two, same-level CONTEXT endpoints. Every visible segment
     * remains exactly present; no road/branch is dropped and no connectivity is claimed.
     * Only used on overflow, preserving ordinary approved scenes byte-for-byte.
     */
    private static void compactContext(List<Path> paths,int limit) {
        boolean changed=true;
        while (changed && paths.size()>limit) {
            changed=false;Map<String,Integer> counts=new HashMap<>();
            for (int i=1;i<paths.size();i++) {
                Path p=paths.get(i);
                for (Point end:Arrays.asList(p.points.get(0),p.points.get(p.points.size()-1))) {
                    String key=p.layer+":"+end.x+":"+end.y;counts.put(key,counts.getOrDefault(key,0)+1);
                }
            }
            search:for (int i=1;i<paths.size();i++) for (int j=i+1;j<paths.size();j++) {
                Path a=paths.get(i),b=paths.get(j);
                if (a.layer!=b.layer || a.points.size()+b.points.size()-1>MAX_PATH_POINTS) continue;
                for (int ai=0;ai<2;ai++) for (int bi=0;bi<2;bi++) {
                    Point aa=a.points.get(ai==0?0:a.points.size()-1),bb=b.points.get(bi==0?0:b.points.size()-1);
                    if (aa.x!=bb.x || aa.y!=bb.y || counts.get(a.layer+":"+aa.x+":"+aa.y)!=2) continue;
                    List<Point> left=new ArrayList<>(a.points),right=new ArrayList<>(b.points);
                    if (ai==0) Collections.reverse(left);if (bi==1) Collections.reverse(right);
                    left.addAll(right.subList(1,right.size()));
                    paths.set(i,new Path(a.id,"context",left,Collections.emptyList(),a.layer,Collections.emptyList()));
                    paths.remove(j);changed=true;break search;
                }
            }
        }
    }

    private Scene limited(Decision d,List<Anchor> anchors,Path selected,String reason) {
        if (selected.points.size()>24) return unavailable(d,reason+"; selected-route limit");
        return new Scene("route_only",reason,d,800,anchors,Collections.singletonList(selected));
    }
    private Scene unavailable(Decision d,String reason) { return new Scene("unavailable",reason,d,800,Collections.emptyList(),Collections.emptyList()); }
    private static Point quantize(XY p) {
        int x=(int)Math.rint(p.x*10),y=(int)Math.rint(p.y*10);
        if ((long)x*x+(long)y*y>800L*800) throw new IllegalArgumentException("Projected geometry outside bounds");
        return new Point(x,y);
    }
    private static List<Point> points(List<XY> input,BitSet kept) {
        List<Point> result=new ArrayList<>();for (int i=kept.nextSetBit(0);i>=0;i=kept.nextSetBit(i+1)) result.add(quantize(input.get(i)));return result;
    }
    private static BitSet simplify(List<XY> p,BitSet fixed) {
        BitSet keep=(BitSet)fixed.clone();keep.set(0);keep.set(p.size()-1);
        ArrayDeque<int[]> stack=new ArrayDeque<>();
        for (int a=keep.nextSetBit(0),b=keep.nextSetBit(a+1);b>=0;a=b,b=keep.nextSetBit(a+1)) stack.push(new int[]{a,b});
        while (!stack.isEmpty()) {
            int[] range=stack.pop();int a=range[0],b=range[1],split=-1;double greatest=1;
            XY aa=p.get(a),bb=p.get(b);double dx=bb.x-aa.x,dy=bb.y-aa.y,len=dx*dx+dy*dy;
            for (int i=a+1;i<b;i++) {
                XY q=p.get(i);double t=len==0?0:Math.max(0,Math.min(1,((q.x-aa.x)*dx+(q.y-aa.y)*dy)/len));
                double error=Math.hypot(q.x-aa.x-t*dx,q.y-aa.y-t*dy);
                if (error>greatest) { greatest=error;split=i; }
            }
            if (split>=0) { keep.set(split);stack.push(new int[]{a,split});stack.push(new int[]{split,b}); }
        }
        return keep;
    }
    private static List<List<XY>> clip(List<XY> points,double radius) {
        List<List<XY>> result=new ArrayList<>();List<XY> current=new ArrayList<>();
        for (int i=1;i<points.size();i++) {
            XY a=points.get(i-1),b=points.get(i);double dx=b.x-a.x,dy=b.y-a.y,len=dx*dx+dy*dy;
            if (len==0) continue;
            double dot=a.x*dx+a.y*dy,disc=dot*dot-len*(a.x*a.x+a.y*a.y-radius*radius);
            double lo=1,hi=0;
            if (disc>0) { double root=Math.sqrt(disc);lo=Math.max(0,(-dot-root)/len);hi=Math.min(1,(-dot+root)/len); }
            if (lo>=hi) { if (!current.isEmpty()) result.add(current);current=new ArrayList<>();continue; }
            XY start=lo==0?a:a.between(b,lo),end=hi==1?b:a.between(b,hi);
            if (!current.isEmpty() && Math.hypot(current.get(current.size()-1).x-start.x,current.get(current.size()-1).y-start.y)>1e-6) {
                result.add(current);current=new ArrayList<>();
            }
            if (current.isEmpty()) current.add(start);current.add(end);
            if (hi<1) { result.add(current);current=new ArrayList<>(); }
        }
        if (!current.isEmpty()) result.add(current);return result;
    }
}
