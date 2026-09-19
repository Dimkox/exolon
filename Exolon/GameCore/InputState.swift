import Foundation

enum GameAction: CaseIterable, Hashable {
    case moveLeft
    case moveRight
    case jump
    case crouch
    case fire
    case grenade
    case pause
    case menuUp
    case menuDown
    case debugHitboxes
}

enum InputSource: Hashable {
    case keyboard
    case gamepadDPad
    case gamepadStick
    case gamepadButtons
}

struct InputSnapshot {
    let moveLeft: Bool
    let moveRight: Bool
    let jump: Bool
    let crouch: Bool
    let fire: Bool
    let grenade: Bool
    let pause: Bool
    let menuUp: Bool
    let menuDown: Bool
    let debugHitboxes: Bool
}

final class InputState {
    private let lock = NSLock()
    private var pressedBySource: [InputSource: Set<GameAction>] = [:]
    private var pausePressPending = false

    func set(_ action: GameAction, pressed isPressed: Bool, source: InputSource) {
        lock.lock()
        defer { lock.unlock() }

        var actions = pressedBySource[source] ?? []
        if isPressed {
            if action == .pause && !actions.contains(.pause) {
                pausePressPending = true
            }
            actions.insert(action)
        } else {
            actions.remove(action)
        }
        pressedBySource[source] = actions
    }

    func reset(source: InputSource) {
        lock.lock()
        pressedBySource[source] = []
        lock.unlock()
    }

    func resetAll() {
        lock.lock()
        pressedBySource.removeAll()
        pausePressPending = false
        lock.unlock()
    }

    /// Pause is an edge-triggered command. The gamepad pause/options callback
    /// arrives as a pulse, so polling only the current held-state can miss it.
    func consumePausePress() -> Bool {
        lock.lock()
        defer { lock.unlock() }
        let pending = pausePressPending
        pausePressPending = false
        return pending
    }

    func resetGamepad() {
        lock.lock()
        pressedBySource[.gamepadDPad] = []
        pressedBySource[.gamepadStick] = []
        pressedBySource[.gamepadButtons] = []
        lock.unlock()
    }

    func snapshot() -> InputSnapshot {
        lock.lock()
        defer { lock.unlock() }

        let pressed = pressedBySource.values.reduce(into: Set<GameAction>()) { result, actions in
            result.formUnion(actions)
        }

        return InputSnapshot(
            moveLeft: pressed.contains(.moveLeft),
            moveRight: pressed.contains(.moveRight),
            jump: pressed.contains(.jump),
            crouch: pressed.contains(.crouch),
            fire: pressed.contains(.fire),
            grenade: pressed.contains(.grenade),
            pause: pressed.contains(.pause),
            menuUp: pressed.contains(.menuUp),
            menuDown: pressed.contains(.menuDown),
            debugHitboxes: pressed.contains(.debugHitboxes)
        )
    }
}
