/**
 * Weapons — blaster, grenade, launcher, rocket
 * Ported from Weapons/ and LauncherBonusState.
 *
 * Original rules:
 * - Blaster: finite ammo (99), destroys floating enemies/spheres/launcher rockets
 * - Grenade: fixed phase table trajectory, 1 active at a time, destroys turrets
 * - Launcher rockets: 16x16, travel left, destroyable, 50 points
 * - Double launcher: fires from two barrels, stops when Vitorc too close
 */

import type { Projectile, WeaponType, Vec2 } from '../types/GameTypes';

export interface Weapons {
  activeProjectiles: Projectile[];
  grenadeActive: boolean;
  grenadeTimer: number;
  doubleLauncherActive: boolean;
  fireBlaster(playerPos: Vec2, facingLeft: boolean, ammo: number): Projectile | null;
  fireGrenade(playerPos: Vec2, facingLeft: boolean): Projectile | null;
  fireLauncher(playerPos: Vec2, facingLeft: boolean): Projectile | null;
  update(dtMs: number): void;
  clear(): void;
}

export function createWeapons(): Weapons {
  const activeProjectiles: Projectile[] = [];
  let grenadeActive = false;
  let grenadeTimer = 0;
  let doubleLauncherActive = false;

  function fireBlaster(
    playerPos: Vec2,
    facingLeft: boolean,
    ammo: number,
  ): Projectile | null {
    if (ammo <= 0) return null;
    const bx = facingLeft ? playerPos.x - 12 : playerPos.x + 12;
    const proj: Projectile = {
      id: `blaster-${Date.now()}-${Math.random()}`,
      type: 'blaster',
      position: { x: bx, y: playerPos.y - 8 },
      velocity: { x: facingLeft ? -8 : 8, y: 0 },
      alive: true,
      destroyable: false,
      points: 0,
    };
    activeProjectiles.push(proj);
    return proj;
  }

  function fireGrenade(playerPos: Vec2, facingLeft: boolean): Projectile | null {
    if (grenadeActive) return null;
    const gx = facingLeft ? playerPos.x - 8 : playerPos.x + 8;
    const proj: Projectile = {
      id: `grenade-${Date.now()}-${Math.random()}`,
      type: 'grenade',
      position: { x: gx, y: playerPos.y },
      velocity: { x: facingLeft ? -4 : 4, y: -6 },
      alive: true,
      destroyable: true,
      points: 150,
    };
    activeProjectiles.push(proj);
    grenadeActive = true;
    grenadeTimer = 0;
    return proj;
  }

  function fireLauncher(playerPos: Vec2, facingLeft: boolean): Projectile | null {
    const bx = facingLeft ? playerPos.x - 12 : playerPos.x + 12;
    const proj: Projectile = {
      id: `launcher-${Date.now()}-${Math.random()}`,
      type: 'launcher',
      position: { x: bx, y: playerPos.y - 8 },
      velocity: { x: facingLeft ? -6 : 6, y: -1 },
      alive: true,
      destroyable: true,
      points: 50,
    };
    activeProjectiles.push(proj);
    doubleLauncherActive = true;
    return proj;
  }

  function update(dtMs: number): void {
    // Update grenade trajectory (fixed phase table)
    if (grenadeActive) {
      grenadeTimer += dtMs;
      // Grenade follows fixed phase table for ~3 seconds then deactivates
      if (grenadeTimer > 3000) {
        grenadeActive = false;
      }
    }

    // Update projectile positions
    for (const proj of activeProjectiles) {
      if (!proj.alive) continue;
      proj.position.x += proj.velocity.x;
      proj.position.y += proj.velocity.y;

      // Gravity on grenades
      if (proj.type === 'grenade') {
        proj.velocity.y += 0.15;
      }

      // Remove if off screen
      if (proj.position.x < -50 || proj.position.x > 600
        || proj.position.y < -50 || proj.position.y > 500) {
        proj.alive = false;
        if (proj.type === 'grenade') grenadeActive = false;
      }
    }

    // Compact
    let w = 0;
    for (const p of activeProjectiles) {
      if (p.alive) activeProjectiles[w++] = p;
    }
    activeProjectiles.length = w;
  }

  function clear(): void {
    activeProjectiles.length = 0;
    grenadeActive = false;
    grenadeTimer = 0;
    doubleLauncherActive = false;
  }

  return {
    get activeProjectiles() { return activeProjectiles; },
    get grenadeActive() { return grenadeActive; },
    get doubleLauncherActive() { return doubleLauncherActive; },
    get grenadeTimer() { return grenadeTimer; },
    fireBlaster,
    fireGrenade,
    fireLauncher,
    update,
    clear,
  };
}
