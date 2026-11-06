package app.aaps.implementation.maintenance

import kotlin.coroutines.cancellation.CancellationException
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.coroutines.flow.first
import app.aaps.core.interfaces.sync.NsClient
import app.aaps.core.data.model.GV
import app.aaps.core.data.time.T
import app.aaps.core.interfaces.alerts.LocalAlertUtils
import app.aaps.core.interfaces.db.PersistenceLayer
import app.aaps.core.interfaces.logging.AAPSLogger
import app.aaps.core.interfaces.logging.LTag
import app.aaps.core.interfaces.maintenance.Maintenance
import app.aaps.core.interfaces.utils.DateUtil
import app.aaps.core.keys.LongNonKey
import app.aaps.core.keys.interfaces.Preferences
import app.aaps.implementation.maintenance.PeriodicMaintenance.Companion.INTERVAL
import app.aaps.implementation.maintenance.PeriodicMaintenance.Companion.MAX_CUTOFF_STEP
import dev.zacsweers.metro.AppScope
import dev.zacsweers.metro.Inject
import dev.zacsweers.metro.SingleIn
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlin.time.Duration.Companion.days
import kotlin.time.Duration.Companion.minutes

/**
 * The housekeeping that has to happen every few minutes whatever the app is running on.
 *
 * All of this lived inside `KeepAliveWorker`, which is an Android WorkManager worker, so it was the
 * only thing that ran it. The bodies were already in `commonMain` - `LocalAlertUtils`,
 * `PersistenceLayer`, `Maintenance` are all shared interfaces - so the code compiled for iOS and
 * desktop and was entered on neither. Shared code with a single platform-specific caller looks
 * finished and is not; that is the shape this class exists to remove.
 *
 * What it cost, concretely: [BooleanKey.AlertMissedBgReading] is drawn and searchable on every
 * platform, and off Android it did nothing, so a follower whose CGM stopped was never told. The
 * local database also grew without bound, because nothing trimmed it.
 *
 * ## What is here and what is not
 *
 * Only the platform-neutral work. `KeepAliveWorker` keeps the rest, and it belongs there: the
 * WorkManager self-rescheduling, the worker-database telemetry, and the pump and APS checks, which
 * are gated on `config.APS` and so are no-ops on the two shells that hardcode it false.
 *
 * ## Who drives it
 *
 * The trigger stays per platform, because that part genuinely differs: Android has WorkManager and a
 * wake lock, and the other two do not. Android calls [runOnce] from `KeepAliveWorker` on its existing
 * schedule; iOS and desktop call [start] and get a coroutine ticker. What must NOT differ again is
 * the work itself, which is why it is one method rather than three call sites.
 */
