/**
 * Player — physics, movement, collision
 * Ported from Player.swift (SKNode physics → Canvas 2D AABB).
 *
 * Original mechanics preserved:
 * - 9 lives start, 99 blaster, 10 grenades
 * - Death refills ammo to 99 / grenades to 10
 * - New zone clears active bullets/grenades/enemies
 * - Exoskeleton: immunity to mines/pumps, double shot, forfeits 10000 bravery bonus
 * - TEST INVULNERABILITY flag (non-original, for verification only)
 */

import type { Vec2, InputState, PlayerState, Projectile, Tile } from '../types/GameTypes';

const SPEED = 3.0;
const JUMP_VEL = -7.0;
const GRAVITY = 0.25;
const TERMINAL_VY = 8.0;

export function createPlayer(position: Vec2): PlayerState {
  return {
    position: { ...position },
    velocity: { x: 0, y: 0 },
    lives: 9,
    blasterAmmo: 99,
    grenades: 10,
    hasExoskeleton: false,
    exoskeletonStage: -1,
    doubleShot: false,
    invincible: false,
    invincibleTimer: 0,
    facingLeft: false,
    alive: true,
  };
}

export function updatePlayer(
  p: PlayerState,
  input: InputState,
  tiles: Tile[][],
  levelWidth: number,
  levelHeight: number,
  dtMs: number,
): void {
  if (!p.alive) return;

  // Horizontal movement
  let dx = 0;
  if (input.left) dx -= SPEED;
  if (input.right) dx += SPEED;
  p.facingLeft = dx < 0;

  // Gravity
  p.velocity.y += GRAVITY;
  if (p.velocity.y > TERMINAL_VY) p.velocity.y = TERMINAL_VY;

  // Apply velocity
  p.position.x += dx;
  p.position.y += p.velocity.y;

  // Stage boundary clamping (original coordinate space)
  p.position.x = Math.max(0, Math.min(levelWidth - 16, p.position.x));
  p.position.y = Math.max(0, Math.min(levelHeight - 32, p.position.y));

  // Simple tile collision resolution
  resolveTileCollision(p, tiles);

  // Invincibility timer
  if (p.invincible) {
    p.invincibleTimer -= dtMs;
    if (p.invincibleTimer <= 0) {
      p.invincible = false;
    }
  }
}

function resolveTileCollision(p: PlayerState, tiles: Tile[][]): void {
  const px = p.position.x;
  const py = p.position.y;
  const pw = 16;
  const ph = 32;

  for (let row = 0; row < tiles.length; row++) {
    const tileRow = tiles[row];
    if (!tileRow) continue;
    for (let col = 0; col < tileRow.length; col++) {
      const t = tileRow[col];
      if (!t || t.type === 'empty') continue;
      const solid = t.type === 'solid' || t.type === 'destroyable'
        || t.type === 'turret' || t.type === 'pump' || t.type === 'force_field';
      if (!solid) continue;

      // AABB overlap check
      if (px + pw / 2 > t.x && px - pw / 2 < t.x + t.w
        && py + ph / 2 > t.y && py - ph / 2 < t.y + t.h) {
        // Push out on shallowest axis
        const overlapL = (px + pw / 2) - t.x;
        const overlapR = (t.x + t.w) - (px - pw / 2);
        const overlapT = (py + ph / 2) - t.y;
        const overlapB = (t.y + t.h) - (py - ph / 2);
        const min = Math.min(overlapL, overlapR, overlapT, overlapB);
        if (min === overlapT) p.position.y = t.y + t.h + ph / 2;
        else if (min === overlapB) p.position.y = t.y - ph / 2;
        else if (min === overlapL) p.position.x = t.x + t.w + pw / 2;
        else p.position.x = t.x - pw / 2;
      }
    }
  }
}

/** Fire a blaster projectile */
export function fireBlaster(p: PlayerState, projectiles: Projectile[]): void {
  if (p.blasterAmmo <= 0 || !p.alive) return;
  p.blasterAmmo -= 1;
  const bx = p.facingLeft ? p.position.x - 12 : p.position.x + 12;
  projectiles.push({
    id: `blaster-${Date.now()}-${Math.random()}`,
    type: 'blaster',
    position: { x: bx, y: p.position.y },
    velocity: { x: p.facingLeft ? -8 : 8, y: 0 },
    alive: true,
    destroyable: false,
    points: 0,
  });
  if (p.doubleShot) {
    projectiles.push({
      id: `blaster-double-${Date.now()}-${Math.random()}`,
      type: 'blaster',
      position: { x: bx, y: p.position.y - 8 },
      velocity: { x: p.facingLeft ? -8 : 8, y: 0 },
      alive: true,
      destroyable: false,
      points: 0,
    });
  }
}

/** Throw a grenade */
export function fireGrenade(p: PlayerState, projectiles: Projectile[]): void {
  if (p.grenades <= 0 || !p.alive) return;
  p.grenades -= 1;
  const gx = p.facingLeft ? p.position.x - 8 : p.position.x + 8;
  projectiles.push({
    id: `grenade-${Date.now()}-${Math.random()}`,
    type: 'grenade',
    position: { x: gx, y: p.position.y },
    velocity: { x: p.facingLeft ? -4 : 4, y: -6 },
    alive: true,
    destroyable: true,
    points: 150,
  });
}

/** Kill the player (death → refill ammo, respawn at zone start) */
export function killPlayer(p: PlayerState): void {
  if (p.invincible) return;
  p.alive = false;
  p.lives -= 1;
  p.blasterAmmo = 99;
  p.grenades = 10;
  if (p.lives <= 0) {
    // game over — handled by GameState
  }
}

/** Respawn player at given position */
export function respawnPlayer(p: PlayerState, pos: Vec2): void {
  p.position = { ...pos };
  p.velocity = { x: 0, y: 0 };
  p.alive = true;
  p.invincible = true;
  p.invincibleTimer = 3000; // 3 seconds invincibility after respawn
}
