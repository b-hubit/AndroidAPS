package app.aaps.implementation.utils

import app.aaps.core.data.iob.InMemoryGlucoseValue
import app.aaps.core.data.model.GV
import app.aaps.core.data.model.TrendArrow
import app.aaps.core.interfaces.aps.AutosensDataStore
import app.aaps.core.interfaces.resources.TextResolver
import app.aaps.core.interfaces.utils.TrendCalculator
import app.aaps.core.ui.extensions.directionToDescription
import dev.zacsweers.metro.AppScope
import dev.zacsweers.metro.ContributesBinding
import dev.zacsweers.metro.Inject
import dev.zacsweers.metro.SingleIn

@ContributesBinding(AppScope::class)
@SingleIn(AppScope::class)
@Inject
class TrendCalculatorImpl(
    private val rh: TextResolver
) : TrendCalculator {

    override fun getTrendArrow(autosensDataStore: AutosensDataStore): TrendArrow? {
        val data = autosensDataStore.getBucketedDataTableCopy()
        val readings = autosensDataStore.getBgReadingsDataTableCopy()
        // Custom build: show the arrow supplied by the CGM source (e.g. Dexcom, via xDrip) when it is current.
        // Smoothing plugins clear trendArrow on the bucketed data, so read it from the raw reading. The bucketed
        // data is null until there are 3 readings, the source arrow must not depend on it.
        if (data.isNullOrEmpty()) return sourceArrow(readings, System.currentTimeMillis())
        sourceArrow(readings, data[0].timestamp)?.let { return it }
        return calculateDirection(data)
    }

    /** Arrow of the newest raw reading, if the source provided one and it is within [SOURCE_ARROW_MAX_AGE_MS] of [referenceTime]. */
    private fun sourceArrow(readings: List<GV>, referenceTime: Long): TrendArrow? {
        val latest = readings.firstOrNull() ?: return null
        if (latest.trendArrow == TrendArrow.NONE) return null
        if (kotlin.math.abs(latest.timestamp - referenceTime) > SOURCE_ARROW_MAX_AGE_MS) return null
        return latest.trendArrow
    }

    override fun getTrendDescription(autosensDataStore: AutosensDataStore): String =
        rh.gs(getTrendArrow(autosensDataStore).directionToDescription())

    private fun calculateDirection(readings: MutableList<InMemoryGlucoseValue>): TrendArrow {

        if (readings.size < 2)
            return TrendArrow.NONE
        val current = readings[0]
        val previous = readings[1]

        // Avoid division by 0
        val slope =
            if (current.timestamp == previous.timestamp) 0.0
            else (previous.recalculated - current.recalculated) / (previous.timestamp - current.timestamp)

        val slopeByMinute = slope * 60000

        return when {
            slopeByMinute <= -3.5 -> TrendArrow.DOUBLE_DOWN
            slopeByMinute <= -2   -> TrendArrow.SINGLE_DOWN
            slopeByMinute <= -1   -> TrendArrow.FORTY_FIVE_DOWN
            slopeByMinute <= 1    -> TrendArrow.FLAT
            slopeByMinute <= 2    -> TrendArrow.FORTY_FIVE_UP
            slopeByMinute <= 3.5  -> TrendArrow.SINGLE_UP
            slopeByMinute <= 40   -> TrendArrow.DOUBLE_UP
            else                  -> TrendArrow.NONE
        }
    }

    private companion object {
        const val SOURCE_ARROW_MAX_AGE_MS = 10 * 60 * 1000L
    }
}
