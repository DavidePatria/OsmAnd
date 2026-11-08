package net.osmand.junction.bridge

import org.junit.Assert.*
import org.junit.Test

class WatchTargetTest {
    @Test fun activityFieldUsesOwnIdentityAndNeverRequestsWatchAppLaunch() {
        assertNotEquals(WatchTarget.appId(false),WatchTarget.appId(true))
        assertEquals("5ee36e99bc8944a2b026040cd9e77f35",WatchTarget.appId(true))
        assertTrue(WatchTarget.shouldPrompt(false,true))
        assertFalse(WatchTarget.shouldPrompt(true,true))
        assertFalse(WatchTarget.shouldPrompt(false,false))
    }
}
