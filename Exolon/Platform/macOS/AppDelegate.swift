import AppKit
import SpriteKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var window: NSWindow!
    private var gamepadInput: GamepadInput!

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
}
