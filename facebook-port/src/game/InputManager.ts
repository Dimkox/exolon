/**
 * InputManager — Keyboard + Gamepad API → InputState
 * Replaces NSEvent (macOS) / GC (GameController) from the SpriteKit original.
 *
 * Edge-triggered fire/grenade/up so actions fire once per press.
 */

import type { InputState } from '../types/GameTypes';

const DEFAULT_INPUT: InputState = {
  left: false, right: false, up: false, down: false,
  fire: false, grenade: false, pause: false,
  uiUp: false,
  firePressed: false, grenadePressed: false, uiUpPressed: false,
};

export interface InputManager {
  readonly state: InputState;
  update(): void;
  reset(): void;
  destroy(): void;
}

export function createInputManager(
  onKeyDown: (e: KeyboardEvent) => void,
  onKeyUp: (e: KeyboardEvent) => void,
): InputManager {
  const prev = { ...DEFAULT_INPUT };
  const current = { ...DEFAULT_INPUT };

  function keyToAction(code: string): keyof InputState | null {
    switch (code) {
      case 'ArrowLeft': case 'KeyA': return 'left';
      case 'ArrowRight': case 'KeyD': return 'right';
      case 'ArrowUp': case 'KeyW': return 'up';
      case 'ArrowDown': case 'KeyS': return 'down';
      case 'Space': case 'KeyJ': return 'fire';
      case 'KeyK': return 'grenade';
      case 'Escape': case 'KeyP': return 'pause';
      case 'Enter': case 'KeyU': return 'uiUp';
      default: return null;
    }
  }

  function handleDown(e: KeyboardEvent): void {
    const action = keyToAction(e.code);
    if (action && !current[action]) {
      current[action] = true;
      // Edge-triggered
      if (action === 'fire') current.firePressed = true;
      if (action === 'grenade') current.grenadePressed = true;
      if (action === 'uiUp') current.uiUpPressed = true;
    }
    onKeyDown(e);
  }

  function handleUp(e: KeyboardEvent): void {
    const action = keyToAction(e.code);
    if (action) current[action] = false;
    onKeyUp(e);
  }

  // Gamepad polling (navigator.getGamepads)
  let gamepadIndex = -1;

  function pollGamepad(): void {
    const gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
    for (let i = 0; i < gamepads.length; i++) {
      const gp = gamepads[i];
      if (!gp) continue;
      // Connect first found gamepad
      if (gamepadIndex === -1) gamepadIndex = i;
      if (i !== gamepadIndex) continue;

      const axes = gp.axes;
      const buttons = gp.buttons;

      current.left = axes[0] < -0.5;
      current.right = axes[0] > 0.5;
      current.up = axes[1] < -0.5;
      current.down = axes[1] > 0.5;
      current.fire = !!buttons[0]?.pressed;
      current.grenade = !!buttons[1]?.pressed;
      current.pause = !!buttons[8]?.pressed;
      current.uiUp = !!buttons[12]?.pressed;

      // Edge-triggered from buttons
      if (buttons[0]?.pressed && !prev.fire) current.firePressed = true;
      if (buttons[1]?.pressed && !prev.grenade) current.grenadePressed = true;
      if (buttons[12]?.pressed && !prev.uiUp) current.uiUpPressed = true;
      return;
    }
    gamepadIndex = -1;
  }

  function clearEdges(): void {
    current.firePressed = false;
    current.grenadePressed = false;
    current.uiUpPressed = false;
  }

  document.addEventListener('keydown', handleDown);
  document.addEventListener('keyup', handleUp);

  return {
    get state() { return { ...current }; },
    update() {
      pollGamepad();
    },
    reset() {
      Object.assign(current, DEFAULT_INPUT);
      Object.assign(prev, DEFAULT_INPUT);
    },
    destroy() {
      document.removeEventListener('keydown', handleDown);
      document.removeEventListener('keyup', handleUp);
    },
  };
}
