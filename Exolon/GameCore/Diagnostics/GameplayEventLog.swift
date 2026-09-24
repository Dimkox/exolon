import Foundation

/// Production gameplay event log.
///
/// Shape (architect section 3, rulings D1-D4): a synchronous, allocation-free 24-byte append into
/// a preallocated ring under `NSLock`, plus one serial `.utility` drain that formats and writes.
/// **The ring IS the file backlog** - a single-slot batch handoff lost 99.1 % of events in the
/// prototype (section 2.1/1), so the writer reads through a consumer cursor and overflow is a
/// counted, visible drop. The drain timer runs its body **on** the queue, never through the
/// `queue.sync` wrapper (section 2.1/2 was a hard dispatch deadlock in the prototype).
///
/// Frozen contract: `engineering/contracts/schemas/gameplay-event-v1.schema.json`.
///
/// There is deliberately no crash path: nothing here calls `fatalError`/`precondition`, because a
/// log that can stop the game is worse than no log (integration section 11). Every failure
/// increments the drop counter and, once, says so on stderr.

enum GameplayEventWriterMode: Equatable {
    /// Ring only; the writer object is never touched, so no file can exist (kill switch).
    case off
    /// No queue, no timer; the caller thread drains (headless harness).
    case synchronous
    /// One serial `.utility` queue plus a drain timer (production).
    case asynchronous
}

/// Sink for already-formatted JSONL text. Injectable so tests never touch a real disk.
protocol GameplayEventWriter: AnyObject {
    /// Bytes already in the file this writer currently holds (buffer included).
    var bytesInCurrentFile: Int { get }
    /// Rotation index of the file currently held; 0 for the first file.
    var rotationIndex: Int { get }
    /// Absolute path of the file currently held.
    var currentPath: String { get }
    /// Path the writer will open on the next rotation. Needed because `log.rotate` is the last line
    /// of the **retired** file, so it must name its successor before that successor exists.
    func nextFilePath() -> String
    /// Opens rotation 0. False when the file could not be created (never fatal).
    func openFirstFile() -> Bool
    /// Buffers formatted text; reaches the device at the buffer size or on `synchronize()`.
    func write(_ text: String)
    /// Pushes the buffer to the file.
    func synchronize()
    /// Flushes and closes the current file, opens rotation index +1, prunes old generations.
    func rotateToNextFile() -> Bool
    /// Closes for good.
    func closeFile()
}

/// JSON-lines file writer with a bounded footprint:
/// `<directory>/<prefix><run token>-<rot>.jsonl`, `maxFileBytes` per file, `keptFiles`
/// generations, one buffered handle.
///
/// Location rule (brief ruling 2, integration section 7): the default directory is
/// `$TMPDIR/exolon/`, **never inside the repository clone** - an untracked log file under the
/// clone invalidates every fingerprint-bound receipt in this route.
final class GameplayEventFileWriter: GameplayEventWriter {
    private let directoryPath: String
    private let filePrefix: String
    private let runToken: String
    private let maxFileBytes: Int
    private let keptFiles: Int
    private let bufferBytes: Int

    private var fileHandle: FileHandle?
    private var buffer = Data()
    private var bytesOnDisk = 0
    private var rotation = 0
    private var path = ""

    init(directoryPath: String,
         filePrefix: String = "gameplay-",
         runToken: String,
         maxFileBytes: Int = 8_388_608,
         keptFiles: Int = 8,
         bufferBytes: Int = 65_536) {
        self.directoryPath = directoryPath
        self.filePrefix = filePrefix
        self.runToken = runToken
        self.maxFileBytes = max(1_024, maxFileBytes)
        self.keptFiles = max(1, keptFiles)
        self.bufferBytes = max(1_024, bufferBytes)
    }

    var bytesInCurrentFile: Int { bytesOnDisk + buffer.count }
    var rotationIndex: Int { rotation }
    var currentPath: String { path }

    func nextFilePath() -> String { path(forRotation: rotation + 1) }

    func path(forRotation rot: Int) -> String {
        "\(directoryPath)/\(filePrefix)\(runToken)-\(rot).jsonl"
    }

    func openFirstFile() -> Bool {
        guard ensureDirectory() else { return false }
        return open(rotation: 0)
    }

    func write(_ text: String) {
        guard fileHandle != nil else { return }
        buffer.append(Data(text.utf8))
        if buffer.count >= bufferBytes { flushBuffer() }
    }

    func synchronize() { flushBuffer() }

    func rotateToNextFile() -> Bool {
        flushBuffer()
        closeHandle()
        rotation += 1
        pruneOldFiles()
        return open(rotation: rotation)
    }

    func closeFile() {
        flushBuffer()
        closeHandle()
    }

    /// Deletes generations older than `rotation - (keptFiles - 1)`, i.e. the live file plus the
    /// `keptFiles - 1` newest retired ones survive. Keyed on the parsed rotation number, so the
    /// just-retired file is no longer protected by the path this writer still remembers.
    func pruneOldFiles() {
        let manager = FileManager.default
        guard let names = try? manager.contentsOfDirectory(atPath: directoryPath) else { return }
        let keepFrom = rotation - (keptFiles - 1)
        for name in names where name.hasPrefix(filePrefix) && name.hasSuffix(".jsonl") {
            guard let index = Self.rotationSuffix(of: name), index < keepFrom else { continue }
            try? manager.removeItem(atPath: "\(directoryPath)/\(name)")
        }
    }

    static func rotationSuffix(of name: String) -> Int? {
        guard let body = name.split(separator: "-").last else { return nil }
        return Int(body.split(separator: ".").first ?? "")
    }

    private func ensureDirectory() -> Bool {
        let manager = FileManager.default
        if manager.fileExists(atPath: directoryPath) { return true }
        do {
            try manager.createDirectory(atPath: directoryPath, withIntermediateDirectories: true, attributes: nil)
            return true
        } catch {
            return false
        }
    }

