package net.osmand.router.junction;

import net.osmand.router.junction.JunctionGeometry.*;
import net.osmand.router.junction.JunctionSnapshotCache.*;
import org.junit.Test;
import java.util.*;
import static org.junit.Assert.*;

public class JunctionSnapshotCacheTest {
    private Scene scene() {
        Route input=new Route(Arrays.asList(new Geo(-.001,0),new Geo(0,0),new Geo(.001,0)),Collections.singletonList(new Decision(1,"C","",0)));
        return new JunctionCompiler().compile(input,0,Context.unavailable());
    }
    @Test public void progressDoesNotRebuildFixedGeometry() {
        JunctionSnapshotCache cache=new JunctionSnapshotCache();Object route=new Object();cache.observe(route,5,State.ACTIVE);
        Ticket ticket=cache.requestBuild();assertNotNull(ticket);Scene geometry=scene();assertTrue(cache.complete(ticket,geometry));
        cache.observe(route,5,State.ACTIVE);assertNull(cache.requestBuild());assertSame(geometry,cache.cachedScene());
        Map<String,Object> first=cache.snapshot(120,800,800,100),second=cache.snapshot(110,1800,1800,100);
        assertEquals(first.get("paths"),second.get("paths"));assertEquals(first.get("generation"),second.get("generation"));
        assertEquals(1800,second.get("fixAgeMs"));assertTrue((Integer)second.get("seq")>(Integer)first.get("seq"));
    }
    @Test public void oldBuildCannotRestoreGeometryAndQueueIsBounded() {
        JunctionSnapshotCache cache=new JunctionSnapshotCache();Object route=new Object();cache.observe(route,5,State.ACTIVE);
        Ticket old=cache.requestBuild();cache.observe(new Object(),8,State.ACTIVE);
        assertFalse(cache.isCurrent(old));assertNull(cache.requestBuild());
        assertFalse(cache.complete(old,scene()));assertNull(cache.cachedScene());
        Ticket next=cache.requestBuild();assertNotNull(next);assertFalse(cache.complete(old,scene()));
        assertTrue(cache.isCurrent(next));assertTrue(cache.complete(next,scene()));
    }
    @Test public void pauseCancelOffRouteAndRerouteInvalidateImmediately() {
        for (State state:new State[]{State.PAUSED,State.IDLE,State.RECALCULATING,State.OFF_ROUTE,State.UNAVAILABLE}) {
            JunctionSnapshotCache cache=new JunctionSnapshotCache();Object route=new Object();cache.observe(route,1,State.ACTIVE);
            cache.complete(cache.requestBuild(),scene());Map<String,Object> active=cache.snapshot(100,0,0,100);
            cache.observe(route,1,state);Map<String,Object> stopped=cache.snapshot(100,0,0,100);
            assertEquals("unavailable",stopped.get("geometryMode"));assertTrue(((List<?>)stopped.get("paths")).isEmpty());
            assertTrue((Integer)stopped.get("generation")>(Integer)active.get("generation"));assertNull(cache.requestBuild());
        }
    }
    @Test public void advancingJunctionAndMutableWireCopyCannotReuseOldScene() {
        JunctionSnapshotCache cache=new JunctionSnapshotCache();Object route=new Object();cache.observe(route,1,State.ACTIVE);
        cache.complete(cache.requestBuild(),scene());Map<String,Object> wire=cache.snapshot(100,0,0,0);
        ((List<?>)wire.get("paths")).clear();assertFalse(((List<?>)cache.snapshot(99,0,0,0).get("paths")).isEmpty());
        cache.observe(route,2,State.ACTIVE);assertNull(cache.cachedScene());assertNotNull(cache.requestBuild());
    }
    @Test public void arrivalIsExplicitAndClearsForCancelOrANewRoute() {
        JunctionSnapshotCache cache=new JunctionSnapshotCache();Object route=new Object();
        cache.observe(route,-1,State.ARRIVED);
        assertEquals("arrived",cache.snapshot(0,60000,60000,0).get("state"));assertNull(cache.requestBuild());
        cache.observe(route,-1,State.IDLE);assertEquals("idle",cache.snapshot(0,0,0,0).get("state"));
        cache.observe(new Object(),1,State.ACTIVE);assertEquals("active",cache.snapshot(10,0,0,0).get("state"));
    }
}
