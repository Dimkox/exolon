/**
 * Renderer — Canvas 2D drawing
 * Ported from SKScene + SKNode rendering → single <canvas> 2D context.
 *
 * All coordinates in original-pixel space (512×448 reference), scaled to
 * the canvas size while preserving aspect ratio.
 */

import type { LevelData, PlayerState, Enemy, Projectile, Tile, Vec2 } from '../types/GameTypes';

export interface RendererConfig {
  canvas: HTMLCanvasElement;
  referenceWidth: number;
  referenceHeight: number;
}

export interface DrawOptions {
  showHitboxes: boolean;
  showTiles: boolean;
}

const DEFAULT_OPTIONS: DrawOptions = { showHitboxes: false, showTiles: true };

export class Renderer {
  private ctx: CanvasRenderingContext2D;
  private cw: number;
  private ch: number;
  private scale: number;
  private offsetX: number;
  private offsetY: number;

  constructor(cfg: RendererConfig) {
    this.ctx = cfg.canvas.getContext('2d')!;
    this.cw = cfg.canvas.width;
    this.ch = cfg.canvas.height;

    // Fit reference into canvas preserving aspect ratio
    const scaleX = this.cw / cfg.referenceWidth;
    const scaleY = this.ch / cfg.referenceHeight;
    this.scale = Math.min(scaleX, scaleY);
    this.offsetX = (this.cw - cfg.referenceWidth * this.scale) / 2;
    this.offsetY = (this.ch - cfg.referenceHeight * this.scale) / 2;
  }

  clear(): void {
    this.ctx.fillStyle = '#000';
    this.ctx.fillRect(0, 0, this.cw, this.ch);
  }

  /** Convert original-pixel coords to canvas pixels */
  private toCanvas(v: Vec2): Vec2 {
    return {
      x: this.offsetX + v.x * this.scale,
      y: this.offsetY + v.y * this.scale,
    };
  }

  private rectToCanvas(x: number, y: number, w: number, h: number): DOMRect {
    return new DOMRect(
      this.offsetX + x * this.scale,
      this.offsetY + y * this.scale,
      w * this.scale,
      h * this.scale,
    );
  }

  drawTiles(tiles: Tile[][]): void {
    const colors: Record<string, string> = {
      solid: '#555',
      destroyable: '#8B4513',
      turret: '#666',
      mine: '#f44',
      ammo_box: '#fff',
      grenade_box: '#FF0',
      sphere_home: '#0AF',
      pump: '#A52A2A',
      rocket_launcher: '#888',
      changing_room: '#0F0',
      beacon: '#0F0',
      force_field: '#0FF',
      stage_end: '#FF0',
      torch: '#F80',
      flashing: '#F0F',
      teleport: '#C0F',
    };

    for (let row = 0; row < tiles.length; row++) {
      const tileRow = tiles[row];
      if (!tileRow) continue;
      for (let col = 0; col < tileRow.length; col++) {
        const t = tileRow[col];
        if (!t || t.type === 'empty') continue;
        const r = this.rectToCanvas(t.x, t.y, t.w, t.h);
        this.ctx.fillStyle = colors[t.type] ?? '#888';
        this.ctx.fillRect(r.x, r.y, r.width, r.height);
        if (t.type === 'teleport') {
          this.ctx.strokeStyle = '#FFF';
          this.ctx.strokeRect(r.x + 1, r.y + 1, r.width - 2, r.height - 2);
        }
      }
    }
  }

  drawPlayer(p: PlayerState): void {
    const pos = this.toCanvas(p.position);
    const size = 16 * this.scale;
    this.ctx.fillStyle = p.hasExoskeleton ? '#0CF' : '#0AF';
    this.ctx.fillRect(pos.x - size / 2, pos.y - size / 2, size, size);
    if (p.doubleShot) {
      this.ctx.fillStyle = '#FF0';
      this.ctx.fillRect(pos.x - size / 2 - 4 * this.scale, pos.y, 4 * this.scale, size);
      this.ctx.fillRect(pos.x + size / 2, pos.y, 4 * this.scale, size);
    }
    if (p.invincible) {
      this.ctx.strokeStyle = '#FFF';
      this.ctx.lineWidth = 2;
      this.ctx.strokeRect(pos.x - size / 2 - 2, pos.y - size / 2 - 2, size + 4, size + 4);
    }
  }

  drawProjectiles(projectiles: Projectile[]): void {
    for (const proj of projectiles) {
      if (!proj.alive) continue;
      const pos = this.toCanvas(proj.position);
      this.ctx.fillStyle = proj.destroyable ? '#FF0' : '#F44';
      const s = (proj.type === 'grenade' ? 8 : 4) * this.scale;
      this.ctx.fillRect(pos.x - s / 2, pos.y - s / 2, s, s);
    }
  }

  drawEnemies(enemies: Enemy[]): void {
    for (const e of enemies) {
      if (!e.alive) continue;
      const pos = this.toCanvas(e.position);
      this.ctx.fillStyle = '#F00';
      const s = 14 * this.scale;
      this.ctx.fillRect(pos.x - s / 2, pos.y - s / 2, s, s);
    }
  }

  drawHUD(score: number, lives: number, stage: number, zoneInStage: number): void {
    this.ctx.fillStyle = '#FFF';
    this.ctx.font = `${14 * this.scale}px monospace`;
    this.ctx.fillText(`Score: ${score}`, 8 * this.scale, 20 * this.scale);
    this.ctx.fillText(`Lives: ${lives}`, 8 * this.scale, 38 * this.scale);
    this.ctx.fillText(`Stage: ${stage + 1}/5 Zone: ${zoneInStage + 1}/25`, 8 * this.scale, 56 * this.scale);
  }

  drawOverlay(text: string, subtext?: string): void {
    this.ctx.fillStyle = 'rgba(0,0,0,0.6)';
    this.ctx.fillRect(0, 0, this.cw, this.ch);
    this.ctx.fillStyle = '#FFF';
    this.ctx.font = `bold ${24 * this.scale}px monospace`;
    this.ctx.textAlign = 'center';
    this.ctx.fillText(text, this.cw / 2, this.ch / 2 - 10 * this.scale);
    if (subtext) {
      this.ctx.font = `${14 * this.scale}px monospace`;
      this.ctx.fillText(subtext, this.cw / 2, this.ch / 2 + 16 * this.scale);
    }
    this.ctx.textAlign = 'start';
  }

  resize(w: number, h: number): void {
    this.cw = w;
    this.ch = h;
    const scaleX = this.cw / 512;
    const scaleY = this.ch / 448;
    this.scale = Math.min(scaleX, scaleY);
    this.offsetX = (this.cw - 512 * this.scale) / 2;
    this.offsetY = (this.ch - 448 * this.scale) / 2;
  }
}
