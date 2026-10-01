/**
 * LevelManager — level loading, zone transitions
 * Ported from TMXLevelRuntime (Foundation bundle → Fetch + bundled JSON).
 *
 * Levels are converted from TMX → JSON by scripts/convert-assets.ts.
 * Each zone is a JSON file: assets/levels/zone_XXX.json
 */

import type { LevelData, Tile } from '../types/GameTypes';

export interface LevelManager {
  readonly currentZone: number;
  readonly currentStage: number;
  loadZone(zoneNumber: number): Promise<LevelData | null>;
  nextZone(): number;
  prevZone(): number;
  isStageEnd(zoneNumber: number): boolean;
  stageStartZone(stage: number): number;
}

const ZONES_PER_STAGE = 25;
const TOTAL_ZONES = 125;
const STAGES = 5;

/** Stage starting positions (original coordinates) */
const STAGE_STARTS: Record<number, { x: number; y: number }> = {
  0: { x: 16, y: 112 },
  1: { x: 0, y: 120 },
  2: { x: 0, y: 32 },
  3: { x: 40, y: 128 },
  4: { x: 16, y: 112 },
};

/** Generate an empty level */
function emptyLevel(zoneNumber: number): LevelData {
  const stage = Math.floor(zoneNumber / ZONES_PER_STAGE);
  const zoneInStage = zoneNumber % ZONES_PER_STAGE;
  const cols = 20;
  const rows = 15;
  const tileW = 25;
  const tileH = 30;

  const tiles: Tile[][] = Array.from({ length: rows }, (_, r) =>
    Array.from({ length: cols }, (_, c) => ({
      type: (r === rows - 1) ? 'solid' : 'empty',
      x: c * tileW,
      y: r * tileH,
      w: tileW,
      h: tileH,
    }))
  );

  return {
    zoneNumber,
    stage,
    width: cols * tileW,
    height: rows * tileH,
    tiles,
    playerStart: { ...STAGE_STARTS[stage] },
    actionMarkers: [],
  };
}

/** Try to fetch a converted level JSON; fall back to generated empty level */
async function fetchLevel(zoneNumber: number): Promise<LevelData | null> {
  try {
    const padded = String(zoneNumber).padStart(3, '0');
    const resp = await fetch(`/assets/levels/zone_${padded}.json`);
    if (!resp.ok) return null;
    const data: LevelData = await resp.json();
    return data;
  } catch {
    return null;
  }
}

export function createLevelManager(): LevelManager {
  let currentZone = 0;
  let currentStage = 0;
  let cachedLevel: LevelData | null = null;

  function isStageEnd(zoneNumber: number): boolean {
    return zoneNumber === 24 || zoneNumber === 49 || zoneNumber === 74
      || zoneNumber === 99 || zoneNumber === 124;
  }

  function stageStartZone(stage: number): number {
    return stage * ZONES_PER_STAGE;
  }

  async function loadZone(zoneNumber: number): Promise<LevelData | null> {
    if (zoneNumber < 0 || zoneNumber >= TOTAL_ZONES) return null;

    currentZone = zoneNumber;
    currentStage = Math.floor(zoneNumber / ZONES_PER_STAGE);

    const fetched = await fetchLevel(zoneNumber);
    cachedLevel = fetched ?? emptyLevel(zoneNumber);
    return cachedLevel;
  }

  function nextZone(): number {
    const next = currentZone + 1;
    if (next >= TOTAL_ZONES) return currentZone;
    return next;
  }

  function prevZone(): number {
    const prev = currentZone - 1;
    if (prev < 0) return 0;
    return prev;
  }

  return {
    get currentZone() { return currentZone; },
    get currentStage() { return currentStage; },
    loadZone,
    nextZone,
    prevZone,
    isStageEnd,
    stageStartZone,
  };
}
