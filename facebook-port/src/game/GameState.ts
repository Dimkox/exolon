/**
 * GameState — flow state, score, lives
 * Ported from GameState.swift (NSUserDefaults-backed persistence → localStorage).
 */

import type { GameFlowState, ScoreSnapshot } from '../types/GameTypes';

const STORAGE_KEY = 'exolon:score';

export interface GameState {
  flow: GameFlowState;
  score: number;
  lives: number;
  stage: number;       // 0–4
  zoneInStage: number; // 0–24
  highScore: number;
  readonly snapshot: () => ScoreSnapshot;
  addScore(points: number): void;
  loseLife(): void;
  gainLife(): void;
  nextZone(): void;
  nextStage(): void;
  resetStage(): void;
  setFlow(flow: GameFlowState): void;
  saveHighScore(): void;
  loadHighScore(): number;
}

export function createGameState(): GameState {
  let flow: GameFlowState = 'title';
  let score = 0;
  let lives = 9;
  let stage = 0;
  let zoneInStage = 0;
  let highScore = 0;

  function snapshot() {
    return { score, highScore, lives, stage, zoneInStage };
  }

  function addScore(points: number): void {
    score += points;
  }

  function loseLife(): void {
    lives -= 1;
  }

  function gainLife(): void {
    if (lives < 9) lives += 1;
  }

  function nextZone(): void {
    zoneInStage += 1;
    if (zoneInStage > 24) {
      zoneInStage = 0;
      nextStage();
    }
  }

  function nextStage(): void {
    stage += 1;
    if (stage > 4) {
      // Zone 124 completed — full combat ability, loop to start
      stage = 0;
    }
  }

  function resetStage(): void {
    stage = 0;
    zoneInStage = 0;
    lives = 9;
    score = 0;
    flow = 'playing';
  }

  function setFlow(newFlow: GameFlowState): void {
    flow = newFlow;
  }

  function saveHighScore(): void {
    try {
      localStorage.setItem(STORAGE_KEY, String(highScore));
    } catch {
      // localStorage unavailable in iframe/secure context — silent fallback
    }
  }

  function loadHighScore(): number {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return stored !== null ? parseInt(stored, 10) : 0;
    } catch {
      return 0;
    }
  }

  highScore = loadHighScore();

  return {
    get flow() { return flow; },
    get score() { return score; },
    get lives() { return lives; },
    get stage() { return stage; },
    get zoneInStage() { return zoneInStage; },
    get highScore() { return highScore; },
    snapshot,
    addScore,
    loseLife,
    gainLife,
    nextZone,
    nextStage,
    resetStage,
    setFlow,
    saveHighScore,
    loadHighScore,
  };
}
