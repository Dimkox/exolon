/**
 * GameLoop — requestAnimationFrame + FixedTickDriver
 * Ported from Swift GameLoop (SpriteKit SKScene + CADisplayLink → Canvas 2D).
 *
 * Original logic: one logical tick every 16.67 ms (60 fps), physics at fixed
 * timestep, rendering interpolated between ticks. Browser equivalent:
 * requestAnimationFrame for rendering, accumulator for fixed-tick stepping.
 */

import type { GameFlowState } from '../types/GameTypes';

const TICK_MS = 16.67; // 60 Hz logical tick
const MAX_ACCUMULATOR = 200; // cap to avoid spiral of death

export type TickHandler = (dtMs: number, state: GameStateSnapshot) => void;
export type RenderHandler = (alpha: number, state: GameStateSnapshot) => void;

export interface GameStateSnapshot {
  flow: GameFlowState;
  score: number;
  lives: number;
  stage: number;
  zoneInStage: number;
  playerAlive: boolean;
}

export interface FixedTickDriver {
  readonly running: boolean;
  start(): void;
  stop(): void;
  onTick: TickHandler | null;
  onRender: RenderHandler | null;
}

export function createFixedTickDriver(
  getState: () => GameStateSnapshot,
  tick: TickHandler,
  render: RenderHandler,
): FixedTickDriver {
  let rafId = 0;
  let lastTimestamp = 0;
  let accumulator = 0;
  let _running = false;

  function loop(timestamp: number): void {
    if (!_running) return;

    if (lastTimestamp === 0) {
      lastTimestamp = timestamp;
    }

    const elapsed = timestamp - lastTimestamp;
    lastTimestamp = timestamp;
    accumulator = Math.min(accumulator + elapsed, MAX_ACCUMULATOR);

    while (accumulator >= TICK_MS) {
      tick(TICK_MS, getState());
      accumulator -= TICK_MS;
    }

    const alpha = accumulator / TICK_MS;
    render(alpha, getState());

    rafId = requestAnimationFrame(loop);
  }

  return {
    get running() { return _running; },
    start() {
      if (_running) return;
      _running = true;
      lastTimestamp = 0;
      accumulator = 0;
      rafId = requestAnimationFrame(loop);
    },
    stop() {
      _running = false;
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = 0;
      }
    },
    onTick: null,
    onRender: null,
  };
}
