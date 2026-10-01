/**
 * FBSDK — Facebook Gaming SDK wrapper (SDK 8.0+ compatible)
 * Abstracts FB Instant Games API behind a testable interface.
 *
 * When running inside a Facebook Instant Games iframe,
 * globalThis.FBInstant is available and all API calls proceed to the real SDK.
 * When running locally (no Facebook iframe), a stub mode allows the game
 * to launch and be tested without requiring Facebook credentials.
 *
 * Key API changes in SDK 8.0+:
 * - player.getName() and player.getPhoto() removed (return null)
 * - globalThis.FBInstant instead of window.FBInstant
 * - getSDKVersion() available for version checking
 * - shareAsync uses intent: 'SHARE' (uppercase)
 */

export interface FBPlayer {
  playerID: string;
  name: string | null;
  pictureURL: string | null;
}

export interface FBLeaderboardEntry {
  playerID: string;
  score: number;
  rank: number;
}

export interface FBSharePayload {
  intent: 'SHARE' | 'REQUEST' | 'SEND' | 'INVITE';
  image?: string;     // base64 data URL for SHARE
  text?: string;
  data?: Record<string, unknown>;
}

export interface FBSDK {
  readonly initialized: boolean;
  readonly sdkVersion: string | null;
  initialize(): Promise<void>;
  startGame(): Promise<void>;
  getPlayer(): Promise<FBPlayer>;
  setScore(leaderboardID: string, score: number): Promise<void>;
  getLeaderboard(leaderboardID: string): Promise<FBLeaderboardEntry[]>;
  getConnectedPlayers(): Promise<FBPlayer[]>;
  share(payload: FBSharePayload): Promise<void>;
  canCreateShortcut(): Promise<boolean>;
  createShortcut(): Promise<void>;
  switchGame(appID: string): Promise<void>;
  setLoadingProgress(progress: number): void;
  subscribeBot(): Promise<void>;
}

// Extend globalThis for FBInstant SDK
declare global {
  interface Window {
    FBInstant?: FBInstantNamespace;
  }
  var FBInstant: FBInstantNamespace | undefined;
}

interface FBInstantNamespace {
  initializeAsync(): Promise<void>;
  startGameAsync(): Promise<void>;
  getPlayer(): FBInstantPlayer;
  getLeaderboard(id: string): FBInstantLeaderboard;
  shareAsync(payload: FBSharePayload): Promise<void>;
  setLoadingProgress(progress: number): void;
  getSDKVersion(): string | undefined;
  canCreateShortcutAsync(): Promise<boolean>;
  createShortcutAsync(): Promise<void>;
  switchGameAsync(id: string): Promise<void>;
  player: FBInstantPlayerAPI;
}

interface FBInstantPlayer {
  playerID: string;
  getID(): string;
  getName(): string | null;        // null in SDK 8.0+
  getPhoto(): string | null;       // null in SDK 8.0+
}

interface FBInstantPlayerAPI {
  getID(): string;
  getName(): string | null;
  getPhoto(): string | null;
  getConnectedPlayersAsync(): Promise<FBInstantPlayer[]>;
  canSubscribeBotAsync(): Promise<boolean>;
  subscribeBotAsync(): Promise<void>;
}

interface FBInstantLeaderboard {
  setScoreAsync(score: number): Promise<void>;
  getEntriesAsync(): Promise<FBInstantLeaderboardEntry[]>;
}

interface FBInstantLeaderboardEntry {
  player: FBInstantPlayer;
  score: number;
}

/** Default no-op stub for local development */
function createStub(): FBSDK {
  return {
    get initialized() { return true; },
    get sdkVersion() { return 'stub'; },
    initialize: async () => {},
    startGame: async () => {},
    getPlayer: async () => ({ playerID: 'stub-player', name: 'Test Player', pictureURL: null }),
    setScore: async () => {},
    getLeaderboard: async () => [],
    getConnectedPlayers: async () => [],
    share: async () => {},
    canCreateShortcut: async () => false,
    createShortcut: async () => {},
    switchGame: async () => {},
    setLoadingProgress: () => {},
    subscribeBot: async () => {},
  };
}

/**
 * Create an FBSDK instance. When running outside Facebook iframe,
 * returns a no-op stub so the game still launches for testing.
 * When running in a Facebook Instant Games iframe, all API calls
 * proceed to the real globalThis.FBInstant implementation.
 */
