/**
 * Persistence — localStorage high score
 * Replaces UserDefaults from macOS original.
 *
 * Stores only high score and per-stage exoskeleton state.
 * Scope limited to high score — no PII, no sensitive data.
 */

import type { ScoreSnapshot } from '../types/GameTypes';

const HIGH_SCORE_KEY = 'exolon:high_score';
const EXO_KEY = 'exolon:exoskeleton_stage';

export interface Persistence {
  highScore: number;
  loadHighScore(): number;
  saveHighScore(score: number): void;
  saveExoskeleton(stage: number): void;
  loadExoskeleton(): number;
  clearAll(): void;
}

export function createPersistence(): Persistence {
  let highScore = loadHighScore();
  let exoskeletonStage = loadExoskeleton();

  function loadHighScore(): number {
    try {
      const stored = localStorage.getItem(HIGH_SCORE_KEY);
      return stored !== null ? parseInt(stored, 10) : 0;
    } catch {
      return 0;
    }
  }

  function saveHighScore(score: number): void {
    highScore = Math.max(highScore, score);
    try {
      localStorage.setItem(HIGH_SCORE_KEY, String(highScore));
    } catch {
      // localStorage unavailable in iframe — silent fallback
    }
  }

  function saveExoskeleton(stage: number): void {
    exoskeletonStage = stage;
    try {
      localStorage.setItem(EXO_KEY, String(stage));
    } catch {
      // silent fallback
    }
  }

  function loadExoskeleton(): number {
    try {
      const stored = localStorage.getItem(EXO_KEY);
      return stored !== null ? parseInt(stored, 10) : -1;
    } catch {
      return -1;
    }
  }

  function clearAll(): void {
    highScore = 0;
    exoskeletonStage = -1;
    try {
      localStorage.removeItem(HIGH_SCORE_KEY);
      localStorage.removeItem(EXO_KEY);
    } catch {
      // silent fallback
    }
  }

  return {
    get highScore() { return highScore; },
    loadHighScore,
    saveHighScore,
    saveExoskeleton,
    loadExoskeleton,
    clearAll,
  };
}
