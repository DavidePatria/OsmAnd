package net.osmand.router.junction;

/** Anchor a fix's initial UTC age to elapsed time; polling never rejuvenates it. */
public final class JunctionFixClock {
    private long fixTime=Long.MIN_VALUE,observedAt;
    private int initialAge=60000;
    public int age(long timestamp,long wallNow,long elapsedNow) {
        if (timestamp<=0 || timestamp>wallNow || elapsedNow<0 || timestamp<fixTime) return 60000;
        if (timestamp!=fixTime) {
            fixTime=timestamp;observedAt=elapsedNow;initialAge=(int)Math.min(60000,wallNow-timestamp);
        }
        if (elapsedNow<observedAt) return 60000;
        return (int)Math.min(60000,initialAge+elapsedNow-observedAt);
    }
}
