import ActivityKit
import SwiftUI
import WidgetKit

/// b-hubit fork (branch ios-live-activity): the glucose Live Activity.
///
/// Shown on the Lock Screen, in the Dynamic Island and - through the `.small` family - in the
/// Apple Watch Smart Stack, which mirrors the iPhone's Live Activities on watchOS 11 and later.
/// Every update comes as a push from the user's Home Assistant; this file only draws.
@main
struct AAPSLiveActivityBundle: WidgetBundle {
    var body: some Widget {
        GlucoseLiveActivity()
    }
}

struct GlucoseLiveActivity: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: GlucoseActivityAttributes.self) { context in
            LockScreenView(state: context.state, isStale: context.isStale)
                .activityBackgroundTint(Color.black.opacity(0.75))
                .activitySystemActionForegroundColor(.white)
        } dynamicIsland: { context in
            let state = context.state
            return DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
                    HStack(spacing: 4) {
                        Text(state.value.isEmpty ? "--" : state.value)
                            .font(.system(size: 34, weight: .bold, design: .rounded))
                            .foregroundStyle(state.color)
                            .lineLimit(1)
                            .minimumScaleFactor(0.6)
                        Text(state.arrow).font(.title2).foregroundStyle(state.color)
                    }
                    .opacity(state.dimmed(context.isStale) ? 0.5 : 1)
                }
                DynamicIslandExpandedRegion(.trailing) {
                    VStack(alignment: .trailing, spacing: 2) {
                        Text(state.delta).font(.headline)
                        HStack(spacing: 3) {
                            WarningIcon(state: state, isStale: context.isStale)
                            AgeText(state: state, isStale: context.isStale)
                        }
                        .font(.caption).foregroundStyle(.secondary)
                    }
                }
                DynamicIslandExpandedRegion(.bottom) {
                    DetailsRow(state: state)
                }
            } compactLeading: {
                Text(state.value.isEmpty ? "--" : state.value)
                    .font(.system(.body, design: .rounded).bold())
                    .foregroundStyle(state.color)
                    .lineLimit(1)
                    .minimumScaleFactor(0.6)
            } compactTrailing: {
                if state.warning(context.isStale) != nil {
                    WarningIcon(state: state, isStale: context.isStale)
                } else {
                    Text(state.arrow).foregroundStyle(state.color)
                }
            } minimal: {
                Text(state.value.isEmpty ? "--" : state.value)
                    .font(.system(.caption, design: .rounded).bold())
                    .foregroundStyle(state.color)
                    .lineLimit(1)
                    .minimumScaleFactor(0.6)
            }
        }
        // Apple Watch Smart Stack (and CarPlay): the compact layout below.
        .supplementalActivityFamilies([.small])
    }
}

/// Lock Screen, and the watch when the family is `.small`.
private struct LockScreenView: View {
    let state: GlucoseActivityAttributes.ContentState
    let isStale: Bool
    @Environment(\.activityFamily) private var family

    private var dim: Bool { state.dimmed(isStale) }

