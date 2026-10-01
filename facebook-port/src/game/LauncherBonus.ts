/**
 * LauncherBonus — double launcher logic
 * Ported from LauncherBonusState.
 *
 * Crossing the launcher's invisible bonus region awards 1000 points once.
 * Launcher stops firing when Vitorc (player) is too close.
 */

export interface LauncherBonusState {
  bonusAwarded: boolean;
  bonusRegionX: number;
  bonusRegionY: number;
  bonusRegionWidth: number;
  bonusRegionHeight: number;
  playerInRegion: boolean;
  reset(): void;
  checkBonus(playerPos: { x: number; y: number }): number; // returns points awarded (0 or 1000)
  setRegion(x: number, y: number, w: number, h: number): void;
}

export function createLauncherBonus(): LauncherBonusState {
  let bonusAwarded = false;
  let bonusRegionX = 0;
  let bonusRegionY = 0;
  let bonusRegionWidth = 0;
  let bonusRegionHeight = 0;
  let playerInRegion = false;

  function reset(): void {
    bonusAwarded = false;
    playerInRegion = false;
  }

  function checkBonus(playerPos: { x: number; y: number }): number {
    const inX = playerPos.x >= bonusRegionX
      && playerPos.x <= bonusRegionX + bonusRegionWidth;
    const inY = playerPos.y >= bonusRegionY
      && playerPos.y <= bonusRegionY + bonusRegionHeight;

    playerInRegion = inX && inY;

    if (playerInRegion && !bonusAwarded) {
      bonusAwarded = true;
      return 1000;
    }
    return 0;
  }

  function setRegion(x: number, y: number, w: number, h: number): void {
    bonusRegionX = x;
    bonusRegionY = y;
    bonusRegionWidth = w;
    bonusRegionHeight = h;
    bonusAwarded = false;
  }

  return {
    get bonusAwarded() { return bonusAwarded; },
    get playerInRegion() { return playerInRegion; },
    get bonusRegionX() { return bonusRegionX; },
    get bonusRegionY() { return bonusRegionY; },
    get bonusRegionWidth() { return bonusRegionWidth; },
    get bonusRegionHeight() { return bonusRegionHeight; },
    reset,
    checkBonus,
    setRegion,
  };
}
