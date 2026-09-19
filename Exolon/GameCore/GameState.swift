import Foundation

enum GameFlowState: String {
    case title
    case playing
    case paused
    case playerDead
    case respawning
    case gameOver
    case contentComplete
}

struct GameCheckpoint {
    let levelName: String
    let ammo: Int
    let grenades: Int
    let points: Int
    let lives: Int
}

final class GamePersistence {
    static let shared = GamePersistence()

    private enum Key {
        static let hasCheckpoint = "Exolon.Step10.HasCheckpoint"
        static let levelName = "Exolon.Step10.LevelName"
        static let ammo = "Exolon.Step10.Ammo"
        static let grenades = "Exolon.Step10.Grenades"
        static let points = "Exolon.Step10.Points"
        static let lives = "Exolon.Step10.Lives"
        static let highScore = "Exolon.Step10.HighScore"
    }

    private let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    func loadCheckpoint() -> GameCheckpoint? {
        guard defaults.bool(forKey: Key.hasCheckpoint) else { return nil }
        guard let levelName = defaults.string(forKey: Key.levelName), !levelName.isEmpty else { return nil }

        return GameCheckpoint(
            levelName: levelName,
            ammo: max(0, defaults.integer(forKey: Key.ammo)),
            grenades: max(0, defaults.integer(forKey: Key.grenades)),
            points: max(0, defaults.integer(forKey: Key.points)),
            lives: max(1, defaults.integer(forKey: Key.lives))
        )
    }

    func saveCheckpoint(_ checkpoint: GameCheckpoint) {
        defaults.set(true, forKey: Key.hasCheckpoint)
        defaults.set(checkpoint.levelName, forKey: Key.levelName)
        defaults.set(checkpoint.ammo, forKey: Key.ammo)
        defaults.set(checkpoint.grenades, forKey: Key.grenades)
        defaults.set(checkpoint.points, forKey: Key.points)
        defaults.set(checkpoint.lives, forKey: Key.lives)
    }

    func clearCheckpoint() {
        defaults.removeObject(forKey: Key.hasCheckpoint)
        defaults.removeObject(forKey: Key.levelName)
        defaults.removeObject(forKey: Key.ammo)
        defaults.removeObject(forKey: Key.grenades)
        defaults.removeObject(forKey: Key.points)
        defaults.removeObject(forKey: Key.lives)
    }

    func loadHighScore() -> Int {
        max(0, defaults.integer(forKey: Key.highScore))
    }

    func saveHighScore(_ value: Int) {
        defaults.set(max(0, value), forKey: Key.highScore)
    }
}

final class GameState {
    static let startingAmmo = 99
    static let startingGrenades = 10
    static let startingLives = 9

    var ammo = GameState.startingAmmo
    var grenades = GameState.startingGrenades
    var points = 0
    var lives = GameState.startingLives
    var highScore = 0
    // Exolon labels the first screen as zone 000.
    var zone = 0

    func resetForNewGame() {
        ammo = GameState.startingAmmo
        grenades = GameState.startingGrenades
        points = 0
        lives = GameState.startingLives
        zone = 0
    }
}
