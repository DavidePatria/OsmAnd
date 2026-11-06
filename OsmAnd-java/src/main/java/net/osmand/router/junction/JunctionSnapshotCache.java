package net.osmand.router.junction;

import net.osmand.router.junction.JunctionGeometry.Scene;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

/** One scene, one worker slot, no geometry/history queue. No Android dependencies. */
public final class JunctionSnapshotCache {
    public enum State { ACTIVE, IDLE, RECALCULATING, PAUSED, OFF_ROUTE, UNAVAILABLE, ARRIVED }
    public static final class Ticket {
        public final long version;
        public final int junction;
        private Ticket(long version,int junction) { this.version=version;this.junction=junction; }
    }
    private String session=UUID.randomUUID().toString();
    private int generation=0,sequence=0,junction=-1;
    private long version=0;
    private Object route;
    private State state=State.UNAVAILABLE;
    private Scene scene;
    private Ticket pending;

    /** Caller supplies a coherent routing observation. Identity is deliberately not equals(). */
    public synchronized void observe(Object routeIdentity,int nextJunction,State status) {
        if (route!=routeIdentity || junction!=nextJunction || state!=status) {
            route=routeIdentity;junction=nextJunction;state=status;scene=null;version++;
            if (++generation>1000000) { session=UUID.randomUUID().toString();generation=1;sequence=0; }
        }
    }
    public synchronized Ticket requestBuild() {
        if (state!=State.ACTIVE || scene!=null || pending!=null || route==null || junction<0) return null;
        pending=new Ticket(version,junction);return pending;
    }
    public synchronized boolean isCurrent(Ticket ticket) {
        return ticket!=null && pending==ticket && version==ticket.version && state==State.ACTIVE;
    }
    public synchronized boolean complete(Ticket ticket,Scene result) {
        if (pending!=ticket) return false;
        boolean accept=isCurrent(ticket);pending=null;
        if (accept) scene=result;
        return accept;
    }
    public synchronized Scene cachedScene() { return scene; }

    /** Fresh copies only. Reading a heartbeat does not reset the supplied fix/progress age. */
    public synchronized Map<String,Object> snapshot(int distanceM,int fixAgeMs,int progressAgeMs,int speedDmps) {
        if (++sequence>1000000) {
            session=UUID.randomUUID().toString();generation=1;sequence=1;version++;
        }
        if (state==State.ACTIVE && scene!=null) {
            Map<String,Object> value=scene.toMap(session,generation,sequence,bound(distanceM,1000000),0,bound(fixAgeMs,60000));
            value.put("progressAgeMs",bound(progressAgeMs,60000));value.put("speedDmps",bound(speedDmps,700));
            return value;
        }
        Map<String,Object> value=new LinkedHashMap<>();
        value.put("version",1);value.put("session",session);value.put("generation",generation);value.put("seq",sequence);
        value.put("state",state==State.ACTIVE?"active":state==State.IDLE?"idle":state==State.RECALCULATING?"recalculating":state==State.ARRIVED?"arrived":"unavailable");
        value.put("geometryMode","unavailable");value.put("reason",state==State.ACTIVE?"geometry pending":state.name().toLowerCase(java.util.Locale.ROOT));
        value.put("distanceM",bound(distanceM,1000000));value.put("roadName","");value.put("maneuver","");value.put("radiusDm",800);
        value.put("sourceAgeMs",0);value.put("fixAgeMs",bound(fixAgeMs,60000));
        value.put("anchors",new ArrayList<>());value.put("paths",new ArrayList<>());
        return value;
    }
    private static int bound(int value,int high) { return Math.max(0,Math.min(value,high)); }
}
