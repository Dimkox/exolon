import AppKit
import SpriteKit

final class GameView: SKView {
    weak var inputState: InputState?

    override var acceptsFirstResponder: Bool { true }

    override func keyDown(with event: NSEvent) {
        setKey(event.keyCode, pressed: true)
    }

    override func keyUp(with event: NSEvent) {
        setKey(event.keyCode, pressed: false)
    }

    // Option is a modifier key on macOS. Pressing it by itself is reported
    // through flagsChanged rather than the normal keyDown/keyUp path.
    override func flagsChanged(with event: NSEvent) {
        switch event.keyCode {
        case 58, 61: // Left / right Option
            let optionIsDown = event.modifierFlags.contains(.option)
            inputState?.set(.grenade, pressed: optionIsDown, source: .keyboard)
        default:
            super.flagsChanged(with: event)
        }
    }

    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()

        if let window = window {
            NotificationCenter.default.addObserver(
                self,
                selector: #selector(windowDidResignKey),
                name: NSWindow.didResignKeyNotification,
                object: window
            )
        }
    }

    @objc private func windowDidResignKey() {
        inputState?.reset(source: .keyboard)
    }

    private func setKey(_ keyCode: UInt16, pressed: Bool) {
        guard let inputState = inputState else { return }

        switch keyCode {
        case 123: // Left arrow
            inputState.set(.moveLeft, pressed: pressed, source: .keyboard)
        case 124: // Right arrow
            inputState.set(.moveRight, pressed: pressed, source: .keyboard)
        case 125: // Down arrow
            inputState.set(.crouch, pressed: pressed, source: .keyboard)
            inputState.set(.menuDown, pressed: pressed, source: .keyboard)
        case 126: // Up arrow
            inputState.set(.jump, pressed: pressed, source: .keyboard)
            inputState.set(.menuUp, pressed: pressed, source: .keyboard)
        case 49: // Space
            inputState.set(.fire, pressed: pressed, source: .keyboard)
        case 58, 61: // Left / right Option
            inputState.set(.grenade, pressed: pressed, source: .keyboard)
        case 35: // P
            inputState.set(.pause, pressed: pressed, source: .keyboard)
        case 122: // F1
            inputState.set(.debugHitboxes, pressed: pressed, source: .keyboard)
        default:
            break
        }
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
    }
}
