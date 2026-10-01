/**
 * InstantGames — FB Instant Games specific integration
 * Handles loading progress, auth, and game loop integration.
 *
 * The FB SDK script is loaded via index.html. This module just wraps
 * the FBSDK with convenience methods and progress reporting.
 */

import { createFBSDK, type FBSDK, type FBPlayer } from './FBSDK';

export interface InstantGamesConfig {
  leaderboardID: string;
  onProgress?: (progress: number) => void;
}

export interface InstantGames {
  readonly sdk: FBSDK;
  readonly ready: boolean;
  initialize(config: InstantGamesConfig): Promise<void>;
  launch(): Promise<void>;
  reportScore(score: number): Promise<void>;
  getHighScore(): Promise<number>;
  getProfile(): Promise<FBPlayer | null>;
}

export async function createInstantGames(): Promise<InstantGames> {
  const sdk = createFBSDK();
  let ready = false;
  let config: InstantGamesConfig | null = null;

  async function initialize(cfg: InstantGamesConfig): Promise<void> {
    config = cfg;

    // SDK script is loaded in index.html, just initialize
    await sdk.initialize();
    ready = true;
  }

  async function launch(): Promise<void> {
    if (!ready) throw new Error('InstantGames not initialized');
    await sdk.startGame();
  }

  async function reportScore(score: number): Promise<void> {
    if (!config) return;
    await sdk.setScore(config.leaderboardID, score);
  }

  async function getHighScore(): Promise<number> {
    if (!config) return 0;
    try {
      const entries = await sdk.getLeaderboard(config.leaderboardID);
      if (entries.length === 0) return 0;
      return entries[0].score;
    } catch {
      return 0;
    }
  }

  async function getProfile(): Promise<FBPlayer | null> {
    if (!config) return null;
    try {
      return await sdk.getPlayer();
    } catch {
      return null;
    }
  }

  return { sdk, ready, initialize, launch, reportScore, getHighScore, getProfile };
}