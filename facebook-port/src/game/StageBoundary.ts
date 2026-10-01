/**
 * StageBoundary — stage-end awards
 * Ported from StageBoundaryLedger.
 *
 * Zones 024, 049, 074, 099, 124 are stage ends.
 * Awards: 1000 points per remaining life + 10000 bravery bonus (if no exoskeleton)
 *         + timed bonus cursor (0/1000/3000/5000/7000) + 1 life (cap 9).
 */

import type { GameFlowState } from '../types/GameTypes';

export interface StageBoundaryResult {
  bonusPoints: number;
  braveryPoints: number;
  timedPoints: number;
  lifeAwarded: boolean;
  flowAfter: GameFlowState;
}

export interface StageBoundary {
  isStageEnd(zoneNumber: number): boolean;
  calculateBonus(lives: number, hasExoskeleton: boolean, stage: number): StageBoundaryResult;
  triggerBonus(zoneNumber: number, lives: number, hasExoskeleton: boolean, stage: number): StageBoundaryResult;
}

export function createStageBoundary(): StageBoundary {
  function isStageEnd(zoneNumber: number): boolean {
    return zoneNumber === 24 || zoneNumber === 49 || zoneNumber === 74
      || zoneNumber === 99 || zoneNumber === 124;
  }

  function calculateBonus(
    lives: number,
    hasExoskeleton: boolean,
    stage: number,
  ): StageBoundaryResult {
    const bonusPoints = lives * 1000;
    const braveryPoints = hasExoskeleton ? 0 : 10000;

    // Timed bonus cursor: depends on "phase" — simulate with stage-based deterministic value
    // Original: cursor cycles through 0/1000/3000/5000/7000 based on timing
    const timedOptions = [0, 1000, 3000, 5000, 7000];
    const timedPoints = timedOptions[stage % timedOptions.length];

    const flowAfter: GameFlowState = 'stage_bonus';

    return { bonusPoints, braveryPoints, timedPoints, lifeAwarded: true, flowAfter };
  }

  function triggerBonus(
    zoneNumber: number,
    lives: number,
    hasExoskeleton: boolean,
    stage: number,
  ): StageBoundaryResult {
    if (!isStageEnd(zoneNumber)) {
      return { bonusPoints: 0, braveryPoints: 0, timedPoints: 0, lifeAwarded: false, flowAfter: 'playing' };
    }
    return calculateBonus(lives, hasExoskeleton, stage);
  }

  return { isStageEnd, calculateBonus, triggerBonus };
}