    private func open(rotation rot: Int) -> Bool {
        let candidate = path(forRotation: rot)
        buffer = Data()
        buffer.reserveCapacity(bufferBytes)
        bytesOnDisk = 0
        path = candidate
        guard ensureDirectory() else { return false }
        _ = FileManager.default.createFile(atPath: candidate, contents: Data(), attributes: nil)
        guard let handle = try? FileHandle(forWritingTo: URL(fileURLWithPath: candidate)) else {
            fileHandle = nil
            return false
        }
        fileHandle = handle
        return true
    }

    private func flushBuffer() {
        guard let handle = fileHandle, !buffer.isEmpty else { return }
        handle.write(buffer)
        bytesOnDisk += buffer.count
        buffer.removeAll(keepingCapacity: true)
    }

    private func closeHandle() {
        guard let handle = fileHandle else { return }
        try? handle.close()
        fileHandle = nil
    }
}

/// Bounded in-memory sink for tests and the Linux harness.
final class GameplayEventMemoryWriter: GameplayEventWriter {
    private(set) var text = ""
    private(set) var bytesInCurrentFileValue = 0
    private(set) var rotationValue = 0
    private(set) var synchronizeCalls = 0
    /// Oldest lines are dropped past this bound so an unthrottled harness cannot flood memory.
    var capacityLines: Int? = 20_000
    var openFailure = false

    init() {}

    var bytesInCurrentFile: Int { bytesInCurrentFileValue }
    var rotationIndex: Int { rotationValue }
    var currentPath: String { "memory://gameplay-events-\(rotationValue).jsonl" }
    func nextFilePath() -> String { "memory://gameplay-events-\(rotationValue + 1).jsonl" }
    var lines: [String] { text.split(separator: "\n", omittingEmptySubsequences: true).map(String.init) }

    func openFirstFile() -> Bool { !openFailure }

    func write(_ text: String) {
        self.text += text
        bytesInCurrentFileValue += text.utf8.count
        guard let capacity = capacityLines else { return }
        var held = self.text.split(separator: "\n", omittingEmptySubsequences: true).map(String.init)
        guard held.count > capacity else { return }
        held.removeFirst(held.count - capacity)
        self.text = held.reduce(into: "") { accumulator, line in accumulator += line + "\n" }
    }

    func synchronize() { synchronizeCalls += 1 }

    func rotateToNextFile() -> Bool {
        rotationValue += 1
        bytesInCurrentFileValue = 0
        return true
    }

    func closeFile() {}
}

/// The concrete sink. One instance, built by the composition root, injected everywhere.
final class GameplayEventLog: GameplayEventSink {
    struct Limits: Equatable {
        /// Power of two. 65 536 x 24 B = 1.5 MiB, about 18 s of the worst credible 3 600 ev/s
        /// backlog, while one drain clears 1.4 M ev/s (measurements M7/M9).
        var ringCapacity = 65_536
        /// Copy-out batch. M8 measured this is NOT a latency knob, so keep it small.
        var drainBatchEvents = 512
        /// Rotation size and retained generations: a 64 MiB hard cap (brief ruling 7).
        var maxFileBytes = 8_388_608
        var keptFiles = 8
        var bufferBytes = 65_536
        /// In-game window.
        var viewEvents = 512
        /// Drain timer interval; 0 means no timer (`.synchronous`/`.off` never build one).
        var drainInterval: TimeInterval = 0.25
        /// Heartbeat period in fixed steps: 600 ticks = 10 s, the only periodic record.
        var heartbeatSteps = 600
    }

    struct Configuration: Equatable {
        var mode: GameplayEventWriterMode = .off
        var level: Int = 0
        var directoryPath: String = ""
        var filePrefix = "gameplay-"
        var build: String = "harness"
        var seed: String = "nondeterministic"
        var limits = Limits()
        var runToken: String?

        /// Pure environment resolution, kept away from `ProcessInfo` so the Linux gate can run the
        /// exact shipped rules. `EXOLON_EVENT_LOG=off|<level>|<path>`; the default level comes from
        /// the build configuration: Debug = 1, Release = 0 (off), tests = 2 (brief ruling 2, 5).
        static func resolved(environment: [String: String],
                             defaultLevel: Int,
                             temporaryDirectory: String,
                             build: String) -> Configuration {
            var configuration = Configuration()
            configuration.build = build
            configuration.directoryPath = GameplayEventLog.defaultDirectoryPath(temporaryDirectory: temporaryDirectory)
            let requested = environment["EXOLON_EVENT_LOG"] ?? ""
            let value = requested.trimmingCharacters(in: .whitespaces)

            if value.isEmpty {
                configuration.level = max(0, min(2, defaultLevel))
                configuration.mode = configuration.level > 0 ? .asynchronous : .off
                return configuration
            }
            if value == "off" {
                configuration.mode = .off
                configuration.level = 0
                return configuration
            }
            if let level = Int(value) {
                configuration.level = max(0, min(2, level))
                configuration.mode = .asynchronous
                return configuration
            }
            // A value that is not `off` and not a level is the directory override.
            configuration.level = defaultLevel > 0 ? max(0, min(2, defaultLevel)) : 1
            configuration.mode = .asynchronous
            configuration.directoryPath = value.hasPrefix("/") ? value : "\(temporaryDirectory)/\(value)"
            return configuration
        }
    }

    static func defaultDirectoryPath(temporaryDirectory: String) -> String {
        "\(temporaryDirectory)/exolon"
    }

    /// Producer-side counters. `events` counts records the game appended; writer-built records
    /// (`log.begin`/`log.rotate`/`log.events_dropped`/`log.end`) carry their own `seq` and are not
    /// counted here, which is what makes "declared events minus written body records == dropped" the
    /// check for a lost record.
    var stats: (events: Int, pending: Int, dropped: Int) {
        lock.lock()
        defer { lock.unlock() }
        return (appendedTotal, pending, droppedTotal)
    }

    /// `seq` numbers issued so far, including writer-built records.
    var seqsIssued: Int {
        lock.lock()
        defer { lock.unlock() }
        return nextSeq
    }

