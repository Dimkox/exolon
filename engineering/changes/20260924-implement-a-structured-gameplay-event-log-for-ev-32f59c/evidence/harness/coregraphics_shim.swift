@_exported import Foundation

/// Linux-only stand-in: swift-corelibs-Foundation provides CGFloat/CGPoint/CGSize/CGRect (which is
/// why `Player.swift`, `InputState.swift`, `GameState.swift` and `GameConstants.swift` compile here
/// unchanged) but not `CGVector`, which `Player.velocity` uses. Four lines, no behavior.
public struct CGVector {
    public var dx: CGFloat
    public var dy: CGFloat
    public init(dx: CGFloat, dy: CGFloat) { self.dx = dx; self.dy = dy }
    public static let zero = CGVector(dx: 0, dy: 0)
}
