/**
 * FBSDK — Facebook Gaming SDK wrapper
 * Abstracts FB Instant Games API behind a testable interface.
 */

export interface FBPlayer {
  playerID: string;
  name: string;
  pictureURL: string;
}

export interface FBLeaderboardEntry {
  playerID: string;
  score: number;
  rank: number;
}

export interface FBSDK {
  readonly initialized: boolean;
  initialize(): Promise<void>;
  startGame(): Promise<void>;
  getPlayer(): Promise<FBPlayer>;
  setScore(leaderboardID: string, score: number): Promise<void>;
  getLeaderboard(leaderboardID: string): Promise<FBLeaderboardEntry[]>;
  share(payload: FBSharePayload): Promise<void>;
}

export interface FBSharePayload {
  intent: 'request' | 'share' | 'send';
  text?: string;
  data?: string;
}

declare global {
  interface Window {
    FBInstant?: FBInstantNamespace;
  }
}

export interface FBInstantNamespace {
  initializeAsync(): Promise<void>;
  startGameAsync(): Promise<void>;
  getPlayer(): FBInstantPlayer;
  getLeaderboardAsync(id: string): Promise<FBInstantLeaderboard>;
  shareAsync(payload: FBSharePayload): Promise<void>;
  setLoadingProgress(progress: number): void;
}

export interface FBInstantPlayer {
  playerID: string;
  getName(): string;
  getPhoto(): string;
}

export interface FBInstantLeaderboard {
  setScoreAsync(score: number): Promise<void>;
  getEntriesAsync(): Promise<FBInstantLeaderboardEntry[]>;
}

export interface FBInstantLeaderboardEntry {
  player: FBInstantPlayer;
  score: number;
}

/**
 * Create an FBSDK instance. When running outside Facebook iframe,
 * returns a no-op stub so the game still launches for testing.
 */
export function createFBSDK(): FBSDK {
  let initialized = false;

  const isFBInstant = typeof window !== 'undefined'
    && typeof window.FBInstant !== 'undefined';

  async function initialize(): Promise<void> {
    if (!isFBInstant) {
      // Stub mode — allow local testing
      initialized = true;
      return;
    }
    await window.FBInstant!.initializeAsync();
    initialized = true;
  }

  async function startGame(): Promise<void> {
    if (!isFBInstant) return;
    await window.FBInstant!.startGameAsync();
  }

  async function getPlayer(): Promise<FBPlayer> {
    if (!isFBInstant) {
      return { playerID: 'stub-player', name: 'Test Player', pictureURL: '' };
    }
    const p = window.FBInstant!.getPlayer();
    return { playerID: p.playerID, name: p.getName(), pictureURL: p.getPhoto() };
  }

  async function setScore(leaderboardID: string, score: number): Promise<void> {
    if (!isFBInstant) return;
    const lb = await window.FBInstant!.getLeaderboardAsync(leaderboardID);
    await lb.setScoreAsync(score);
  }

  async function getLeaderboard(leaderboardID: string): Promise<FBLeaderboardEntry[]> {
    if (!isFBInstant) return [];
    const lb = await window.FBInstant!.getLeaderboardAsync(leaderboardID);
    const entries = await lb.getEntriesAsync();
    return entries.map(e => ({
      playerID: e.player.playerID,
      score: e.score,
      rank: 0, // FBInstant API doesn't expose rank in getEntriesAsync
    }));
  }

  async function share(payload: FBSharePayload): Promise<void> {
    if (!isFBInstant) return;
    await window.FBInstant!.shareAsync(payload);
  }

  return {
    get initialized() { return initialized; },
    initialize,
    startGame,
    getPlayer,
    setScore,
    getLeaderboard,
    share,
  };
}
