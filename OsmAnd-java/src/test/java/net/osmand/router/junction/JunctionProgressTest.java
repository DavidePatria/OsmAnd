package net.osmand.router.junction;

import org.junit.Test;
import static org.junit.Assert.assertEquals;

public class JunctionProgressTest {
    @Test public void roundaboutTargetsEntryThenNativeExitWithoutAdvancingDirection() {
        assertEquals(18,JunctionProgress.targetIndex(10,18,46,true,80));
        assertEquals(18,JunctionProgress.targetIndex(18,18,46,true,80));
        assertEquals(46,JunctionProgress.targetIndex(19,18,46,true,80));
        assertEquals(46,JunctionProgress.targetIndex(46,18,46,true,80));
        assertEquals(-1,JunctionProgress.targetIndex(47,18,46,true,80));
    }
    @Test public void ordinaryAndInvalidEndsNeverInventAnExit() {
        assertEquals(-1,JunctionProgress.targetIndex(19,18,46,false,80));
        assertEquals(-1,JunctionProgress.targetIndex(19,18,18,true,80));
        assertEquals(-1,JunctionProgress.targetIndex(19,18,80,true,80));
        assertEquals(-1,JunctionProgress.targetIndex(1,80,90,true,80));
    }
}
