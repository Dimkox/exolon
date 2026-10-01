/**
 * TouchControls — Virtual joystick + buttons for mobile Facebook Gaming
 *
 * Creates overlay touch controls that work alongside keyboard/gamepad input.
 * Joystick for movement, buttons for fire/grenade/up/pause.
 */

import type { InputState } from '../types/GameTypes';

export interface TouchControls {
  element: HTMLElement;
  destroy(): void;
}

interface JoystickState {
  active: boolean;
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
  id: number | null;
}

interface ButtonState {
  pressed: boolean;
  id: number | null;
}

const JOYSTICK_RADIUS = 60;
const JOYSTICK_THUMB_RADIUS = 25;
const BUTTON_SIZE = 60;

export function createTouchControls(inputState: InputState): TouchControls {
  const container = document.createElement('div');
  container.id = 'touch-controls';
  container.style.cssText = `
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 1000;
    touch-action: none;
  `;

  // Left joystick
  const joystick = document.createElement('div');
  joystick.id = 'touch-joystick';
  joystick.style.cssText = `
    position: absolute;
    left: 20px;
    bottom: 20px;
    width: ${JOYSTICK_RADIUS * 2}px;
    height: ${JOYSTICK_RADIUS * 2}px;
    border: 2px solid rgba(255,255,255,0.3);
    border-radius: 50%;
    background: rgba(0,0,0,0.3);
    pointer-events: auto;
    touch-action: none;
  `;

  const joystickThumb = document.createElement('div');
  joystickThumb.style.cssText = `
    position: absolute;
    top: 50%;
    left: 50%;
    width: ${JOYSTICK_THUMB_RADIUS * 2}px;
    height: ${JOYSTICK_THUMB_RADIUS * 2}px;
    border-radius: 50%;
    background: rgba(255,255,255,0.6);
    transform: translate(-50%, -50%);
    pointer-events: none;
    transition: transform 0.05s linear;
  `;
  joystick.appendChild(joystickThumb);

  // Right buttons container
  const buttonsContainer = document.createElement('div');
  buttonsContainer.id = 'touch-buttons';
  buttonsContainer.style.cssText = `
    position: absolute;
    right: 20px;
    bottom: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    pointer-events: auto;
    touch-action: none;
  `;

  // Fire button (large, bottom-right)
  const fireBtn = createButton('fire', 'FIRE', '#FF4444');
  fireBtn.style.width = `${BUTTON_SIZE * 1.2}px`;
  fireBtn.style.height = `${BUTTON_SIZE * 1.2}px`;
  fireBtn.style.fontSize = '14px';
  fireBtn.style.borderRadius = '50%';

  // Grenade button (above fire)
  const grenadeBtn = createButton('grenade', 'GRENADE', '#FFAA00');
  grenadeBtn.style.width = `${BUTTON_SIZE}px`;
  grenadeBtn.style.height = `${BUTTON_SIZE}px`;
  grenadeBtn.style.fontSize = '11px';
  grenadeBtn.style.borderRadius = '50%';

  // Up button (above grenade)
  const upBtn = createButton('uiUp', 'UP', '#44AAFF');
  upBtn.style.width = `${BUTTON_SIZE}px`;
  upBtn.style.height = `${BUTTON_SIZE}px`;
  upBtn.style.fontSize = '12px';
  upBtn.style.borderRadius = '50%';

  // Pause button (top-right)
  const pauseBtn = createButton('pause', '||', '#888888');
  pauseBtn.style.position = 'absolute';
  pauseBtn.style.top = '20px';
  pauseBtn.style.right = '20px';
  pauseBtn.style.width = `${BUTTON_SIZE}px`;
  pauseBtn.style.height = `${BUTTON_SIZE}px`;
  pauseBtn.style.borderRadius = '8px';

  buttonsContainer.appendChild(grenadeBtn);
  buttonsContainer.appendChild(fireBtn);
  buttonsContainer.appendChild(upBtn);

  container.appendChild(joystick);
  container.appendChild(buttonsContainer);
  container.appendChild(pauseBtn);
  document.body.appendChild(container);

  // Joystick state
  const joyState: JoystickState = {
    active: false,
    startX: 0,
    startY: 0,
    currentX: 0,
    currentY: 0,
    id: null,
  };

  // Button states
  const btnStates: Record<string, ButtonState> = {
    fire: { pressed: false, id: null },
    grenade: { pressed: false, id: null },
    uiUp: { pressed: false, id: null },
    pause: { pressed: false, id: null },
  };

  function createButton(action: string, label: string, color: string): HTMLButtonElement {
    const btn = document.createElement('button');
    btn.dataset.action = action;
    btn.textContent = label;
    btn.style.cssText = `
      border: 2px solid ${color};
      background: rgba(0,0,0,0.5);
      color: ${color};
      font-family: monospace;
      font-weight: bold;
      display: flex;
      align-items: center;
      justify-content: center;
      pointer-events: auto;
      touch-action: none;
      user-select: none;
    `;
    return btn;
  }

  function updateJoystickVisual(): void {
    const dx = joyState.currentX - joyState.startX;
    const dy = joyState.currentY - joyState.startY;
    const dist = Math.hypot(dx, dy);
    const maxDist = JOYSTICK_RADIUS - JOYSTICK_THUMB_RADIUS;

    if (dist > maxDist) {
      const angle = Math.atan2(dy, dx);
      joyState.currentX = joyState.startX + Math.cos(angle) * maxDist;
      joyState.currentY = joyState.startY + Math.sin(angle) * maxDist;
    }

    const offsetX = joyState.currentX - joyState.startX;
    const offsetY = joyState.currentY - joyState.startY;
    joystickThumb.style.transform = `translate(calc(-50% + ${offsetX}px), calc(-50% + ${offsetY}px))`;
  }

  function updateInputFromJoystick(): void {
    const dx = joyState.currentX - joyState.startX;
    const dy = joyState.currentY - joyState.startY;
    const deadzone = 15;

    if (Math.abs(dx) > deadzone) {
      inputState.left = dx < 0;
      inputState.right = dx > 0;
    } else {
      inputState.left = false;
      inputState.right = false;
    }

    if (Math.abs(dy) > deadzone) {
      inputState.up = dy < 0;
      inputState.down = dy > 0;
    } else {
      inputState.up = false;
      inputState.down = false;
    }
  }

  function setButton(action: string, pressed: boolean): void {
    const state = btnStates[action];
    if (!state) return;

    const wasPressed = state.pressed;
    state.pressed = pressed;

    // Edge-triggered
    if (pressed && !wasPressed) {
      if (action === 'fire') inputState.firePressed = true;
      if (action === 'grenade') inputState.grenadePressed = true;
      if (action === 'uiUp') inputState.uiUpPressed = true;
    }

    // Sustained state
    inputState[action as keyof InputState] = pressed;

    // Visual feedback
    const btn = container.querySelector(`[data-action="${action}"]`) as HTMLElement | null;
    if (btn) {
      btn.style.background = pressed ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.5)';
      btn.style.transform = pressed ? 'scale(0.95)' : 'scale(1)';
    }
  }

  // Joystick touch handlers
  joystick.addEventListener('touchstart', (e) => {
    e.preventDefault();
    const touch = e.changedTouches[0];
    const rect = joystick.getBoundingClientRect();
    joyState.startX = touch.clientX - rect.left - JOYSTICK_RADIUS;
    joyState.startY = touch.clientY - rect.top - JOYSTICK_RADIUS;
    joyState.currentX = joyState.startX;
    joyState.currentY = joyState.startY;
    joyState.active = true;
    joyState.id = touch.identifier;
    updateJoystickVisual();
    updateInputFromJoystick();
  }, { passive: false });

  joystick.addEventListener('touchmove', (e) => {
    e.preventDefault();
    for (const touch of e.changedTouches) {
      if (touch.identifier === joyState.id) {
        const rect = joystick.getBoundingClientRect();
        joyState.currentX = touch.clientX - rect.left - JOYSTICK_RADIUS;
        joyState.currentY = touch.clientY - rect.top - JOYSTICK_RADIUS;
        updateJoystickVisual();
        updateInputFromJoystick();
        break;
      }
    }
  }, { passive: false });

  joystick.addEventListener('touchend', (e) => {
    e.preventDefault();
    for (const touch of e.changedTouches) {
      if (touch.identifier === joyState.id) {
        joyState.active = false;
        joyState.id = null;
        joyState.currentX = joyState.startX;
        joyState.currentY = joyState.startY;
        updateJoystickVisual();
        inputState.left = false;
        inputState.right = false;
        inputState.up = false;
        inputState.down = false;
        break;
      }
    }
  }, { passive: false });

  joystick.addEventListener('touchcancel', (e) => {
    for (const touch of e.changedTouches) {
      if (touch.identifier === joyState.id) {
        joyState.active = false;
        joyState.id = null;
        joyState.currentX = joyState.startX;
        joyState.currentY = joyState.startY;
        updateJoystickVisual();
        inputState.left = false;
        inputState.right = false;
        inputState.up = false;
        inputState.down = false;
        break;
      }
    }
  }, { passive: false });

  // Button touch handlers
  function attachButtonHandlers(btn: HTMLButtonElement, action: string): void {
    btn.addEventListener('touchstart', (e) => {
      e.preventDefault();
      const touch = e.changedTouches[0];
      btnStates[action].id = touch.identifier;
      setButton(action, true);
    }, { passive: false });

    btn.addEventListener('touchend', (e) => {
      e.preventDefault();
      for (const touch of e.changedTouches) {
        if (touch.identifier === btnStates[action].id) {
          btnStates[action].id = null;
          setButton(action, false);
          break;
        }
      }
    }, { passive: false });

    btn.addEventListener('touchcancel', (e) => {
      for (const touch of e.changedTouches) {
        if (touch.identifier === btnStates[action].id) {
          btnStates[action].id = null;
          setButton(action, false);
          break;
        }
      }
    }, { passive: false });

    // Mouse support for desktop testing
    btn.addEventListener('mousedown', (e) => {
      e.preventDefault();
      setButton(action, true);
    });
    btn.addEventListener('mouseup', (e) => {
      e.preventDefault();
      setButton(action, false);
    });
    btn.addEventListener('mouseleave', (e) => {
      setButton(action, false);
    });
  }

  attachButtonHandlers(fireBtn, 'fire');
  attachButtonHandlers(grenadeBtn, 'grenade');
  attachButtonHandlers(upBtn, 'uiUp');
  attachButtonHandlers(pauseBtn, 'pause');

  return {
    element: container,
    destroy() {
      container.remove();
    },
  };
}