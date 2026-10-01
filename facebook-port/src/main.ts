/**
 * Exolon — Facebook Gaming Instant Games (HTML5)
 * Entry point / composition root
 *
 * Boot sequence:
 *  1. FB Instant Games SDK init → player ID
 *  2. Compose game subsystems
 *  3. Start fixed-tick game loop
 *  4. Render loop interpolated via requestAnimationFrame
 */

import { createInstantGames } from './fb/InstantGames';
import { createFixedTickDriver } from './game/GameLoop';
import { createGameState } from './game/GameState';
import { Renderer } from './game/Renderer';
import { createPlayer, updatePlayer, fireBlaster, fireGrenade, killPlayer, respawnPlayer } from './game/Player';
import { createInputManager } from './game/InputManager';
import { createLevelManager } from './game/LevelManager';
import { createEnemyManager } from './game/Entities';
import { createWeapons } from './game/Weapons';
import { createStageBoundary } from './game/StageBoundary';
import { createLauncherBonus } from './game/LauncherBonus';
import { createAudioManager } from './game/AudioManager';
import { createPersistence } from './game/Persistence';
import type { GameFlowState, LevelData } from './types/GameTypes';

const FB_SDK_URL = 'https://connect.facebook.net/en_US/fbinstant.6.2.js';
const LEADERBOARD_ID = 'exolon_high_score';

