// Shared interfaces matching change-spec.yaml contracts for the Exolon port.
// All coordinate systems are in original-pixel space (512×448 reference) unless noted.

export interface Vec2 {
  x: number;
  y: number;
}

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Game flow states — mirrors GameState.swift flow enum */
export type GameFlowState =
  | 'title'
  | 'playing'
  | 'paused'
  | 'dying'
  | 'stage_bonus'
  | 'game_over'
  | 'stage_complete';

/** Player state */
export interface PlayerState {
  position: Vec2;
  velocity: Vec2;
  lives: number;
  blasterAmmo: number;
  grenades: number;
  hasExoskeleton: boolean;
  exoskeletonStage: number; // 0–4, cleared at stage end
  doubleShot: boolean;
  invincible: boolean; // TEST INVULNERABILITY flag (non-original)
  invincibleTimer: number;
  facingLeft: boolean;
  alive: boolean;
}

/** Weapon types */
export type WeaponType = 'blaster' | 'grenade' | 'launcher' | 'rocket';

/** Active projectile */
export interface Projectile {
  id: string;
  type: WeaponType;
  position: Vec2;
  velocity: Vec2;
  alive: boolean;
  destroyable: boolean; // blaster can destroy this
  points: number;
}

/** Enemy types from tab_enemy */
export type EnemyType =
  | 'flying_1' | 'flying_2' | 'flying_3'
  | 'flying_4' | 'flying_5' | 'flying_6'
  | 'sphere' | 'rocket_tower';

export interface Enemy {
  id: string;
  type: EnemyType;
  position: Vec2;
  velocity: Vec2;
  alive: boolean;
  trajectoryPhase: number;
  spawnDelay: number;
  points: number;
}

/** Level tile types (from TMX action markers) */
export type TileType =
  | 'empty' | 'solid' | 'destroyable'
  | 'turret' | 'mine' | 'teleport'
  | 'ammo_box' | 'grenade_box'
  | 'sphere_home' | 'pump'
  | 'rocket_launcher' | 'changing_room'
  | 'beacon' | 'force_field'
  | 'stage_end' | 'torch' | 'flashing';

export interface Tile {
  type: TileType;
  x: number;
  y: number;
  w: number;
  h: number;
  meta?: Record<string, unknown>;
}

/** Level data (converted from TMX → JSON) */
export interface LevelData {
  zoneNumber: number;
  stage: number;
  width: number;
  height: number;
  tiles: Tile[][];
  playerStart: Vec2;
  actionMarkers: Vec2[];
}

/** Gameplay event log record (mirrors Wave A event log contract) */
export interface GameplayEvent {
  tick: number;
  type: string;
  payload: Record<string, unknown>;
}

/** Input state aggregated from Keyboard + Gamepad APIs */
export interface InputState {
  left: boolean;
  right: boolean;
  up: boolean;
  down: boolean;
  fire: boolean;
  grenade: boolean;
  pause: boolean;
  uiUp: boolean;
  firePressed: boolean;   // edge-triggered
  grenadePressed: boolean; // edge-triggered
  uiUpPressed: boolean;    // edge-triggered
}

/** Audio event — Web Audio API synthesis params */
export interface SfxEvent {
  type: 'blaster' | 'grenade' | 'explosion' | 'teleport' | 'stage_end' | 'pickup';
  frequency: number;
  duration: number;
  volume: number;
}

/** Score snapshot for persistence */
export interface ScoreSnapshot {
  score: number;
  highScore: number;
  lives: number;
  stage: number;
  zoneInStage: number;
}
