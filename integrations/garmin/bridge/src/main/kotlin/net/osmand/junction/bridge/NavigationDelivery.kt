package net.osmand.junction.bridge

/** One source read/send slot. Old callbacks cannot release a later request. */
class NavigationDelivery {
    data class Ticket internal constructor(val epoch: String, val id: Int, val startedAt: Long, val connection: Long)
    private var connection = 0L
    private var slot: Ticket? = null
    private var lastEpoch = ""
    private var lastId = 0
    private val retired = ArrayDeque<String>()

    @Synchronized fun connectionChanged() { connection++; lastEpoch = ""; lastId = 0; retired.clear() }
    @Synchronized fun begin(value: Any?, now: Long): Ticket? {
        if (slot != null || now < 0) return null
        val request = value as? Map<*, *> ?: return null
        if (request["kind"] != "junction_request" || request["version"] != 1) return null
        val epoch = request["epoch"] as? String ?: return null
        val id = request["requestId"] as? Int ?: return null
        if (epoch.length !in 1..64 || id !in 1..1_000_000 || epoch in retired) return null
        val ack=listOf("displayedSession","displayedGeneration","displayedSeq","displayedState")
        if(ack.any { request.containsKey(it) }) {
            val session=request["displayedSession"] as? String ?: return null
            val generation=request["displayedGeneration"] as? Int ?: return null
            val seq=request["displayedSeq"] as? Int ?: return null
            if(session.length !in 1..64 || generation !in 0..1_000_000 || seq !in 0..1_000_000 ||
                request["displayedState"] !in listOf("active","idle","recalculating","unavailable","stale_source","stale_transport"))return null
        }
        if (epoch == lastEpoch && id <= lastId) return null
        if (epoch != lastEpoch) {
            if (lastEpoch.isNotEmpty()) { retired.addLast(lastEpoch); if (retired.size > 4) retired.removeFirst() }
            lastEpoch = epoch; lastId = 0
        }
        lastId = id
        return Ticket(epoch, id, now, connection).also { slot = it }
    }
    @Synchronized fun response(ticket: Ticket, scene: Map<String, Any>, now: Long): Map<String, Any>? {
        if (slot !== ticket || ticket.connection != connection || now < ticket.startedAt || now-ticket.startedAt >= 3000) return null
        return mapOf("version" to 1, "kind" to "junction_snapshot", "epoch" to ticket.epoch, "requestId" to ticket.id, "scene" to scene)
    }
    @Synchronized fun finish(ticket: Ticket) { if (slot === ticket) slot = null }
    @Synchronized fun unavailable(ticket: Ticket, reason: String, now: Long): Map<String, Any>? {
        if (response(ticket,emptyMap(),now)==null) return null
        return mapOf("version" to 1,"kind" to "junction_unavailable","epoch" to ticket.epoch,"requestId" to ticket.id,"reason" to reason.take(80))
    }
}
