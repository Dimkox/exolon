import Foundation
import GameController

final class GamepadInput {
    private let inputState: InputState
    private weak var scene: GameScene?

    init(inputState: InputState, scene: GameScene) {
        self.inputState = inputState
        self.scene = scene
    }

    func start() {
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(controllerDidConnect(_:)),
            name: .GCControllerDidConnect,
            object: nil
        )

        NotificationCenter.default.addObserver(
            self,
            selector: #selector(controllerDidDisconnect(_:)),
            name: .GCControllerDidDisconnect,
            object: nil
        )

        for controller in GCController.controllers() {
            configure(controller)
        }

        updateStatus()
    }

    @objc private func controllerDidConnect(_ notification: Notification) {
        guard let controller = notification.object as? GCController else { return }
        configure(controller)
        updateStatus()
    }

    @objc private func controllerDidDisconnect(_ notification: Notification) {
        inputState.resetGamepad()
        updateStatus()
    }

    private func configure(_ controller: GCController) {
        guard let gamepad = controller.extendedGamepad else { return }

        gamepad.dpad.left.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.inputState.set(.moveLeft, pressed: pressed, source: .gamepadDPad)
        }
        gamepad.dpad.right.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.inputState.set(.moveRight, pressed: pressed, source: .gamepadDPad)
        }
        gamepad.dpad.down.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.inputState.set(.crouch, pressed: pressed, source: .gamepadDPad)
            self?.inputState.set(.menuDown, pressed: pressed, source: .gamepadDPad)
        }
        gamepad.dpad.up.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.inputState.set(.jump, pressed: pressed, source: .gamepadDPad)
            self?.inputState.set(.menuUp, pressed: pressed, source: .gamepadDPad)
        }

        gamepad.leftThumbstick.valueChangedHandler = { [weak self] _, x, y in
            guard let self = self else { return }
            let deadZone: Float = 0.35
            self.inputState.set(.moveLeft, pressed: x < -deadZone, source: .gamepadStick)
            self.inputState.set(.moveRight, pressed: x > deadZone, source: .gamepadStick)
            self.inputState.set(.crouch, pressed: y < -0.65, source: .gamepadStick)
            self.inputState.set(.menuDown, pressed: y < -0.65, source: .gamepadStick)
            self.inputState.set(.menuUp, pressed: y > 0.65, source: .gamepadStick)
        }

        // GameController generic mapping. On a PlayStation pad:
        // buttonA = Cross (jump), buttonX = Square (fire / menu restart),
        // buttonB = Circle (grenade).
        gamepad.buttonA.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.inputState.set(.jump, pressed: pressed, source: .gamepadButtons)
        }
        gamepad.buttonX.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.inputState.set(.fire, pressed: pressed, source: .gamepadButtons)
        }
        gamepad.buttonB.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.inputState.set(.grenade, pressed: pressed, source: .gamepadButtons)
        }

        controller.controllerPausedHandler = { [weak self] _ in
            guard let self = self else { return }
            self.inputState.set(.pause, pressed: true, source: .gamepadButtons)
            self.inputState.set(.pause, pressed: false, source: .gamepadButtons)
        }
    }

    private func updateStatus() {
        let count = GCController.controllers().filter { $0.extendedGamepad != nil }.count
        let text = count > 0 ? "GAMEPAD: connected (\(count))" : "GAMEPAD: waiting / keyboard ready"
        DispatchQueue.main.async { [weak self] in
            self?.scene?.setGamepadStatus(text)
        }
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
    }
}
