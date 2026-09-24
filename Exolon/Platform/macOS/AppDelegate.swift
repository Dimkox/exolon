import AppKit
import SpriteKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var window: NSWindow!
    private var gamepadInput: GamepadInput!

    /// The one concrete gameplay log this process owns. Everything else takes
    /// `any GameplayEventSink`, so the default (`NullGameplayEventSink` inside `GameScene`) stays
    /// intact if composition ever happens without this class.
    private var gameplayLog: GameplayEventLog?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let contentRect = NSRect(x: 0, y: 0, width: 1024, height: 768)
        window = NSWindow(
            contentRect: contentRect,
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Exolon Remake — Step 9 Rebase"
        window.minSize = NSSize(width: 640, height: 480)
        window.center()

        let gameView = GameView(frame: contentRect)
        gameView.autoresizingMask = [.width, .height]
        gameView.ignoresSiblingOrder = true
        gameView.shouldCullNonVisibleNodes = true

        let scene = GameScene(size: GameConstants.logicalSize)
        scene.scaleMode = .aspectFit
        // Composition root: environment plus build configuration decide the mode and the level,
        // then the sink is injected scene -> level runtime -> player (architect ruling D3).
        let configuration = GameplayEventLog.Configuration.resolved(environment: ProcessInfo.processInfo.environment,
                                                                   defaultLevel: AppDelegate.defaultEmissionLevel,
                                                                   temporaryDirectory: NSTemporaryDirectory(),
                                                                   build: AppDelegate.buildIdentifier)
        let log = GameplayEventLog(configuration: configuration)
        gameplayLog = log
        scene.events = log
        gameView.inputState = scene.inputState
        gameView.presentScene(scene)

        window.contentView = gameView
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        window.makeFirstResponder(gameView)

        gamepadInput = GamepadInput(inputState: scene.inputState, scene: scene)
        gamepadInput.start()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }

    func applicationWillTerminate(_ notification: Notification) {
        // `log.end` plus a final buffered flush; the kill switch path never gets here with a file.
        gameplayLog?.shutdown(reason: .appQuit)
    }

    /// Debug = 1 (state, actions, damage, bonus), Release = 0 which `Configuration.resolved`
    /// turns into `.off`, so a shipped build writes nothing until `EXOLON_EVENT_LOG` says otherwise.
    private static var defaultEmissionLevel: Int {
        #if DEBUG
        return 1
        #else
        return 0
        #endif
    }

    /// CFBundleShortVersion+CFBundleVersion, or `unknown` when running outside a bundle.
    private static var buildIdentifier: String {
        let info = Bundle.main.infoDictionary
        let short = info?["CFBundleShortVersionString"] as? String ?? ""
        let build = info?["CFBundleVersion"] as? String ?? ""
        let combined = [short, build].filter { !$0.isEmpty }.joined(separator: "+")
        return combined.isEmpty ? "unknown" : combined
    }
}
