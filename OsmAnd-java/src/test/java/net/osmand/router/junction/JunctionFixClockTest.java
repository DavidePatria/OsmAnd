package net.osmand.router.junction;

import org.junit.Test;
import static org.junit.Assert.*;

public class JunctionFixClockTest {
    @Test public void speedRequiresMatchingValidProjectionAndFix() {
        assertEquals(138, JunctionFixClock.matchedSpeedDmps(1000,1000,true,13.8f));
        assertEquals(0, JunctionFixClock.matchedSpeedDmps(1000,999,true,13.8f));
        assertEquals(0, JunctionFixClock.matchedSpeedDmps(0,0,true,13.8f));
        assertEquals(0, JunctionFixClock.matchedSpeedDmps(1000,1000,false,13.8f));
        assertEquals(0, JunctionFixClock.matchedSpeedDmps(1000,1000,true,Float.NaN));
        assertEquals(0, JunctionFixClock.matchedSpeedDmps(1000,1000,true,-1));
        assertEquals(0, JunctionFixClock.matchedSpeedDmps(1000,1000,true,70.1f));
    }
    @Test public void pollingAndWallClockJumpCannotRefreshOldFix() {
        JunctionFixClock clock=new JunctionFixClock();
        assertEquals(100,clock.age(10000,10100,500));
        assertEquals(2100,clock.age(10000,90000,2500));
        assertEquals(60000,clock.age(10000,99000,99999));
    }
    @Test public void futureOutOfOrderAndElapsedRollbackAreOld() {
        JunctionFixClock clock=new JunctionFixClock();
        assertEquals(60000,clock.age(11000,10000,100));
        assertEquals(0,clock.age(10000,10000,100));
        assertEquals(60000,clock.age(9999,10000,200));
        assertEquals(60000,clock.age(10000,10000,50));
        assertEquals(10,clock.age(11000,11010,300));
    }
}
