package net.osmand.router.junction;

import net.osmand.router.junction.JunctionGeometry.*;
import org.junit.Test;
import java.util.*;
import static org.junit.Assert.*;

public class JunctionCompilerTest {
    private static Geo geo(double east,double north) { return new Geo(Math.toDegrees(north/6371000),Math.toDegrees(east/6371000),east+":"+north); }
    private static Map<String,String> tags(String... pairs) {
        Map<String,String> result=new HashMap<>();for (int i=0;i<pairs.length;i+=2) result.put(pairs[i],pairs[i+1]);return result;
    }
    private static Road road(String id,Map<String,String> tags,Geo... points) { return new Road(id,Arrays.asList(points),tags); }
    private static Route route() {
        return new Route(Arrays.asList(geo(0,-100),geo(0,0),geo(40,0),geo(40,100)),
                Arrays.asList(new Decision(1,"TR","Test",0),new Decision(2,"TL","Next",0)));
    }
    private static Context context(Road... roads) { return new Context(Arrays.asList(roads),true,false); }
    private static Scene compile(Context context) { return new JunctionCompiler().compile(route(),0,context); }

    @Test public void approachUpAndSeparateCloseDecisions() {
        Scene scene=compile(context(road("r",tags("highway","residential"),geo(-100,0),geo(0,0),geo(100,0))));
        assertEquals("map_context",scene.mode);assertEquals(2,scene.anchors.size());
        assertEquals(1,scene.anchors.get(0).routeIndex);assertEquals(2,scene.anchors.get(1).routeIndex);
        assertEquals(400,scene.anchors.get(1).point.x);assertEquals(0,scene.anchors.get(1).point.y);
        assertEquals(-750,scene.paths.get(0).points.get(0).y);
        for (int i=0;i<2;i++) {
            Point expected=scene.anchors.get(i).point,actual=scene.paths.get(0).points.get(scene.paths.get(0).anchorIndexes.get(i));
            assertEquals(expected.x,actual.x);assertEquals(expected.y,actual.y);
        }
    }
    @Test public void sharedMapVerticesSurviveBelowTolerance() {
        Scene scene=compile(context(road("a",tags(),geo(-30,0),geo(0,.01),geo(30,0)),road("b",tags(),geo(0,.01),geo(0,30))));
        assertEquals(3,scene.paths.get(1).points.size());
        assertTrue(scene.paths.get(1).anchorIndexes.isEmpty());
    }
    @Test public void circleClipKeepsOutsideToOutsideCrossing() {
        Scene scene=compile(context(road("r",tags(),geo(-100,10),geo(100,10))));
        assertEquals(2,scene.paths.size());assertTrue(scene.paths.get(1).points.get(0).x<0);
        assertTrue(scene.paths.get(1).points.get(1).x>0);
    }
    @Test public void clippingDoesNotJoinOutsideExcursion() {
        Scene scene=compile(context(road("r",tags(),geo(0,0),geo(100,0),geo(100,100),geo(0,0))));
        assertEquals(3,scene.paths.size());
    }
    @Test public void motorAccessAndUnpavedTracks() {
        assertNotNull(JunctionCompiler.nonMotorReason(tags("highway","cycleway")));
        assertNull(JunctionCompiler.nonMotorReason(tags("highway","cycleway","motor_vehicle","no","motorcycle","yes")));
        assertNotNull(JunctionCompiler.nonMotorReason(tags("highway","residential","motorcycle","no","access","yes")));
        assertNull(JunctionCompiler.nonMotorReason(tags("highway","track","surface","gravel")));
        assertNull(JunctionCompiler.nonMotorReason(tags("highway","service","access","private")));
        Scene scene=compile(context(road("foot",tags("highway","footway"),geo(0,0),geo(30,30)),road("motor",tags("highway","service"),geo(0,0),geo(-30,30))));
        assertEquals(2,scene.paths.size());assertEquals("selected",scene.paths.get(0).role);
    }
    @Test public void overflowIsExplicitAndBridgesRetainRoadContext() {
        List<Road> roads=new ArrayList<>();for (int i=0;i<33;i++) roads.add(road("r"+i,tags(),geo(0,0),geo(20,i)));
        Scene scene=compile(new Context(roads,true,false));assertEquals("route_only",scene.mode);assertTrue(scene.reason.contains("capacity"));
        scene=compile(context(road("bridge",tags("bridge","yes"),geo(-20,20),geo(20,20))));
        assertEquals("layer_context",scene.mode);assertEquals(2,scene.paths.size());assertEquals(1,scene.paths.get(1).layer);
        assertEquals("route_only",compile(Context.unavailable()).mode);
    }
    @Test public void buildingPassageDoesNotChangeAnOrdinaryRoadDiagram() {
        Scene a=compile(context(road("r",tags("highway","residential"),geo(-50,0),geo(50,0))));
        Scene b=compile(context(road("r",tags("highway","residential","tunnel","building_passage"),geo(-50,0),geo(50,0))));
        assertEquals(a.toMap("t",1,1,120,0,0),b.toMap("t",1,1,120,0,0));
    }
    @Test public void layerChangesSurviveSelectedRouteSimplificationAndWindowing() {
        List<Geo> points=Arrays.asList(geo(0,-100),geo(0,-20),new Geo(0,0,null,1),geo(0,20),geo(0,100));
        Route route=new Route(points,Collections.singletonList(new Decision(2,"C","",0)));
        Context context=context(road("r",tags(),geo(-50,10),geo(50,10)));
        Scene scene=new JunctionCompiler().compile(route,0,context);
        assertEquals("layer_context",scene.mode);assertEquals(Arrays.asList(0,1,0),scene.paths.get(0).segmentLayers);
        assertEquals(4,scene.paths.get(0).points.size());
        Route window=JunctionWindow.copy(points.size(),1,0,points::get,route.decisions::get);
        assertEquals(scene.toMap("t",1,1,120,0,0),new JunctionCompiler().compile(window,0,context).toMap("t",1,1,120,0,0));
    }
    @Test public void levelTagsAreDrawingOrderAndExplicitValuesTakePrecedence() {
        assertEquals(0,JunctionLayers.level(null,null,"building_passage"));
        assertEquals(1,JunctionLayers.level(null,"yes",null));assertEquals(-1,JunctionLayers.level(null,null,"yes"));
        assertEquals(2,JunctionLayers.level("2","yes",null));assertEquals(0,JunctionLayers.level("0","yes",null));
        try { JunctionLayers.level("not-a-level",null,null);fail("bad layer"); } catch (IllegalArgumentException expected) { }
    }
    @Test public void onlyLayeredModeEmitsTheRequiredDrawingMetadata() {
        Map<String,Object> layered=compile(context(road("r",tags("bridge","yes"),geo(-30,20),geo(30,20)))).toMap("t",1,1,120,0,0);
        List<?> paths=(List<?>)layered.get("paths");assertTrue(((Map<?,?>)paths.get(0)).containsKey("segmentLayers"));
        assertEquals(1,((Map<?,?>)paths.get(1)).get("layer"));
        Map<String,Object> ordinary=compile(context(road("r",tags(),geo(-30,20),geo(30,20)))).toMap("t",1,1,120,0,0);
        assertFalse(((Map<?,?>)((List<?>)ordinary.get("paths")).get(0)).containsKey("layer"));
    }
    @Test public void overflowCompactionPreservesEveryContextSegment() {
        List<Road> roads=new ArrayList<>();Set<String> expected=new HashSet<>();
        for (int i=0;i<16;i++) {
            int y=-30+i*3;
            roads.add(road("a"+i,tags(),geo(-20,y),geo(0,y)));
            roads.add(road("b"+i,tags(),geo(0,y),geo(20,y)));
            expected.add(edge(new Point(-200,y*10),new Point(0,y*10)));
            expected.add(edge(new Point(0,y*10),new Point(200,y*10)));
        }
        Scene scene=compile(new Context(roads,true,false));assertEquals("map_context",scene.mode);assertEquals(32,scene.paths.size());
        Set<String> actual=new HashSet<>();
        for (Path p:scene.paths) if (p.role.equals("context")) for (int i=1;i<p.points.size();i++) actual.add(edge(p.points.get(i-1),p.points.get(i)));
        assertEquals(expected,actual);
    }
    private static String edge(Point a,Point b) {
        String aa=a.x+":"+a.y,bb=b.x+":"+b.y;return aa.compareTo(bb)<0?aa+"/"+bb:bb+"/"+aa;
    }
    @Test public void rawAndOutputCollectionsAreOwned() {
        List<Geo> points=new ArrayList<>(route().points);Route route=new Route(points,route().decisions);points.clear();
        Scene scene=new JunctionCompiler().compile(route,0,Context.unavailable());assertFalse(scene.paths.isEmpty());
        Map<String,Object> wire=scene.toMap("test",1,1,100,0,0);((List<?>)wire.get("paths")).clear();
        assertFalse(scene.paths.isEmpty());
        try { scene.paths.clear();fail("mutable scene"); } catch (UnsupportedOperationException expected) { }
    }
    @Test public void equalCoordinatesDoNotMergeOriginalIndexes() {
        Route input=new Route(Arrays.asList(geo(0,-50),geo(0,0),geo(0,0),geo(0,50)),Arrays.asList(new Decision(1,"C","",0),new Decision(2,"C","",0)));
        Scene scene=new JunctionCompiler().compile(input,0,Context.unavailable());
        assertEquals(2,scene.anchors.size());assertEquals(1,scene.anchors.get(0).routeIndex);assertEquals(2,scene.anchors.get(1).routeIndex);
    }
    @Test public void deterministicAndRoundaboutMetadataRetained() {
        Route input=new Route(route().points,Collections.singletonList(new Decision(1,"RNDB2","",2)));
        JunctionCompiler engine=new JunctionCompiler();Scene a=engine.compile(input,0,Context.unavailable()),b=engine.compile(input,0,Context.unavailable());
        assertEquals(2,a.roundaboutExit);assertEquals(a.toMap("t",1,1,1,0,0),b.toMap("t",1,1,1,0,0));
    }
    @Test public void longRouteWindowRetainsOriginalIndexes() {
        Route window=new Route(route().points,Arrays.asList(new Decision(100001,"TR","",0),new Decision(100002,"TL","",0)),100000);
        Scene scene=new JunctionCompiler().compile(window,0,Context.unavailable());
        assertEquals(100001,scene.anchors.get(0).routeIndex);assertEquals(100002,scene.anchors.get(1).routeIndex);
        assertEquals(400,scene.anchors.get(1).point.x);
    }
    @Test public void millionPointSourceIsReadLocallyAndMatchesFullFrame() {
        final int[] reads={0};List<Decision> decisions=Arrays.asList(new Decision(500000,"C","",0),new Decision(500040,"C","",0));
        Route window=JunctionWindow.copy(1000000,2,0,i->{ reads[0]++;return geo(0,i-500000); },decisions::get);
        assertTrue(reads[0]<1000);assertTrue(window.points.size()<300);
        Scene scene=new JunctionCompiler().compile(window,0,Context.unavailable());
        assertEquals(500000,scene.anchors.get(0).routeIndex);assertEquals(500040,scene.anchors.get(1).routeIndex);
        Route full=route();Route local=JunctionWindow.copy(full.points.size(),full.decisions.size(),0,full.points::get,full.decisions::get);
        assertEquals(new JunctionCompiler().compile(full,0,Context.unavailable()).toMap("t",1,1,1,0,0),
                new JunctionCompiler().compile(local,0,Context.unavailable()).toMap("t",1,1,1,0,0));
    }
    @Test public void datelineDistanceUsesShortArcAndBadInputsRejected() {
        assertTrue(JunctionCompiler.distance(new Geo(0,179.999),new Geo(0,-179.999))<225);
        try { new Geo(Double.NaN,0);fail("NaN"); } catch (IllegalArgumentException expected) { }
        try { new Route(route().points,Collections.singletonList(new Decision(99,"C","",0)));fail("index"); } catch (IllegalArgumentException expected) { }
    }
    @Test public void destinationFlagRequiresTheActualVisibleRouteEnd() {
        List<Geo> pts=Arrays.asList(geo(0,-100),geo(0,0),geo(30,10));
        List<Decision> decisions=Collections.singletonList(new Decision(1,"TR","",0));
        JunctionCompiler compiler=new JunctionCompiler();
        Scene full=compiler.compile(new Route(pts,decisions),0,Context.unavailable());
        assertNotNull(full.destination);
        assertEquals(full.paths.get(0).points.get(full.paths.get(0).points.size()-1).pair(),full.destination.pair());
        assertNull(compiler.compile(new Route(pts,decisions,0,100),0,Context.unavailable()).destination);
        assertEquals(full.toMap("s",1,1,2,0,0),compiler.compile(JunctionWindow.copy(pts.size(),1,0,pts::get,decisions::get),0,Context.unavailable()).toMap("s",1,1,2,0,0));
    }
}
