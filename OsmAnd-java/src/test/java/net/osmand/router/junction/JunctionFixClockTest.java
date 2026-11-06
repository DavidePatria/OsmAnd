package net.osmand.router.junction;

import org.junit.Test;
import static org.junit.Assert.*;

public class JunctionFixClockTest {
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
