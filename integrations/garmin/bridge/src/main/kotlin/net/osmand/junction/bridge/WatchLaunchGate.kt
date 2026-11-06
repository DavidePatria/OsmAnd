package net.osmand.junction.bridge

/** Explicit starts arm one attempt. Device reconnects never create prompt loops. */
class WatchLaunchGate {
    private var armed=false
    private var lastAttempt:Long?=null
    fun request() { armed=true }
    fun begin(now:Long,connected:Boolean):Boolean {
        if(!armed || !connected || now<0)return false
        val last=lastAttempt
        if(last!=null && (now<last || now-last<30_000))return false
        armed=false;lastAttempt=now;return true
    }
}
