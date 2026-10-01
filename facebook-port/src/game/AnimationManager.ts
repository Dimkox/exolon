/**
 * AnimationManager — sprite animations for flashing cells, torches, etc.
 * Ported from SKAction + SKSpriteNode animation logic.
 *
 * Flashing cells toggle visibility on a timer.
 * Torches pulse with a sine wave.
 */

import type { Tile } from '../types/GameTypes';

export interface AnimationManager {
  tick: number;
  update(dtMs: number): void;
  getAlpha(tileType: string): number; // 0..1, alpha for flashing cells
  isVisible(tileType: string): boolean;
}

export function createAnimationManager(): AnimationManager {
  let tick = 0;

  // Flashing cell state: cycle through visible/invisible
  const flashingPhase = 8; // ticks per half-cycle

  function update(dtMs: number): void {
    tick += 1;
  }

  function getAlpha(tileType: string): number {
    switch (tileType) {
      case 'flashing':
        // Toggle visibility every flashingPhase ticks
        return (tick % (flashingPhase * 2)) < flashingPhase ? 1 : 0.2;
      case 'torch':
        // Pulsing alpha
        return 0.6 + 0.4 * Math.sin(tick * 0.1);
      default:
        return 1;
    }
  }

  function isVisible(tileType: string): boolean {
    if (tileType === 'flashing') {
      return (tick % (flashingPhase * 2)) < flashingPhase;
    }
    return true;
  }

  return { tick, update, getAlpha, isVisible };
}