async function main(): Promise<void> {
  const loadingEl = document.getElementById('loading')!;
  const progressEl = document.getElementById('progress') as HTMLDivElement;

  // ── Phase 1: FB Instant Games SDK ──
  const ig = await createInstantGames();
  await ig.initialize({
    sdkUrl: FB_SDK_URL,
    leaderboardID: LEADERBOARD_ID,
    onProgress: (p) => { progressEl.style.width = `${p}%`; },
  });
  await ig.launch();

  const player = await ig.sdk.getPlayer();
  console.log(`Exolon — player: ${player.playerID}`);

  // ── Phase 2: Compose game ──
  const canvas = document.getElementById('game-canvas') as HTMLCanvasElement;
  const renderer = new Renderer({ canvas, referenceWidth: 512, referenceHeight: 448 });
  const gameState = createGameState();
  const input = createInputManager(() => {}, () => {});
  const levelManager = createLevelManager();
  const enemyManager = createEnemyManager();
  const weapons = createWeapons();
  const stageBoundary = createStageBoundary();
  const launcherBonus = createLauncherBonus();
  const audio = createAudioManager();
  const persistence = createPersistence();

  const playerState = createPlayer({ x: 16, y: 112 });

  let currentLevel: LevelData | null = null;
  let levelWidth = 512;
  let levelHeight = 448;

  // Load initial level
  currentLevel = await levelManager.loadZone(0);

  // ── Phase 3: Fixed-tick game loop ──
  function getSnapshot() {
    const gs = gameState.snapshot();
    return {
      flow: gameState.flow,
      score: gs.score,
      lives: gs.lives,
      stage: gs.stage,
      zoneInStage: gs.zoneInStage,
      playerAlive: playerState.alive,
    };
  }

  async function onTick(dtMs: number, _snapshot: ReturnType<typeof getSnapshot>): Promise<void> {
    input.update();

    const state = gameState;
    if (state.flow !== 'playing') return;

    // Ensure level loaded
    if (!currentLevel) {
      currentLevel = await levelManager.loadZone(0);
    }
    const level = currentLevel;
    if (!level) return;

    levelWidth = level.width;
    levelHeight = level.height;

    // Player update
    const inp = input.state;
    updatePlayer(playerState, inp, level.tiles, levelWidth, levelHeight, dtMs);

    // Edge-triggered actions
    if (inp.firePressed && playerState.blasterAmmo > 0) {
      fireBlaster(playerState, weapons.activeProjectiles);
      audio.playSfx({ type: 'blaster', frequency: 440, duration: 0.05, volume: 0.3 });
    }
    if (inp.grenadePressed && playerState.grenades > 0) {
      fireGrenade(playerState, weapons.activeProjectiles);
      audio.playSfx({ type: 'grenade', frequency: 200, duration: 0.15, volume: 0.4 });
    }

    // Update weapons
    weapons.update(dtMs);

    // Update enemies
    enemyManager.update(dtMs, playerState.position, levelManager.currentZone, levelWidth);

    // Launcher bonus region check
    launcherBonus.checkBonus(playerState.position);

    // Stage end check
    if (levelManager.isStageEnd(levelManager.currentZone)) {
      const bonus = stageBoundary.triggerBonus(
        levelManager.currentZone,
        playerState.lives,
        playerState.hasExoskeleton,
        gameState.stage,
      );
      if (bonus.lifeAwarded) {
        state.addScore(bonus.bonusPoints + bonus.braveryPoints + bonus.timedPoints);
        gameState.gainLife();
        audio.playSfx({ type: 'stage_end', frequency: 880, duration: 0.3, volume: 0.5 });
      }
    }

    // Player death → respawn
    if (!playerState.alive) {
      playerState.blasterAmmo = 99;
      playerState.grenades = 10;
      weapons.clear();
      enemyManager.clear();
      launcherBonus.reset();
      respawnPlayer(playerState, level.playerStart);
      if (playerState.lives <= 0) {
        state.setFlow('game_over');
        persistence.saveHighScore(state.score);
      }
    }

    // Clean dead projectiles
    let w = 0;
    for (const p of weapons.activeProjectiles) {
      if (p.alive) weapons.activeProjectiles[w++] = p;
    }
    weapons.activeProjectiles.length = w;

    // Save high score periodically
    if (state.score > persistence.highScore) {
      persistence.saveHighScore(state.score);
    }
  }

  function onRender(alpha: number, _snapshot: ReturnType<typeof getSnapshot>): void {
    renderer.clear();

    const state = gameState;
    const level = currentLevel;

    if (level) {
      renderer.drawTiles(level.tiles);
    }
    renderer.drawPlayer(playerState);
    renderer.drawProjectiles(weapons.activeProjectiles);
    renderer.drawEnemies(enemyManager.enemies);
    renderer.drawHUD(state.score, state.lives, state.stage, state.zoneInStage);

    // Flow overlays
    if (state.flow === 'title') {
      renderer.drawOverlay('EXOLON', 'Press Space to start');
    } else if (state.flow === 'paused') {
      renderer.drawOverlay('PAUSED', 'Press Escape to resume');
    } else if (state.flow === 'game_over') {
      renderer.drawOverlay('GAME OVER', `Score: ${state.score} — Press R`);
    } else if (state.flow === 'stage_bonus') {
      renderer.drawOverlay('STAGE BONUS', 'Press Space to continue');
    }

    // Clear edge-triggered flags
    input.state.firePressed = false;
    input.state.grenadePressed = false;
    input.state.uiUpPressed = false;
  }

  const driver = createFixedTickDriver(getSnapshot, onTick, onRender);
  driver.onTick = onTick;
  driver.onRender = onRender;
  driver.start();

  // ── Loading complete ──
  loadingEl.classList.add('hidden');

  // ── Keyboard handling for pause / restart ──
  document.addEventListener('keydown', async (e) => {
    if (e.code === 'Escape' && gameState.flow === 'playing') {
      gameState.setFlow('paused');
    } else if (e.code === 'Escape' && gameState.flow === 'paused') {
      gameState.setFlow('playing');
    } else if (e.code === 'Space' && gameState.flow === 'title') {
      gameState.setFlow('playing');
    } else if (e.code === 'Space' && gameState.flow === 'stage_bonus') {
      gameState.nextZone();
      currentLevel = await levelManager.loadZone(gameState.zoneInStage + gameState.stage * 25);
      gameState.setFlow('playing');
    } else if (e.code === 'KeyR' && gameState.flow === 'game_over') {
      gameState.resetStage();
      currentLevel = await levelManager.loadZone(0);
      respawnPlayer(playerState, { x: 16, y: 112 });
    }
  });
}

main().catch((err) => {
  console.error('Exolon boot failed:', err);
  document.getElementById('loading')!.textContent = `Error: ${err.message}`;
});