@SingleIn(AppScope::class)
@Inject
class PeriodicMaintenance(
    private val aapsLogger: AAPSLogger,
    private val localAlertUtils: LocalAlertUtils,
    private val persistenceLayer: PersistenceLayer,
    private val maintenance: Maintenance,
    private val preferences: Preferences,
    private val dateUtil: DateUtil,
    private val nsClient: NsClient
) {

    /**
     * One pass. Safe to call from any platform and at any interval - every step decides for itself
     * whether it is due, so calling more often than needed does no extra work.
     */
    suspend fun runOnce() {
        localAlertUtils.shortenSnoozeInterval()
        localAlertUtils.checkStaleBGAlert()
        maintenance.deleteLogs(KEEP_LOG_FILES)
        cleanupDatabase()
    }

    /**
     * Runs [runOnce] every [INTERVAL] on [scope], for the platforms with no WorkManager.
     *
     * Deliberately not idempotent-guarded here: the callers are shell startup paths that run once.
     * A failure is logged and the loop continues - one bad pass must not stop the missed-reading
     * alarm for the rest of the session.
     */
    fun start(scope: CoroutineScope) {
        scope.launch {
            var lastPassAt = 0L
            while (isActive) {
                try {
                    // b-hubit fork (missed-readings test): after a start, or when iOS kept the app
                    // frozen past the interval, the local database is as old as the freeze. Judging it
                    // straight away raised "missed BG readings" for readings that were in Nightscout
                    // all along and arrived a few seconds later. Wait for the data first.
                    val now = dateUtil.now()
                    if (lastPassAt == 0L || now - lastPassAt > (INTERVAL + RESUME_SLACK).inWholeMilliseconds)
                        awaitCaughtUp(since = now - RACE_MARGIN.inWholeMilliseconds)
                    runOnce()
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    aapsLogger.error(LTag.CORE, "Periodic maintenance pass failed", e)
                }
                lastPassAt = dateUtil.now()
                delay(INTERVAL)
            }
        }
        // Take the missed-readings alarm down the moment a fresh reading is stored, instead of at the
        // next pass up to five minutes later - by then the user has already had to silence it.
        scope.launch {
            persistenceLayer.observeChanges(GV::class).collect {
                try {
                    localAlertUtils.dismissStaleBGAlertIfFresh()
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    aapsLogger.error(LTag.CORE, "Missed-readings dismiss failed", e)
                }
            }
        }
    }

    /**
     * Waits until a Nightscout load round has brought the local data up to date after [since], or
     * [CATCH_UP_WAIT] has passed. The bound is what keeps a real outage alarming: with no network, or
     * a source that is not Nightscout, the check runs after the wait and judges what is there.
     */
    private suspend fun awaitCaughtUp(since: Long) {
        var from = since
        while (true) {
            val startedAt = dateUtil.now()
            val caughtUp = withTimeoutOrNull(CATCH_UP_WAIT) { nsClient.lastCatchUpAt.first { it >= from } }
            if (caughtUp != null) {
                aapsLogger.debug(LTag.CORE, "Nightscout caught up, checking missed readings")
                return
            }
            // The timeout can run out while iOS has the app frozen, and then it fires the moment the
            // app is back - before anything could be fetched. A wait that took far longer than it was
            // given was such a freeze, so it starts over from now instead of judging stale data.
            val now = dateUtil.now()
            if (now - startedAt > (CATCH_UP_WAIT + RESUME_SLACK).inWholeMilliseconds) {
                aapsLogger.debug(LTag.CORE, "Catch-up wait was frozen, waiting again")
                from = now - RACE_MARGIN.inWholeMilliseconds
                continue
            }
            aapsLogger.debug(LTag.CORE, "No Nightscout catch-up within $CATCH_UP_WAIT, checking missed readings anyway")
            return
        }
    }

    /**
     * Keep six months of history, trimmed once a day.
     *
     * Also runs when the last run is in the future: the clock went back, and without this the
     * cleanup would stop until real time caught up with it.
     */
    private suspend fun cleanupDatabase() {
        val now = dateUtil.now()
        val lastRun = preferences.get(LongNonKey.LastCleanupRun)
        if (lastRun < now - T.days(1).msecs() || lastRun > now) {
            val cutoff = nextCutoff(now, lastRun)
            val result = persistenceLayer.cleanupDatabase(cutoff, deleteTrackedChanges = false)
            aapsLogger.debug(LTag.CORE, "Cleanup result: $result")
            preferences.put(LongNonKey.LastCleanupRun, now)
            preferences.put(LongNonKey.LastCleanupCutoff, cutoff)
        }
    }

    /**
     * The time before which records are deleted in this pass.
     *
     * Normally `now - KEEP_DAYS`. But the cutoff may move forward by at most [MAX_CUTOFF_STEP] per
     * pass. The pass runs about once a day, so in normal use the cutoff moves about one day and the
     * limit is never hit. If the phone clock jumps forward by months, `now - KEEP_DAYS` would be after
     * all the real data and delete it all, including the boluses that still count for IOB. With the
     * limit only the oldest days go, and the recent data is safe until the clock is fixed (#5210).
     *
     * After a long pause the old data is removed over the next days instead of at once. That only
     * keeps a little more data for a while.
     */
    private fun nextCutoff(now: Long, lastRun: Long): Long {
        val wanted = now - T.days(KEEP_DAYS).msecs()
        // Before LastCleanupCutoff existed, the last cutoff was lastRun - KEEP_DAYS.
        // With neither (first run on a new install) there is no history to protect.
        val lastCutoff = preferences.get(LongNonKey.LastCleanupCutoff).takeIf { it != 0L }
            ?: lastRun.takeIf { it != 0L }?.let { it - T.days(KEEP_DAYS).msecs() }
            ?: return wanted
        val limit = lastCutoff + MAX_CUTOFF_STEP.inWholeMilliseconds
        if (wanted > limit) {
            aapsLogger.warn(LTag.CORE, "Cleanup cutoff limited to ${dateUtil.dateAndTimeString(limit)}, clock may have jumped forward. Wanted ${dateUtil.dateAndTimeString(wanted)}")
            return limit
        }
        return wanted
    }

    companion object {

        /** Matches the interval `KeepAliveWorker` is scheduled at on Android. */
        val INTERVAL = 5.minutes
        const val KEEP_DAYS = 6L * 31

        /** One day per daily pass, plus room for a pass that runs late. */
        val MAX_CUTOFF_STEP = 2.days
        const val KEEP_LOG_FILES = 30

        /** A pass later than [INTERVAL] by more than this means the app was not running in between. */
        val RESUME_SLACK = 2.minutes

        /** Longest wait for fresh data after a start or a resume before checking anyway. */
        val CATCH_UP_WAIT = 3.minutes

        /** A catch-up that finished just before the pass woke up still counts. */
        val RACE_MARGIN = 1.minutes
    }
}
