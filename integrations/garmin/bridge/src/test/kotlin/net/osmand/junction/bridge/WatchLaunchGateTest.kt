package net.osmand.junction.bridge
import org.junit.Assert.*
import org.junit.Test

class WatchLaunchGateTest {
    @Test fun waitsForConnectionAndNeverPromptsForReconnectsAlone() {
        val gate=WatchLaunchGate();assertFalse(gate.begin(0,true));gate.request()
        assertFalse(gate.begin(0,false));assertTrue(gate.begin(100,true))
        assertFalse(gate.begin(200,true));assertFalse(gate.begin(40000,true))
    }
    @Test fun explicitStartsAreRateLimitedAndClockRollbackCannotBypassIt() {
        val gate=WatchLaunchGate();gate.request();assertTrue(gate.begin(100,true))
        gate.request();assertFalse(gate.begin(30100,false));assertFalse(gate.begin(99,true))
        assertFalse(gate.begin(30099,true));assertTrue(gate.begin(30100,true))
    }
}
