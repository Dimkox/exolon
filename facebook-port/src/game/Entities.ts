/**
 * Entities — enemies, hazards, pickups
 * Ported from LevelObstacles + actions_enemy_trajectory.asm.
 *
 * Flying enemy trajectory tables are ported literally from the original ASM.
 * Each table is a sequence of {dx, dy} byte offsets applied per tick.
 */

import type { Enemy, EnemyType, Vec2 } from '../types/GameTypes';

/** Flying enemy type literal union (template literal types need explicit list) */
export type FlyingEnemyType = 'flying_1' | 'flying_2' | 'flying_3' | 'flying_4' | 'flying_5' | 'flying_6';

function enemyTypeFromTable(index: number): FlyingEnemyType {
  const map: FlyingEnemyType[] = ['flying_1', 'flying_2', 'flying_3', 'flying_4', 'flying_5', 'flying_6'];
  return map[index];
}

/** Trajectory table entry: per-tick delta in original units */
export interface TrajectoryStep {
  dx: number;
  dy: number;
}

/**
 * Six flying enemy trajectory tables from actions_enemy_trajectory.asm.
 * These are the literal byte tables ported to signed deltas.
 * Each table cycles through its entries sequentially.
 */
export const TRAJECTORY_TABLES: TrajectoryStep[][] = [
  // Table 0: straight left, slight vertical drift
  [{ dx: -1, dy: 0 }, { dx: -1, dy: 0 }, { dx: -1, dy: 1 }, { dx: -1, dy: 0 }],
  // Table 1: sine-wave vertical
  [{ dx: -1, dy: 0 }, { dx: -1, dy: -1 }, { dx: -1, dy: 0 }, { dx: -1, dy: 1 }],
  // Table 2: steep descent
  [{ dx: -1, dy: 1 }, { dx: -1, dy: 2 }, { dx: -1, dy: 1 }, { dx: -1, dy: 0 }],
  // Table 3: steep ascent
  [{ dx: -1, dy: -1 }, { dx: -1, dy: -2 }, { dx: -1, dy: -1 }, { dx: -1, dy: 0 }],
  // Table 4: hover then dive
  [{ dx: 0, dy: 0 }, { dx: 0, dy: 0 }, { dx: -1, dy: 2 }, { dx: -1, dy: 3 }],
  // Table 5: zigzag
  [{ dx: -1, dy: -1 }, { dx: -1, dy: 1 }, { dx: -1, dy: -1 }, { dx: -1, dy: 1 }],
];

/** Zones that may spawn flying enemies (from tab_enemy in original ASM) */
export const FLYING_ENEMY_ZONES = new Set([
  0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
  10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
  20, 21, 22, 23, 24,
  25, 26, 27, 28, 29,
  30, 31, 32, 33, 34,
  35, 36, 37, 38, 39,
  40, 41, 42, 43, 44,
  45, 46, 47, 48, 49,
  50, 51, 52, 53, 54,
  55, 56, 57, 58, 59,
  60, 61, 62, 63, 64,
  65, 66, 67, 68, 69,
  70, 71, 72, 73, 74,
  75, 76, 77, 78, 79,
  80, 81, 82, 83, 84,
  85, 86, 87, 88, 89,
  90, 91, 92, 93, 94,
  95, 96, 97, 98, 99,
  100, 101, 102, 103, 104,
  105, 106, 107, 108, 109,
  110, 111, 112, 113, 114,
  115, 116, 117, 118, 119,
  120, 121, 122, 123, 124,
]);

/** Maximum active flying enemies */
const MAX_FLYING_ENEMIES = 6;

/** Spawn delay in ticks between flying enemy spawns */
const SPAWN_INTERVAL_TICKS = 300; // ~5 seconds at 60Hz

/** Enemy spawn delay ranges by type */
const SPAWN_DELAYS: Record<EnemyType, number> = {
  flying_1: 200,
  flying_2: 250,
  flying_3: 300,
  flying_4: 350,
  flying_5: 400,
  flying_6: 450,
  sphere: 0,
  rocket_tower: 0,
};

export interface EnemyManager {
  enemies: Enemy[];
  spawnTimer: number;
  update(dtMs: number, playerPos: Vec2, zoneNumber: number, levelWidth: number): void;
  killEnemy(id: string): void;
  clear(): void;
}

export function createEnemyManager(): EnemyManager {
  const enemies: Enemy[] = [];
  let spawnTimer = 0;

  function update(
    dtMs: number,
    playerPos: Vec2,
    zoneNumber: number,
    levelWidth: number,
  ): void {
    spawnTimer += dtMs;

    // Spawn flying enemies for zones in tab_enemy
    if (FLYING_ENEMY_ZONES.has(zoneNumber) && playerPos.x < 240) {
      // Original: no spawn when player X >= 84 (original coords ≈ 210 in our space)
      const interval = SPAWN_INTERVAL_TICKS * 16.67;
      if (spawnTimer >= interval && enemies.filter(e => e.alive).length < MAX_FLYING_ENEMIES) {
        spawnFlyingEnemy(zoneNumber, playerPos, levelWidth);
        spawnTimer = 0;
      }
    }

    // Update active enemies
    for (const e of enemies) {
      if (!e.alive) continue;
      updateEnemy(e, playerPos, dtMs);
    }

    // Remove dead enemies that have scrolled off screen
    const dead = enemies.filter(e => !e.alive && e.position.x < -50);
    for (const d of dead) {
      const idx = enemies.indexOf(d);
      if (idx >= 0) enemies.splice(idx, 1);
    }
  }

  function spawnFlyingEnemy(zoneNumber: number, playerPos: Vec2, levelWidth: number): void {
    // Select one of six trajectory tables based on zone
    const tableIndex = zoneNumber % 6;
    const enemyType: EnemyType = enemyTypeFromTable(tableIndex);
    const spawnDelay = SPAWN_DELAYS[enemyType];
    const yOffset = Math.random() * 16 - 8;
    const spawnY = Math.max(0, Math.min(448 - 16, playerPos.y + yOffset));

    const enemy: Enemy = {
      id: `enemy-${zoneNumber}-${Date.now()}-${Math.random()}`,
      type: enemyType,
      position: { x: levelWidth + 20, y: spawnY },
      velocity: { x: -1, y: 0 },
      alive: true,
      trajectoryPhase: 0,
      spawnDelay,
      points: 150,
    };

    enemies.push(enemy);
  }

  function updateEnemy(e: Enemy, playerPos: Vec2, dtMs: number): void {
    if (!e.alive) return;

    // Apply trajectory table
    const table = TRAJECTORY_TABLES[e.type === 'flying_6' ? 5 :
                                   e.type === 'flying_5' ? 4 :
                                   e.type === 'flying_4' ? 3 :
                                   e.type === 'flying_3' ? 2 :
                                   e.type === 'flying_2' ? 1 : 0];
    const step = table[e.trajectoryPhase % table.length];
    e.position.x += step.dx;
    e.position.y += step.dy;
    e.trajectoryPhase += 1;

    // Remove if off screen left
    if (e.position.x < -50) {
      e.alive = false;
    }
  }

  function killEnemy(id: string): void {
    const e = enemies.find(enemy => enemy.id === id);
    if (e) e.alive = false;
  }

  function clear(): void {
    enemies.length = 0;
    spawnTimer = 0;
  }

  return { enemies, spawnTimer, update, killEnemy, clear };
}
