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
                        Text(state.arrow).font(.title2).foregroundStyle(state.color)
                    }
                }
                DynamicIslandExpandedRegion(.trailing) {
                    VStack(alignment: .trailing, spacing: 2) {
                        Text(state.delta).font(.headline)
                        AgeText(state: state).font(.caption).foregroundStyle(.secondary)
                    }
                }
                DynamicIslandExpandedRegion(.bottom) {
                    DetailsRow(state: state)
                }
            } compactLeading: {
                Text(state.value.isEmpty ? "--" : state.value)
                    .font(.system(.body, design: .rounded).bold())
                    .foregroundStyle(state.color)
            } compactTrailing: {
                Text(state.arrow).foregroundStyle(state.color)
            } minimal: {
                Text(state.value.isEmpty ? "--" : state.value)
                    .font(.system(.caption, design: .rounded).bold())
                    .foregroundStyle(state.color)
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

    var body: some View {
        switch family {
        case .small:
            HStack(spacing: 6) {
                Text(state.value.isEmpty ? "--" : state.value)
                    .font(.system(size: 30, weight: .bold, design: .rounded))
                    .foregroundStyle(state.color)
                VStack(alignment: .leading, spacing: 0) {
                    Text(state.arrow).font(.headline).foregroundStyle(state.color)
                    Text(state.delta).font(.caption2)
                }
                Spacer(minLength: 0)
                AgeText(state: state).font(.caption2).foregroundStyle(.secondary)
            }
            .opacity(isStale ? 0.5 : 1)
            .padding(.horizontal, 6)
        default:
            HStack(alignment: .center, spacing: 12) {
                HStack(alignment: .firstTextBaseline, spacing: 6) {
                    Text(state.value.isEmpty ? "--" : state.value)
                        .font(.system(size: 48, weight: .bold, design: .rounded))
                        .foregroundStyle(state.color)
                    Text(state.arrow)
                        .font(.system(size: 30, weight: .semibold))
                        .foregroundStyle(state.color)
                }
                VStack(alignment: .leading, spacing: 4) {
                    Text(state.delta).font(.title3.weight(.semibold)).foregroundStyle(.white)
                    AgeText(state: state).font(.subheadline).foregroundStyle(.white.opacity(0.7))
                }
                Spacer(minLength: 0)
                DetailsColumn(state: state)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .opacity(isStale ? 0.5 : 1)
        }
    }
}

/// "3 min" - counts up by itself on the device, so it stays right between pushes.
private struct AgeText: View {
    let state: GlucoseActivityAttributes.ContentState

    var body: some View {
        if state.readingTime > 0 {
            Text(Date(timeIntervalSince1970: state.readingTime), style: .relative)
                .monospacedDigit()
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

private extension GlucoseActivityAttributes.ContentState {
    var color: Color {
        guard mgdl > 0 else { return .gray }
        if mgdl < low { return .red }
        if mgdl > high { return .yellow }
        return .green
    }
}
