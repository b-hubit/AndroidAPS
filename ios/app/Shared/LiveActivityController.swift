import ActivityKit
import Foundation
import UIKit

/// b-hubit fork (branch ios-live-activity): keeps one glucose Live Activity running and tells the
/// user's Home Assistant where to push to.
///
/// The app never updates the activity itself. iOS freezes the app in the background, so anything it
/// did would stop there; a push is delivered whatever state the app is in. So the app's whole job is
/// handing out addresses:
///
/// - the *update* token of the running activity: Home Assistant pushes every new reading to it;
/// - the *push-to-start* token (iOS 17.2+): an activity lives at most 8 hours, and with this token
///   Home Assistant starts the next one by itself, without the app being opened.
///
/// When an activity is started by a push, iOS wakes the app in the background long enough for
/// `activityUpdates` to hand it over and for its update token to be sent.
///
/// Both are posted as JSON to the webhook URL set in the iOS Settings app (Settings > AAPS Live).
/// Nothing is sent anywhere when that URL is empty.
@MainActor
final class LiveActivityController {

    static let shared = LiveActivityController()

    private static let webhookKey = "live_activity_webhook"
    private static let enabledKey = "live_activity_enabled"

    private var observed = Set<String>()
    private var startTokenTask: Task<Void, Never>?
    private var activityUpdatesTask: Task<Void, Never>?

    private init() {}

    private var webhookURL: URL? {
        guard let text = UserDefaults.standard.string(forKey: Self.webhookKey)?
            .trimmingCharacters(in: .whitespacesAndNewlines), !text.isEmpty else { return nil }
        return URL(string: text)
    }

    /// On by default: the switch in Settings is only read once the user has opened that page.
    private var enabled: Bool {
        UserDefaults.standard.object(forKey: Self.enabledKey) as? Bool ?? true
    }

    /// Called when the process starts, in the foreground or not. iOS launches the app in the
    /// background after Home Assistant started an activity by push, and only this path runs then:
    /// the scene never becomes active, so the new activity's token has to be picked up from here.
    func startObserving() {
        guard enabled, webhookURL != nil else { return }
        observeTokens()
    }

    /// Called every time the app comes to the front. Cheap when everything is already running.
    func refresh() {
        guard enabled, webhookURL != nil else {
            endAll()
            return
        }
        guard ActivityAuthorizationInfo().areActivitiesEnabled else {
            NSLog("AAPS Live: Live Activities are switched off for this app in iOS Settings")
            return
        }
        observeTokens()
        let running = Activity<GlucoseActivityAttributes>.activities.filter {
            $0.activityState == .active || $0.activityState == .stale
        }
        if running.isEmpty { requestNew() }
    }

    private func observeTokens() {
        if startTokenTask == nil, #available(iOS 17.2, *) {
            startTokenTask = Task { [weak self] in
                for await data in Activity<GlucoseActivityAttributes>.pushToStartTokenUpdates {
                    await self?.post(kind: "start", token: data.hexString, activityId: nil)
                }
            }
        }
        if activityUpdatesTask == nil {
            // Activities started by a push-to-start arrive here, also when iOS woke the app for it.
            activityUpdatesTask = Task { [weak self] in
                for await activity in Activity<GlucoseActivityAttributes>.activityUpdates {
                    self?.observe(activity)
                }
            }
        }

        Activity<GlucoseActivityAttributes>.activities
            .filter { $0.activityState == .active || $0.activityState == .stale }
            .forEach(observe)
    }

    private func requestNew() {
        do {
            let activity = try Activity.request(
                attributes: GlucoseActivityAttributes(name: "AAPS"),
                content: ActivityContent(state: .placeholder, staleDate: nil),
                pushType: .token
            )
            observe(activity)
        } catch {
            NSLog("AAPS Live: could not start the Live Activity: \(error)")
        }
    }

    private func observe(_ activity: Activity<GlucoseActivityAttributes>) {
        guard !observed.contains(activity.id) else { return }
        observed.insert(activity.id)
        Task { [weak self] in
            for await data in activity.pushTokenUpdates {
                await self?.post(kind: "update", token: data.hexString, activityId: activity.id)
            }
        }
    }

    private func endAll() {
        let activities = Activity<GlucoseActivityAttributes>.activities
        guard !activities.isEmpty else { return }
        Task {
            for activity in activities {
                await activity.end(nil, dismissalPolicy: .immediate)
            }
        }
    }

    private func post(kind: String, token: String, activityId: String?) async {
        guard let url = webhookURL else { return }
        var body: [String: String] = [
            "kind": kind,
            "token": token,
            "bundle_id": Bundle.main.bundleIdentifier ?? "",
            // Lets Home Assistant keep one Live Activity per iPhone when several people follow.
            "device": UIDevice.current.identifierForVendor?.uuidString ?? "default"
        ]
        if let activityId { body["activity_id"] = activityId }

        var request = URLRequest(url: url, timeoutInterval: 20)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            let status = (response as? HTTPURLResponse)?.statusCode ?? 0
            NSLog("AAPS Live: sent \(kind) token to Home Assistant, HTTP \(status)")
        } catch {
            NSLog("AAPS Live: could not reach Home Assistant: \(error)")
        }
    }
}

private extension Data {
    var hexString: String { map { String(format: "%02x", $0) }.joined() }
}