    var body: some View {
        switch family {
        case .small:
            HStack(spacing: 6) {
                HStack(spacing: 6) {
                    Text(state.value.isEmpty ? "--" : state.value)
                        .font(.system(size: 30, weight: .bold, design: .rounded))
                        .foregroundStyle(state.color)
                        .lineLimit(1)
                        .minimumScaleFactor(0.6)
                    VStack(alignment: .leading, spacing: 0) {
                        Text(state.arrow).font(.headline).foregroundStyle(state.color)
                        Text(state.delta).font(.caption2)
                    }
                }
                .opacity(dim ? 0.5 : 1)
                Spacer(minLength: 0)
                VStack(alignment: .trailing, spacing: 0) {
                    WarningIcon(state: state, isStale: isStale).font(.caption)
                    AgeText(state: state, isStale: isStale).font(.caption2).foregroundStyle(.secondary)
                }
            }
            .padding(.horizontal, 6)
        default:
            HStack(alignment: .center, spacing: 12) {
                HStack(alignment: .firstTextBaseline, spacing: 6) {
                    Text(state.value.isEmpty ? "--" : state.value)
                        .font(.system(size: 48, weight: .bold, design: .rounded))
                        .foregroundStyle(state.color)
                        .lineLimit(1)
                        .minimumScaleFactor(0.6)
                    Text(state.arrow)
                        .font(.system(size: 30, weight: .semibold))
                        .foregroundStyle(state.color)
                }
                .opacity(dim ? 0.5 : 1)
                VStack(alignment: .leading, spacing: 4) {
                    Text(state.delta).font(.title3.weight(.semibold)).foregroundStyle(.white)
                        .opacity(dim ? 0.5 : 1)
                    HStack(spacing: 4) {
                        WarningIcon(state: state, isStale: isStale)
                        AgeText(state: state, isStale: isStale)
                    }
                    .font(.subheadline).foregroundStyle(.white.opacity(0.7))
                }
                Spacer(minLength: 0)
                DetailsColumn(state: state)
                    .opacity(dim ? 0.5 : 1)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
        }
    }
}

/// "3' temu": minutes since the reading, sent by Home Assistant once a minute (a counting `.timer`
/// text stretched to all the width it got and blanked the whole Live Activity). Without that field,
/// or when updates stopped (the text would be frozen and wrong), the time of the reading is shown.
private struct AgeText: View {
    let state: GlucoseActivityAttributes.ContentState
    let isStale: Bool

    var body: some View {
        if !isStale, let age = state.age, !age.isEmpty {
            Text(age).monospacedDigit().lineLimit(1)
        } else if state.readingTime > 0 {
            Text(Date(timeIntervalSince1970: state.readingTime), style: .time)
                .monospacedDigit()
                .lineLimit(1)
        } else {
            Text("")
        }
    }
}

private struct DetailsColumn: View {
    let state: GlucoseActivityAttributes.ContentState

    var body: some View {
        VStack(alignment: .trailing, spacing: 4) {
            if !state.iob.isEmpty { Text("IOB \(state.iob) U").font(.subheadline).foregroundStyle(.white) }
            if !state.cob.isEmpty { Text("COB \(state.cob) g").font(.subheadline).foregroundStyle(.white) }
        }
    }
}

private struct DetailsRow: View {
    let state: GlucoseActivityAttributes.ContentState

    var body: some View {
        HStack {
            if !state.iob.isEmpty { Text("IOB \(state.iob) U") }
            Spacer()
            if !state.cob.isEmpty { Text("COB \(state.cob) g") }
        }
        .font(.subheadline)
        .padding(.horizontal, 8)
    }
}

/// Something is wrong with the data, shown next to the age:
/// - red (!)  : no update from Home Assistant for a few minutes - the automation stopped, Home
///              Assistant or Nightscout is down, or the iPhone is offline. The age is frozen, so the
///              time of the reading is shown instead.
/// - orange ⚠ : updates arrive, but the newest reading in Nightscout is older than 11 minutes -
///              the sensor, the phone with AAPS or its upload is the problem.
private struct WarningIcon: View {
    let state: GlucoseActivityAttributes.ContentState
    let isStale: Bool

    var body: some View {
        switch state.warning(isStale) {
        case .noUpdates:
            Image(systemName: "exclamationmark.circle.fill").foregroundStyle(.red)
        case .oldReading:
            Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(.orange)
        case nil:
            EmptyView()
        }
    }
}

enum DataWarning { case noUpdates, oldReading }

private extension GlucoseActivityAttributes.ContentState {
    /// A reading older than this is "old", as Nightscout and AAPS treat it.
    static let oldAfter: Double = 11 * 60

    func warning(_ isStale: Bool) -> DataWarning? {
        if isStale { return .noUpdates }
        if let updated, readingTime > 0, updated - readingTime > Self.oldAfter { return .oldReading }
        return nil
    }

    func dimmed(_ isStale: Bool) -> Bool { warning(isStale) != nil }

    var color: Color {
        guard mgdl > 0 else { return .gray }
        if mgdl < low { return .red }
        if mgdl > high { return .yellow }
        return .green
    }
}
