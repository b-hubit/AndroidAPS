package app.aaps.core.utils

import kotlinx.datetime.TimeZone
import kotlin.concurrent.Volatile
import kotlin.time.TimeSource

/**
 * The system time zone, read again at most every [MAX_AGE_MS] instead of on every call.
 *
 * b-hubit fork. On iOS, `TimeZone.currentSystemDefault()` resets Foundation's cached
 * system zone, then reads the zone's file from disk and parses it - on every call, with no cache in
 * kotlinx-datetime (0.8.0, `core/darwin/src/internal/TimeZoneNative.kt` and `TzdbOnFilesystem.rulesForId`).
 * The IOB calculation asks for it once for every basal rate it looks up, tens of thousands of times a
 * run, which made one calculation take over half a minute on a phone. On Android it is a cheap lookup.
 *
 * A change of the phone's time zone is seen within [MAX_AGE_MS]. The calculation restarts from scratch on
 * a zone change anyway (`EventTimeZoneChanged`), and that event comes later than this refresh.
 */
object SystemTimeZone {

    private const val MAX_AGE_MS = 10_000L

    private class Entry(val zone: TimeZone, val readAt: TimeSource.Monotonic.ValueTimeMark)

    // One immutable entry swapped as a whole, so a reader on another thread never sees half of it.
    @Volatile private var entry: Entry? = null

    fun current(): TimeZone {
        val cached = entry
        if (cached != null && cached.readAt.elapsedNow().inWholeMilliseconds < MAX_AGE_MS) return cached.zone
        val zone = TimeZone.currentSystemDefault()
        entry = Entry(zone, TimeSource.Monotonic.markNow())
        return zone
    }
}
