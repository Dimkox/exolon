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
    /// Which source most recently reported each held action. The merged `snapshot()` cannot answer
    /// that, and `input.action_edge{source}` is a frozen contract field, so the attribution is
    /// recorded where the press arrives instead of guessed at the tick.
    private var sourceByAction: [GameAction: InputSource] = [:]
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
            sourceByAction[action] = source
        } else {
            actions.remove(action)
            if sourceByAction[action] == source {
                sourceByAction[action] = nil
            }
        }
        pressedBySource[source] = actions
    }

    /// Read once per emitted edge (a few per second), never per frame.
    func source(for action: GameAction) -> InputSource? {
        lock.lock()
        defer { lock.unlock() }
        return sourceByAction[action]
    }

    func reset(source: InputSource) {
        lock.lock()
        let cleared = pressedBySource[source] ?? []
        pressedBySource[source] = []
        for action in cleared where sourceByAction[action] == source {
            sourceByAction[action] = nil
        }
        lock.unlock()
    }

    func resetAll() {
        lock.lock()
        pressedBySource.removeAll()
        sourceByAction.removeAll()
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
        for source in [InputSource.gamepadDPad, .gamepadStick, .gamepadButtons] {
            let cleared = pressedBySource[source] ?? []
            pressedBySource[source] = []
            for action in cleared where sourceByAction[action] == source {
                sourceByAction[action] = nil
            }
        }
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