    private let lock = NSLock()
    private let limits: Limits
    private let mode: GameplayEventWriterMode
    private let level: Int
    private let writer: GameplayEventWriter
    private let runToken: String
    private let buildIdentifier: String
    private let seedIdentifier: String

    private var ring: [GameplayEvent]
    private let mask: Int
    private var head = 0
    private var tail = 0
    private var pending = 0
    private var droppedTotal = 0
    private var droppedSinceDrain = 0
    private var appendedTotal = 0

    private var tickValue: UInt32 = 0
    private var frameValue: UInt32 = 0
    private var zoneValue: UInt16 = 0
    private var flowValue: UInt16 = 0

    // Drain-side state. A single writer assigns `seq`, which is what makes the stream a total order.
    private var nextSeq = 0
    private var fileIsOpen = false
    private var openFailed = false
    private var isShutDown = false
    private var wantsInlineDrain = false
    private var scratch: [GameplayEvent]
    /// Reused JSON batch buffer of the drain, so formatting does not allocate a fresh String per
    /// drain cycle.
    private var drainBuffer = ""

    private var drainQueue: DispatchQueue?
    private var drainTimer: DispatchSourceTimer?
    private static let queueKey = DispatchSpecificKey<Bool>()

    /// Process-shared, RFC 3339 UTC formatter for `log.begin` only - used exclusively on the drain
    /// thread (`Foundation.Formatter` is not thread-safe; one log per process is the shipped shape).
    private static let timestampFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"
        return formatter
    }()

    init(configuration: Configuration, writer: GameplayEventWriter) {
        let capacity = max(16, GameplayEventLog.roundedPowerOfTwo(configuration.limits.ringCapacity))
        self.limits = configuration.limits
        self.mode = configuration.mode
        self.level = max(0, min(2, configuration.level))
        self.writer = writer
        self.runToken = configuration.runToken ?? GameplayEventLog.makeRunToken()
        self.buildIdentifier = configuration.build
        self.seedIdentifier = configuration.seed
        self.mask = capacity - 1
        self.ring = [GameplayEvent](repeating: GameplayEvent.zero, count: capacity)
        self.scratch = [GameplayEvent]()
        self.scratch.reserveCapacity(configuration.limits.drainBatchEvents)

        if mode == .asynchronous {
            let queue = DispatchQueue(label: "com.exolon.gameplay-event-log", qos: .utility)
            queue.setSpecific(key: GameplayEventLog.queueKey, value: true)
            drainQueue = queue
            if self.limits.drainInterval > 0 {
                let timer = DispatchSource.makeTimerSource(queue: queue)
                timer.schedule(deadline: .now() + self.limits.drainInterval, repeating: self.limits.drainInterval)
                // The handler runs ON the queue; routing it through the `queue.sync` wrapper
                // deadlocked the prototype (architect section 2.1/2).
                timer.setEventHandler { [weak self] in self?.drainNow() }
                drainTimer = timer
                timer.resume()
            }
        }
    }

    /// Builds the production writer for this configuration (a file writer outside the clone).
    convenience init(configuration: Configuration) {
        let limits = configuration.limits
        let token = configuration.runToken ?? GameplayEventLog.makeRunToken()
        var resolved = configuration
        resolved.runToken = token
        let writer = GameplayEventFileWriter(directoryPath: configuration.directoryPath,
                                             filePrefix: configuration.filePrefix,
                                             runToken: token,
                                             maxFileBytes: limits.maxFileBytes,
                                             keptFiles: limits.keptFiles,
                                             bufferBytes: limits.bufferBytes)
        self.init(configuration: resolved, writer: writer)
    }

    deinit {
        drainTimer?.cancel()
    }

    // MARK: Sink surface

    var isRecording: Bool { mode != .off }
    var emissionLevel: Int { level }

    var tick: UInt32 {
        lock.lock()
        defer { lock.unlock() }
        return tickValue
    }

    var frame: UInt32 {
        lock.lock()
        defer { lock.unlock() }
        return frameValue
    }

    var zone: UInt16 {
        lock.lock()
        defer { lock.unlock() }
        return zoneValue
    }

    /// Kept in step with the scene's `state.flow` so `log.begin`/`tick.heartbeat` can name the
    /// current flow state without a producer-path string.
    var flowStateCode: UInt16 {
        lock.lock()
        defer { lock.unlock() }
        return flowValue
    }

    var flowStateLabel: String { GameplayWire.flowLabel(flowStateCode) }

    func setFlowState(_ state: GameFlowState) {
        lock.lock()
        flowValue = GameplayWire.code(state)
        lock.unlock()
    }

    /// Hot path: one locked append of a 24-byte record. No String, no collection, no closure, no I/O.
    func emit(_ kind: GameplayEventKind, entity: UInt16, _ a: Int16, _ b: Int16, _ c: Int16, _ d: Int16) {
        if level < kind.minimumLevel { return }
        appendRecord(kind.rawValue, entity, a, b, c, d)
    }

    /// Contract seam used by the Linux gate to prove an unassigned raw value formats as
    /// `unknown<N>` instead of aliasing a real name (INV-003). Product code always goes through
    /// `emit(_:entity:_:_:_:_:)`; this is the identical append with the enum lookup removed.
    func appendRawKind(_ rawKind: UInt8, entity: UInt16, _ a: Int16, _ b: Int16, _ c: Int16, _ d: Int16) {
        appendRecord(rawKind, entity, a, b, c, d)
    }

    private func appendRecord(_ rawKind: UInt8, _ entity: UInt16, _ a: Int16, _ b: Int16, _ c: Int16, _ d: Int16) {
        lock.lock()
        appendedTotal += 1
        let record = GameplayEvent(tick: tickValue,
                                   frame: frameValue,
                                   zone: zoneValue,
                                   entity: entity,
                                   kind: rawKind,
                                   a: a, b: b, c: c, d: d)
        storeLocked(record)
        let drainInline = wantsInlineDrain
        wantsInlineDrain = false
        lock.unlock()
        if drainInline { drainNow() }
    }

    func beginFrame() {
        lock.lock()
        frameValue = frameValue &+ 1
        lock.unlock()
    }

    /// The only mutator of the tick counter. The first executed fixed step is tick **1** - an
    /// off-by-one there was a live prototype bug (architect section 2.1/3) - and the counter is
    /// process-global: nothing in this type ever resets it.
    func beginTick(zone: Int) {
        lock.lock()
        zoneValue = UInt16(truncatingIfNeeded: max(0, min(65_535, zone)))
        tickValue = tickValue &+ 1
        if limits.heartbeatSteps > 0, tickValue % UInt32(limits.heartbeatSteps) == 0 {
            appendHeartbeatLocked()
        }
        lock.unlock()
    }

    /// Last `n` records; serves the in-game view and never blocks on I/O.
    func view(_ n: Int?) -> [GameplayEvent] {
        let wanted = max(1, min(n ?? limits.viewEvents, limits.viewEvents))
        lock.lock()
        defer { lock.unlock() }
        let available = min(pending, wanted)
        var result = [GameplayEvent]()
        result.reserveCapacity(available)
        var index = tail - available
        for _ in 0..<available {
            result.append(ring[index & mask])
            index += 1
        }
        return result
    }

    /// Rendered tail of the ring for the F1 overlay: the same records, the same wire format
    /// (integration section 11-4 - never a second, cheaper format). Allocation here is fine:
    /// the overlay is throttled to every 10th rendered frame and gated on `showHitboxes`.
    func describe(_ n: Int?) -> [String] {
        view(n).map { formatRecord($0, seq: nil) }
    }

    // MARK: Drain control

    /// Cross-thread drain request. Safe from any thread; the timer uses `drainNow` directly.
    func requestDrain() {
        guard mode == .asynchronous, let queue = drainQueue else { return }
        queue.async { [weak self] in self?.drainNow() }
    }

    /// Barrier: **everything** appended so far is handed to the writer. One `drainNow()` covers a
    /// single batch, so the barrier loops until the ring is empty - otherwise `shutdown()` could
    /// write `log.end` over records still sitting in the ring (caught by the async scenario:
    /// 23 232 records stayed behind after a "flush").
    func flush() {
        switch mode {
        case .off:
            return
        case .synchronous:
            drainEverything()
            writer.synchronize()
        case .asynchronous:
            guard let queue = drainQueue else { return }
            if DispatchQueue.getSpecific(key: GameplayEventLog.queueKey) == true {
                // Already on the drain queue: routing through the sync wrapper here is exactly the
                // prototype deadlock (architect section 2.1/2).
                drainEverything()
                writer.synchronize()
            } else {
                queue.sync {
                    self.drainEverything()
                    self.writer.synchronize()
                }
            }
        }
    }

    private func hasPendingWork() -> Bool {
        lock.lock()
        defer { lock.unlock() }
        return pending > 0 || droppedSinceDrain > 0
    }

    /// Drains batch by batch until the ring is empty. Bounded by the ring capacity and the batch
    /// size, so it terminates: every pass advances `head`.
    private func drainEverything() {
        while hasPendingWork() {
            drainNow()
        }
    }

    /// Writes `log.end`, closes the file and stops the timer. One-step kill switch partner.
    /// The reason is the declared enum, not a free-form string: `reason` is an enum field.
    func shutdown(reason: GameplayLogEndReason = .appQuit) {
        drainTimer?.cancel()
        drainTimer = nil
        lock.lock()
        let alreadyClosed = isShutDown
        let events = appendedTotal
        let lastTick = Int(tickValue)
        let lastFrame = Int(frameValue)
        lock.unlock()
        guard !alreadyClosed, mode != .off else { return }

        // Drain first: everything appended must reach the file before the terminal record.
        flush()
        lock.lock()
        isShutDown = true
        lock.unlock()
        let closer: () -> Void = {
            guard self.ensureFileOpen(stampTick: lastTick, stampFrame: lastFrame) else { return }
            var line = Line()
            line.envelope(schemaVersion: 1, seq: self.nextSeq, tick: lastTick, frame: lastFrame,
                          rot: self.writer.rotationIndex, name: GameplayEventKind.logEnd.label)
            line.string("reason", reason.label)
            line.number("events", events)
            self.nextSeq += 1
            self.writer.write(line.finish())
            self.writer.synchronize()
            self.writer.closeFile()
        }
        if let queue = drainQueue {
            if DispatchQueue.getSpecific(key: GameplayEventLog.queueKey) == true { closer() } else { queue.sync(execute: closer) }
        } else {
            closer()
        }
    }

    // MARK: Ring

    private func storeLocked(_ record: GameplayEvent) {
        if pending >= ring.count {
            // The ring lapped: keep the newest, count the loss, make it visible at the drain.
            head += 1
            pending -= 1
            droppedTotal += 1
            droppedSinceDrain += 1
        }
        ring[tail & mask] = record
        tail += 1
        pending += 1
        if mode == .synchronous, pending >= limits.drainBatchEvents {
            wantsInlineDrain = true
        }
    }

    /// Appends `tick.heartbeat` without re-entering the lock (`NSLock` is not recursive).
    private func appendHeartbeatLocked() {
        let eventsSplit = GameplayEvent.split(Int32(truncatingIfNeeded: appendedTotal))
        let dropsSplit = GameplayEvent.split(Int32(truncatingIfNeeded: droppedTotal))
        appendedTotal += 1
        let record = GameplayEvent(tick: tickValue,
                                   frame: frameValue,
                                   zone: zoneValue,
                                   entity: flowValue,
                                   kind: GameplayEventKind.tickHeartbeat.rawValue,
                                   a: eventsSplit.0, b: eventsSplit.1,
                                   c: dropsSplit.0, d: dropsSplit.1)
        if pending >= ring.count {
            head += 1
            pending -= 1
            droppedTotal += 1
            droppedSinceDrain += 1
        }
        ring[tail & mask] = record
        tail += 1
        pending += 1
    }

    // MARK: Drain (one writer, so seq is a total order)

    private func drainNow() {
        guard mode != .off else { return }
        lock.lock()
        if isShutDown {
            lock.unlock()
            return
        }
        let batch = min(pending, limits.drainBatchEvents)
        // Only claim the loss window when this drain can actually declare it (the drop record is
        // written immediately before the batch it brackets); otherwise it stays pending.
        let drops = batch > 0 ? droppedSinceDrain : 0
        droppedSinceDrain -= drops
        scratch.removeAll(keepingCapacity: true)
        var index = head
        for _ in 0..<batch {
            scratch.append(ring[index & mask])
            index += 1
        }
        head = index
        pending -= batch
        let headRecordTick = scratch.first?.tick ?? tickValue
        let headRecordFrame = scratch.first?.frame ?? frameValue
        lock.unlock()

        if batch == 0 && drops == 0 { return }
        if !ensureFileOpen(stampTick: Int(headRecordTick), stampFrame: Int(headRecordFrame)) {
            // Nothing can reach a file that cannot be opened. Count the loss instead of pretending:
            // an operator sees the stderr line, a test sees the counter.
            lock.lock()
            droppedTotal += batch
            lock.unlock()
            return
        }

        // Boundary records are stamped from the batch that follows them: `tick` and `frame` are
        // non-decreasing along a file (INV-001), and a header written at open time would otherwise
        // carry a later tick than the records it precedes.
        let stampTick = Int(headRecordTick)
        let stampFrame = Int(headRecordFrame)
        // Rotation is decided per batch, before any of it is numbered: measuring each line's byte
        // length rescans the block (the cost probe's biggest line item), and numbering first would
        // give the new file's header a lower `seq` than the records that follow it. The retired file
        // therefore ends at 8 MiB plus at most one batch, and still ends with its own log.rotate.
        if writer.bytesInCurrentFile >= limits.maxFileBytes {
            rotateFile(tick: stampTick, frame: stampFrame)
        }
        var output = drainBuffer
        output.removeAll(keepingCapacity: true)
        var wantsSync = false
        if drops > 0, batch > 0 {
            // `seq` is assigned by this writer, so the file stays dense and the loss window is
            // bracketed instead: `last_seq` is the record written immediately before the loss and
            // `first_seq` the one written immediately after this line. Both name real records, so a
            // consumer locates the hole without trusting a number that was never issued.
            output += dropRecordLine(drops: drops, lastRetainedSeq: nextSeq - 1, firstRetainedSeq: nextSeq + 1,
                                     tick: stampTick, frame: stampFrame)
            wantsSync = true
        }
        for record in scratch {
            output += formatRecord(record, seq: nextSeq)
            nextSeq += 1
            if shouldFlush(record) { wantsSync = true }
        }
        writer.write(output)
        if wantsSync { writer.synchronize() }
        drainBuffer = output
    }

    /// Flush policy (brief ruling 7): every 60th tick and on any state/damage/bonus/tick record.
    private func shouldFlush(_ record: GameplayEvent) -> Bool {
        if shouldFlushRecord(record) { return true }
        return record.tick % 60 == 0
    }

    /// Family membership without any substring allocation: `family` is derived from the same
    /// exhaustive switch, so a new kind lands in exactly one of these branches.
    private func shouldFlushRecord(_ record: GameplayEvent) -> Bool {
        guard let kind = GameplayEventKind(rawValue: record.kind) else { return false }
        switch kind {
        case .logBegin, .logRotate, .logEventsDropped, .logEnd,
             .stateFlow, .stateZoneLoad, .stateZoneLoaded, .stateZoneExit, .stateZoneTransition,
             .stateContentComplete, .stateTitleEnter, .stateCheckpointSaved, .stateCheckpointCleared,
             .statePauseEnter, .statePauseExit, .stateRestart, .stateCheatInvulnerability,
             .tickFrameGapClamped, .tickAccumulatorReset, .tickSlowStep, .tickHeartbeat,
             .damagePlayerBlocked, .damagePlayerHit,
             .bonusDoubleLauncher, .bonusStagePoints, .bonusStageComponent, .bonusStageBoundarySuppressed,
             .gameGameOver:
            return true
        case .inputActionEdge, .inputPauseConsumed, .inputContextualConsumed,
             .playerMotion, .playerJump, .playerLand, .playerCrouchBegin, .playerCrouchEnd,
             .playerExoskeleton, .playerShootBlaster, .playerShootDenied, .playerThrowGrenade,
             .playerTeleport, .playerDeathBegin, .playerDeathLanded, .playerDeathSettled,
             .pickupCollect, .scoreAwarded, .scoreHighScoreSaved, .entityLauncherFire:
            return false
        }
    }

    private func ensureFileOpen(stampTick: Int, stampFrame: Int) -> Bool {
        if openFailed { return false }
        if fileIsOpen { return true }
        guard mode != .off else { return false }
        guard writer.openFirstFile() else {
            openFailed = true
            reportOnce("gameplay event log: cannot write \(writer.currentPath); emission disabled")
            return false
        }
        fileIsOpen = true
        // A human must know what to `tail -f` (integration section 7).
        reportOnce("gameplay event log: \(writer.currentPath)")
        let rotation = writer.rotationIndex
        outputAppend(beginRecordLine(rotation: rotation, path: writer.currentPath,
                                     tick: stampTick, frame: stampFrame))
        return true
    }

    private func outputAppend(_ line: String) {
        writer.write(line)
        writer.synchronize()
    }

    /// Ends the retired file with its own `log.rotate` (`x-encode`: "last line of the file being
    /// retired") so a consumer holding only that file can tell a rotation from a truncation, then
    /// opens the successor and writes its header. Payload `rot` names the incoming generation.
    private func rotateFile(tick: Int, frame: Int) {
        let retired = writer.rotationIndex
        let fromPath = writer.currentPath
        let toPath = writer.nextFilePath()
        var line = Line()
        line.envelope(schemaVersion: 1, seq: nextSeq, tick: tick, frame: frame, rot: retired,
                      name: GameplayEventKind.logRotate.label)
        line.string("from_path", fromPath)
        line.string("to_path", toPath)
        line.number("rot", retired + 1)
        line.number("rotated_at_tick", tick)
        nextSeq += 1
        writer.write(line.finish())
        writer.synchronize()
        guard writer.rotateToNextFile() else {
            openFailed = true
            reportOnce("gameplay event log: rotation failed; emission disabled")
            return
        }
        fileIsOpen = true
        outputAppend(beginRecordLine(rotation: writer.rotationIndex, path: writer.currentPath,
                                     tick: tick, frame: frame))
    }

    private func beginRecordLine(rotation: Int, path: String, tick: Int, frame: Int) -> String {
        var line = Line()
        line.envelope(schemaVersion: 1, seq: nextSeq, tick: tick, frame: frame, rot: rotation,
                      name: GameplayEventKind.logBegin.label)
        line.string("run_id", runToken)
        line.string("build", buildIdentifier)
        line.string("wall_utc", GameplayEventLog.timestampFormatter.string(from: Date()))
        line.number("level", level)
        line.string("path", path)
        line.string("seed", seedIdentifier)
        line.number("zone", 0)
        line.string("flow_state", flowStateLabel)
        nextSeq += 1
        return line.finish()
    }

    private func dropRecordLine(drops: Int, lastRetainedSeq: Int, firstRetainedSeq: Int,
                                tick: Int, frame: Int) -> String {
        var line = Line()
        line.envelope(schemaVersion: 1, seq: nextSeq, tick: tick, frame: frame,
                      rot: writer.rotationIndex, name: GameplayEventKind.logEventsDropped.label)
        line.number("count", drops)
        line.number("first_seq", max(0, firstRetainedSeq))
        line.number("last_seq", max(0, lastRetainedSeq))
        line.number("total_dropped", droppedTotal)
        line.number("ring_capacity", ring.count)
        line.string("marker", "# dropped \(drops) oldest events (writer behind)")
        nextSeq += 1
        return line.finish()
    }

    private func reportOnce(_ message: String) {
        lock.lock()
        let alreadyReported = hasReportedFailure
        hasReportedFailure = true
        lock.unlock()
        guard !alreadyReported else { return }
        // Diagnostics about the log itself must never throw or block gameplay.
        FileHandle.standardError.write(Data("exolon: \(message)\n".utf8))
    }

    private var hasReportedFailure = false

    // MARK: Formatting (drain path: strings live here and nowhere else)

    /// Streaming JSON member builder.
    ///
    /// Every method appends with plain `+=` and `String(value)` on purpose: `"\(value)"` for an
    /// `Int` goes through the generic `appendInterpolation` and can box the operand, which the cost
    /// probe measured at ~100 ns per field - the single biggest line item of the format path.
    struct Line {
        var text = ""

        mutating func reserve(_ wanted: Int) {
            if text.utf8.count == 0 { text.reserveCapacity(wanted) }
        }

        mutating func key(_ name: String) {
            text += ",\""
            text += name
            text += "\":"
        }

        mutating func number(_ name: String, _ value: Int) {
            key(name)
            text += String(value)
        }

        mutating func flag(_ name: String, _ value: Bool) {
            key(name)
            text += value ? "true" : "false"
        }

        /// Whitelisted lowercase-ASCII label: no free text reaches this path, so no escaping.
        mutating func label(_ name: String, _ value: String) {
            key(name)
            text += "\""; text += value; text += "\""
        }

        /// The exempt free-form fields (run_id, build, wall_utc, path, seed) only.
        mutating func string(_ name: String, _ value: String) {
            key(name)
            text += GameplayEventLog.escapedJSONString(value)
        }

        mutating func point(_ name: String, _ x: Int, _ y: Int) {
            key(name)
            text += "{\"x\":"
            text += String(x)
            text += ",\"y\":"
            text += String(y)
            text += "}"
        }

        /// Envelope, in the normative key order (integration section 4).
        mutating func envelope(schemaVersion: Int, seq: Int, tick: Int, frame: Int, rot: Int, name: String) {
            reserve(192)
            text += "{\"schema_version\":"
            text += String(schemaVersion)
            text += ",\"seq\":"
            text += String(seq)
            text += ",\"tick\":"
            text += String(tick)
            text += ",\"frame\":"
            text += String(frame)
            text += ",\"rot\":"
            text += String(rot)
            text += ",\"ts_us\":"
            text += String(GameplayEvent.microseconds(fromSteps: tick))
            text += ",\"name\":\""
            text += name
            text += "\""
        }

        func finish() -> String {
            var closed = text
            closed += "}\n"
            return closed
        }
    }

    /// One record -> one JSON line, payload keys in the frozen order.
    private func formatRecord(_ record: GameplayEvent, seq: Int?) -> String {
        var line = Line()
        let name = GameplayEventKind.names[record.kind] ?? "unknown\(record.kind)"
        line.envelope(schemaVersion: 1, seq: seq ?? nextSeq, tick: Int(record.tick),
                      frame: Int(record.frame), rot: writer.rotationIndex, name: name)
        if let kind = GameplayEventKind(rawValue: record.kind) {
            appendPayload(&line, kind: kind, record: record)
        }
        return line.finish()
    }

    /// Exhaustive over the catalog: no `default:`, so a new case must declare its payload here
    /// exactly as `x-encode` in the frozen schema declares its lanes.
    private func appendPayload(_ line: inout Line, kind: GameplayEventKind, record: GameplayEvent) {
        let zone = Int(record.zone)
        let subject = record.entity
        let a = Int(record.a)
        let b = Int(record.b)
        let c = Int(record.c)
        let d = Int(record.d)
        switch kind {
        case .logBegin, .logRotate, .logEventsDropped, .logEnd:
            // Written by this type with its own fields, never by the producer path.
            break
        case .inputActionEdge:
            line.label("action", GameplayWire.actionLabel(subject & 0b11_1111))
            line.flag("pressed", record.b != 0)
            line.label("source", GameplayWire.sourceLabel((subject >> 6) & 0b11))
            line.number("held_us", a * 1_000)
        case .inputPauseConsumed:
            line.flag("pending", record.a != 0)
        case .inputContextualConsumed:
            line.label("kind", GameplayWire.contextualLabel(subject))
            line.flag("jump_suppressed", record.a != 0)
        case .playerMotion:
            line.number("zone", zone)
            line.number("x", a)
            line.number("y", b)
            line.number("vx", c)
            line.number("vy", d)
            line.flag("grounded", (subject >> 3) & 1 != 0)
            line.label("motion_state", GameplayWire.motionLabel(subject & 0b111))
            line.label("facing", GameplayWire.facingLabel((subject >> 4) & 1))
            line.flag("exoskeleton", (subject >> 5) & 1 != 0)
        case .playerJump:
            line.number("x", a)
            line.number("y", b)
            line.number("velocity", c)
            line.flag("grounded_before", subject & 1 != 0)
            line.flag("after_teleport", (subject >> 1) & 1 != 0)
        case .playerLand:
            line.number("x", a)
            line.number("y", b)
            line.number("vy_before", c)
            line.label("support", GameplayWire.supportLabel(subject))
        case .playerCrouchBegin, .playerCrouchEnd:
            line.number("x", a)
            line.number("y", b)
        case .playerExoskeleton:
            line.flag("enabled", record.a != 0)
            line.label("cause", GameplayWire.exoskeletonCauseLabel(subject))
        case .playerShootBlaster:
            line.number("x", a)
            line.number("y", b)
            line.label("facing", GameplayWire.facingLabel(subject & 1))
            line.flag("double", (subject >> 1) & 1 != 0)
            line.number("ammo_before", c)
            line.number("ammo_after", d)
        case .playerShootDenied:
            line.label("reason", GameplayWire.shootDeniedReasonLabel(subject))
            line.number("ammo", a)
        case .playerThrowGrenade:
            line.number("x", a)
            line.number("y", b)
            line.label("direction", GameplayWire.facingLabel(subject & 1))
            line.number("grenades_before", c)
            line.number("grenades_after", d)
            line.label("blocked_by", ((subject >> 1) & 1) != 0 ? "one_in_flight" : "none")
        case .playerTeleport:
            line.point("from", a, b)
            line.point("to", c, d)
            line.number("portal_index", Int(subject & 0xFF))
            line.flag("jump_latch_held", ((subject >> 8) & 1) != 0)
        case .playerDeathBegin:
            line.number("x", a)
            line.number("y", b)
            line.number("lives", c)
            line.number("ammo", d)
            line.number("grenades", Int(subject))
        case .playerDeathLanded:
            line.number("x", a)
            line.number("y", b)
            line.number("ground_ticks", c)
        case .playerDeathSettled:
            line.number("delay_us", GameplayEvent.microseconds(fromSteps: d))
            line.number("lives_before", a)
            line.number("lives_after", b)
            line.number("invulnerability_us", GameplayEvent.microseconds(fromSteps: c))
            line.flag("checkpoint_saved", subject & 1 != 0)
        case .gameGameOver:
            line.number("points", Int(GameplayEvent.join(high: record.a, low: record.b)))
            line.number("high_score", Int(GameplayEvent.join(high: record.c, low: record.d)))
            line.number("zone", zone)
            line.flag("checkpoint_cleared", subject & 1 != 0)
        case .damagePlayerBlocked:
            // cause + test_invulnerability live in lane c, exactly as the producer helper packs
            // them and as `x-encode` declares; the subject lane is unused by this record.
            let packed = GameplayEvent.word(record.c)
            line.label("cause", GameplayWire.damageCauseLabel(packed & 0b11_1111))
            line.number("invulnerability_us", Int(GameplayEvent.join(high: record.a, low: record.b)))
            line.flag("test_invulnerability", ((packed >> 6) & 1) != 0)
        case .damagePlayerHit:
            line.label("cause", GameplayWire.damageCauseLabel(GameplayEvent.word(record.c) & 0b11_1111))
            line.number("x", a)
            line.number("y", b)
            line.label("flow_state_before", GameplayWire.flowLabel((GameplayEvent.word(record.c) >> 6) & 0b111))
            line.label("flow_state_after", GameplayWire.flowLabel((GameplayEvent.word(record.c) >> 9) & 0b111))
            line.number("lives", d)
        case .pickupCollect:
            line.label("kind", GameplayWire.pickupKindLabel(subject))
            line.number("count_before", c)
            line.number("count_after", d)
            line.number("x", a)
            line.number("y", b)
        case .bonusDoubleLauncher:
            line.number("points", a)
            line.number("completed_zone", zone)
            line.string("launcher_object_id", String(subject))
            line.number("x", b)
            line.number("y", c)
            line.flag("launcher_active_after", record.d != 0)
        case .bonusStagePoints:
            // Wave A freezes one component (lives x 1000); `bonus.stage_component` carries the
            // breakdown so a later wave can extend the total without touching this seam.
            line.number("completed_zone", zone)
            line.number("points", Int(GameplayEvent.join(high: record.a, low: record.b)))
            line.number("lives_before", Int(subject & 0b1111))
            line.number("lives_after", Int((subject >> 4) & 0b1111))
            line.flag("ammo_reset", ((subject >> 8) & 1) != 0)
        case .bonusStageComponent:
            line.number("completed_zone", zone)
            line.label("component_id", GameplayWire.stageComponentLabel(subject))
            line.number("points", a)
        case .bonusStageBoundarySuppressed:
            line.number("completed_zone", zone)
            line.label("reason", GameplayWire.stageSuppressionReasonLabel(subject))
        case .scoreAwarded:
            // points_after/clamped are the same arithmetic the product performs in awardPoints.
            let before = Int(GameplayEvent.join(high: record.b, low: record.c))
            line.number("points", a)
            line.label("reason", GameplayWire.scoreReasonLabel(subject))
            line.number("points_before", before)
            line.number("points_after", min(999_999, before + a))
            line.flag("clamped", before + a > 999_999)
        case .scoreHighScoreSaved:
            line.number("value", Int(GameplayEvent.join(high: record.a, low: record.b)))
        case .stateFlow:
            line.label("from", GameplayWire.flowLabel(GameplayEvent.word(record.a)))
            line.label("to", GameplayWire.flowLabel(GameplayEvent.word(record.b)))
            line.label("cause", GameplayWire.flowCauseLabel(GameplayEvent.word(record.c)))
        case .stateZoneLoad:
            line.string("resource", GameplayWire.resource(for: record.zone))
            line.number("zone", zone)
            line.label("cause", GameplayWire.zoneLoadCauseLabel(subject))
        case .stateZoneLoaded:
            line.string("resource", GameplayWire.resource(for: record.zone))
            line.number("zone", zone)
            line.number("solid_count", a)
            line.number("spawn_x", b)
            line.number("spawn_y", c)
            line.number("ground_y", d)
            line.number("invulnerability_us", GameplayEvent.microseconds(fromSteps: Int(subject & 0b1_1111_1111)))
            line.flag("carried_y", ((subject >> 9) & 1) != 0)
        case .stateZoneExit:
            // `next_level` is derived from the zone lane (zone+1 -> L..S..), which is how every
            // shipped map numbers its successor; the producer carries only the "playable next" bit.
            line.number("zone", zone)
            line.number("trigger_x", a)
            line.number("player_x", b)
            line.string("next_level", subject != 0 ? GameplayWire.resource(for: UInt16(zone + 1)) : "")
        case .stateZoneTransition:
            line.number("from_zone", zone)
            line.number("to_zone", Int(subject))
            line.number("accumulator_us", Int(GameplayEvent.join(high: record.a, low: record.b)))
            line.number("pending_steps", c)
        case .stateContentComplete:
            line.number("zone", zone)
            line.string("next_level", ((subject >> 1) & 1) != 0 ? GameplayWire.resource(for: UInt16(zone + 1)) : "")
            line.number("points", Int(GameplayEvent.join(high: record.a, low: record.b)))
            line.flag("final", (subject & 1) != 0)
        case .stateTitleEnter:
            line.number("high_score", Int(GameplayEvent.join(high: record.a, low: record.b)))
            line.flag("has_saved_checkpoint", subject & 1 != 0)
        case .stateCheckpointSaved:
            line.string("resource", GameplayWire.resource(for: record.zone))
            line.number("ammo", Int(subject & 0b111_1111))
            line.number("grenades", Int((subject >> 7) & 0b11111))
            line.number("points", Int(GameplayEvent.join(high: record.b, low: record.c)))
            line.number("lives", Int((subject >> 12) & 0b1111))
        case .stateCheckpointCleared:
            line.label("reason", GameplayWire.checkpointClearedReasonLabel(subject))
        case .statePauseEnter, .statePauseExit:
            line.label("state_before", GameplayWire.flowLabel(GameplayEvent.word(record.a)))
            line.number("selected_index", b)
        case .stateRestart:
            line.number("from_zone", zone)
            line.number("points", Int(GameplayEvent.join(high: record.a, low: record.b)))
        case .stateCheatInvulnerability:
            line.flag("enabled", record.a != 0)
            line.number("menu_index", b)
        case .tickFrameGapClamped:
            let raw = Int(GameplayEvent.join(high: record.a, low: record.b))
            line.number("raw_frame_time_us", raw)
            line.number("clamp_us", 250_000)
            line.number("lost_us", max(0, raw - 250_000))
        case .tickAccumulatorReset:
            line.label("reason", GameplayWire.accumulatorResetReasonLabel(subject))
            line.number("discarded_us", Int(GameplayEvent.join(high: record.a, low: record.b)))
            line.number("discarded_steps", c)
        case .tickSlowStep:
            line.number("step_us", Int(GameplayEvent.join(high: record.a, low: record.b)))
            line.number("budget_us", 16_667)
            line.number("steps_this_frame", c)
        case .tickHeartbeat:
            line.number("uptime_us", GameplayEvent.microseconds(fromSteps: Int(record.tick)))
            line.number("events", Int(GameplayEvent.join(high: record.a, low: record.b)))
            line.number("drops", Int(GameplayEvent.join(high: record.c, low: record.d)))
            line.number("zone", zone)
            // The flow code travels inside the record (subject lane), so a heartbeat drained
            // shortly after a flow change still names the state it was emitted in.
            line.label("flow_state", GameplayWire.flowLabel(subject))
        case .entityLauncherFire:
            line.string("object_id", String(subject))
            line.label("kind", "double_launcher")
            line.number("x", a)
            line.number("y", b)
            line.number("muzzle_y", c)
        }
    }

    // MARK: Small helpers

    static func roundedPowerOfTwo(_ wanted: Int) -> Int {
        var candidate = 16
        while candidate < max(16, wanted) { candidate <<= 1 }
        return candidate
    }

    /// Escaping for the exempt free-form fields only; labels never pass through here.
    static func escapedJSONString(_ value: String) -> String {
        var escaped = "\""
        escaped.reserveCapacity(value.utf8.count + 8)
        for scalar in value.unicodeScalars {
            switch scalar {
            case "\"": escaped += "\\\""
            case "\\": escaped += "\\\\"
            case "\n": escaped += "\\n"
            case "\r": escaped += "\\r"
            case "\t": escaped += "\\t"
            default:
                if scalar.value < 0x20 {
                    escaped += String(format: "\\u%04x", Int(scalar.value))
                } else {
                    escaped.unicodeScalars.append(scalar)
                }
            }
        }
        return escaped + "\""
    }

    static func makeRunToken() -> String {
        String(format: "%016llx", UInt64.random(in: 1 ... .max))
    }
}
