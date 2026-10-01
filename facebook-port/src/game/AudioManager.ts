/**
 * AudioManager — Web Audio API SFX/music
 * New subsystem — no audio in the original macOS build.
 *
 * Synthesizes simple beeps using Web Audio API OscillatorNode.
 * No external audio files required for MVP.
 */

import type { SfxEvent } from '../types/GameTypes';

export interface AudioManager {
  readonly supported: boolean;
  playSfx(event: SfxEvent): void;
  stopAll(): void;
  setVolume(volume: number): void;
}

export function createAudioManager(): AudioManager {
  let audioCtx: AudioContext | null = null;
  let volume = 0.5;

  function getContext(): AudioContext | null {
    if (!audioCtx) {
      try {
        audioCtx = new (window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext)();
      } catch {
        return null;
      }
    }
    return audioCtx;
  }

  function playSfx(event: SfxEvent): void {
    const ctx = getContext();
    if (!ctx) return;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = event.type === 'blaster' ? 'square' : 'sine';
    osc.frequency.value = event.frequency;
    gain.gain.value = event.volume * volume;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + event.duration);
  }

  function stopAll(): void {
    if (audioCtx) {
      audioCtx.close().catch(() => {});
      audioCtx = null;
    }
  }

  function setVolume(v: number): void {
    volume = Math.max(0, Math.min(1, v));
  }

  return {
    get supported() { return typeof AudioContext !== 'undefined' || typeof (window as unknown as { webkitAudioContext?: unknown }).webkitAudioContext !== 'undefined'; },
    playSfx,
    stopAll,
    setVolume,
  };
}
