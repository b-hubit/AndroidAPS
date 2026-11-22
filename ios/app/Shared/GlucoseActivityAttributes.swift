import ActivityKit
import Foundation

/// b-hubit fork (branch ios-live-activity): what the glucose Live Activity shows.
///
/// Compiled into the app and into the AAPSLiveActivity widget extension, because both sides have to
/// agree on the type. The content is filled by pushes from the user's own Home Assistant
/// (see ios/live-activity/), not by the app: a suspended app cannot update anything, a push can.
///
/// The JSON keys of `ContentState` are what the push's `content-state` must carry, so they are kept
/// plain and stable. Times are Unix seconds as numbers, not `Date`: ActivityKit decodes a `Date`
/// as seconds since 2001, which a server writing Unix time would get wrong by 31 years.
struct GlucoseActivityAttributes: ActivityAttributes {

    public struct ContentState: Codable, Hashable {
        /// Glucose as it should be shown, already in the user's units ("123" or "6.8"). Empty = none yet.
        var value: String
        /// Glucose in mg/dL, only for choosing the colour. 0 when unknown.
        var mgdl: Int
        /// Trend arrow as text ("↗"), empty when unknown.
        var arrow: String
        /// Change since the previous reading, formatted ("+3", "-0.2").
        var delta: String
        /// When the reading was taken, Unix seconds. 0 when unknown.
        var readingTime: Double
        /// Insulin on board, formatted ("1.25"), empty when unknown.
        var iob: String
        /// Carbs on board, formatted ("12"), empty when unknown.
        var cob: String
        /// Low and high limits in mg/dL for the colour.
        var low: Int
        var high: Int

        static let placeholder = ContentState(
            value: "", mgdl: 0, arrow: "", delta: "", readingTime: 0, iob: "", cob: "", low: 70, high: 180
        )
    }

    /// Fixed for the life of one activity. Only a label.
    var name: String
}
