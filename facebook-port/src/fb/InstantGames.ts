/**
 * InstantGames — FB Instant Games specific integration
 * Handles loading progress, auth, and game loop integration.
 */

import { createFBSDK, type FBSDK } from './FBSDK';

export interface InstantGamesConfig {
  sdkUrl: string;
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
}

export async function createInstantGames(): Promise<InstantGames> {
  const sdk = createFBSDK();
  let ready = false;
  let config: InstantGamesConfig | null = null;

  async function initialize(cfg: InstantGamesConfig): Promise<void> {
    config = cfg;

    // Load SDK script if not already loaded
    if (typeof window !== 'undefined' && !window.FBInstant) {
      await loadSDK(cfg.sdkUrl, cfg.onProgress);
    }

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

  return { sdk, ready, initialize, launch, reportScore, getHighScore };
}

function loadSDK(url: string, onProgress?: (p: number) => void): Promise<void> {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = url;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load FB SDK: ${url}`));
    // Simulate progress during load
    let progress = 0;
    const interval = setInterval(() => {
      progress = Math.min(progress + 20, 90);
      onProgress?.(progress);
    }, 100);
    script.onload = () => {
      clearInterval(interval);
      onProgress?.(100);
      resolve();
    };
    script.onerror = () => {
      clearInterval(interval);
      reject(new Error(`Failed to load FB SDK: ${url}`));
    };
    document.head.appendChild(script);
  });
}