export function createFBSDK(): FBSDK {
  // Detect if we're running inside a Facebook Instant Games iframe
  const isFBInstant = typeof globalThis !== 'undefined'
    && typeof globalThis.FBInstant !== 'undefined';

  let initialized = false;
  let sdkVersion: string | null = null;

  // Initialize the FB SDK (real or stub mode)
  async function initialize(): Promise<void> {
    if (!isFBInstant) {
      // Stub mode — allow local testing
      initialized = true;
      return;
    }
    try {
      const FBInstant = globalThis.FBInstant!;
      await FBInstant.initializeAsync();
      sdkVersion = FBInstant.getSDKVersion?.() ?? 'unknown';
      initialized = true;
    } catch (err) {
      console.error('FB Instant Games initialization failed:', err);
      // Fallback to stub if SDK fails or is unavailable
      initialized = true;
    }
  }

  // Start the game — signals FB that the game is ready to render
  async function startGame(): Promise<void> {
    if (!initialized) await initialize();
    if (isFBInstant) {
      try {
        const FBInstant = globalThis.FBInstant!;
        await FBInstant.startGameAsync();
      } catch (err) {
        console.error('FB startGame failed:', err);
      }
    }
  }

  // Get the current Facebook player ID and name
  async function getPlayer(): Promise<FBPlayer> {
    if (!initialized) await initialize();
    if (isFBInstant) {
      try {
        const FBInstant = globalThis.FBInstant!;
        const player = FBInstant.getPlayer();
        const sdkVer = parseFloat(sdkVersion ?? '0');
        const isSDK8OrHigher = sdkVer >= 8.0 || sdkVersion === 'latest';

        let name: string | null = null;
        let photo: string | null = null;

        if (!isSDK8OrHigher) {
          name = player.getName();
          photo = player.getPhoto();
          // Check for bad pic data (can be 1000+ char string)
          if (photo && photo.length > 1000) photo = null;
        }

        return {
          playerID: player.getID(),
          name,
          pictureURL: photo,
        };
      } catch (err) {
        console.error('FB getPlayer failed:', err);
        return { playerID: 'error', name: 'Error', pictureURL: null };
      }
    }
    // Stub mode return
    return { playerID: 'stub-player', name: 'Test Player', pictureURL: null };
  }

  // Set a score on the specified leaderboard
  async function setScore(leaderboardID: string, score: number): Promise<void> {
    if (!initialized) await initialize();
    if (isFBInstant) {
      try {
        const FBInstant = globalThis.FBInstant!;
        const lb = FBInstant.getLeaderboard(leaderboardID);
        await lb.setScoreAsync(score);
      } catch (err) {
        console.error(`FB setScore failed for ${leaderboardID}:`, err);
      }
    }
    // Stub mode: silently succeed
  }

  // Get the current leaderboard entries
  async function getLeaderboard(leaderboardID: string): Promise<FBLeaderboardEntry[]> {
    if (!initialized) await initialize();
    if (isFBInstant) {
      try {
        const FBInstant = globalThis.FBInstant!;
        const lb = FBInstant.getLeaderboard(leaderboardID);
        const entries = await lb.getEntriesAsync();
        return entries.map((e, i) => ({
          playerID: e.player.getID(),
          score: e.score,
          rank: i + 1, // approximate rank
        }));
      } catch (err) {
        console.error(`FB getLeaderboard failed for ${leaderboardID}:`, err);
        return [];
      }
    }
    // Stub mode: return empty leaderboard
    return [];
  }

  // Get connected players (friends who also play this game)
  async function getConnectedPlayers(): Promise<FBPlayer[]> {
    if (!initialized) await initialize();
    if (isFBInstant) {
      try {
        const FBInstant = globalThis.FBInstant!;
        const players = await FBInstant.player.getConnectedPlayersAsync();
        return players.map(p => ({
          playerID: p.getID(),
          name: p.getName(),
          pictureURL: p.getPhoto(),
        }));
      } catch (err) {
        console.error('FB getConnectedPlayers failed:', err);
        return [];
      }
    }
    return [];
  }

  // Share to Facebook (SHARE, REQUEST, SEND, or INVITE)
  async function share(payload: FBSharePayload): Promise<void> {
    if (!initialized) await initialize();
    if (isFBInstant) {
      try {
        const FBInstant = globalThis.FBInstant!;
        await FBInstant.shareAsync(payload);
      } catch (err) {
        console.error('FB share failed:', err);
      }
    }
    // Stub mode: silently succeed
  }

  // Check if shortcut creation is available
  async function canCreateShortcut(): Promise<boolean> {
    if (!initialized) await initialize();
    if (isFBInstant) {
      try {
        const FBInstant = globalThis.FBInstant!;
        return await FBInstant.canCreateShortcutAsync();
      } catch (err) {
        console.error('FB canCreateShortcut failed:', err);
        return false;
      }
    }
    return false;
  }

  // Create a home screen shortcut
  async function createShortcut(): Promise<void> {
    if (!initialized) await initialize();
    if (isFBInstant) {
      try {
        const FBInstant = globalThis.FBInstant!;
        const canCreate = await FBInstant.canCreateShortcutAsync();
        if (canCreate) {
          await FBInstant.createShortcutAsync();
        }
      } catch (err) {
        console.error('FB createShortcut failed:', err);
      }
    }
  }

  // Switch to another Instant Game
  async function switchGame(appID: string): Promise<void> {
    if (!initialized) await initialize();
    if (isFBInstant) {
      try {
        const FBInstant = globalThis.FBInstant!;
        await FBInstant.switchGameAsync(appID);
      } catch (err) {
        console.error('FB switchGame failed:', err);
      }
    }
  }

  // Set the loading progress bar visible to the player
  function setLoadingProgress(progress: number): void {
    try {
      if (isFBInstant) {
        const FBInstant = globalThis.FBInstant!;
        FBInstant.setLoadingProgress(progress);
      }
    } catch (err) {
      console.error('FB setLoadingProgress failed:', err);
    }
  }

  // Subscribe player to bot
  async function subscribeBot(): Promise<void> {
    if (!initialized) await initialize();
    if (isFBInstant) {
      try {
        const FBInstant = globalThis.FBInstant!;
        if (await FBInstant.player.canSubscribeBotAsync()) {
          await FBInstant.player.subscribeBotAsync();
        }
      } catch (err) {
        console.error('FB subscribeBot failed:', err);
      }
    }
  }

  return {
    get initialized() { return initialized; },
    get sdkVersion() { return sdkVersion; },
    initialize,
    startGame,
    getPlayer,
    setScore,
    getLeaderboard,
    getConnectedPlayers,
    share,
    canCreateShortcut,
    createShortcut,
    switchGame,
    setLoadingProgress,
    subscribeBot,
  };
}