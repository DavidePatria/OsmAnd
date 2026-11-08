package net.osmand.router.junction;

/** Selects a distance target without changing OsmAnd's current direction. */
public final class JunctionProgress {
    private JunctionProgress() { }

    /** Returns -1 after a passed ordinary entry or for invalid route indexes. */
    public static int targetIndex(int current, int entry, int end, boolean roundabout, int pointCount) {
        if (current<0 || entry<0 || entry>=pointCount) return -1;
        if (roundabout && end>entry && end<pointCount && current>entry && current<=end) return end;
        return current>entry?-1:entry;
    }
}
