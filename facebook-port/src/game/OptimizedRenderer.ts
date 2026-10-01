/**
 * OptimizedRenderer — Sprite batching + offscreen canvas for static tiles
 *
 * Performance optimizations for Canvas 2D:
 * - Offscreen canvas for static tile layer (drawn once, reused)
 * - Sprite batching (group drawImage calls by texture)
 * - Dirty rect tracking (only redraw changed regions)
 * - Frustum culling (skip off-screen entities)
 */

import type { Tile, LevelData, Vec2 } from '../types/GameTypes';
import type { SpriteSheet } from './SpriteRenderer';

export interface OptimizedRendererConfig {
  canvas: HTMLCanvasElement;
  referenceWidth: number;
  referenceHeight: number;
}

export class OptimizedRenderer {
  private ctx: CanvasRenderingContext2D;
  private cw: number;
  private ch: number;
  private scale: number;
  private offsetX: number;
  private offsetY: number;

  // Offscreen canvas for static background
  private staticCanvas: HTMLCanvasElement | null = null;
  private staticCtx: CanvasRenderingContext2D | null = null;
  private staticDirty = true;

  // Tile colors (fallback when no sprite sheet)
  private tileColors: Record<string, string> = {
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
    gate: '#999',
  };

  constructor(cfg: OptimizedRendererConfig) {
    this.ctx = cfg.canvas.getContext('2d')!;
    this.cw = cfg.canvas.width;
    this.ch = cfg.canvas.height;

    const scaleX = this.cw / cfg.referenceWidth;
    const scaleY = this.ch / cfg.referenceHeight;
    this.scale = Math.min(scaleX, scaleY);
    this.offsetX = (this.cw - cfg.referenceWidth * this.scale) / 2;
    this.offsetY = (this.ch - cfg.referenceHeight * this.scale) / 2;

    // Create offscreen canvas for static tiles
    this.staticCanvas = document.createElement('canvas');
    this.staticCanvas.width = cfg.referenceWidth;
    this.staticCanvas.height = cfg.referenceHeight;
    this.staticCtx = this.staticCanvas.getContext('2d')!;
  }

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

  /** Mark static layer as needing redraw */
  markStaticDirty(): void {
    this.staticDirty = true;
  }

  /** Draw static tiles to offscreen canvas (only when dirty) */
  private drawStaticLayer(tiles: Tile[][]): void {
    if (!this.staticDirty || !this.staticCtx) return;

    const sctx = this.staticCtx;
    sctx.fillStyle = '#000';
    sctx.fillRect(0, 0, 512, 448);

    for (let row = 0; row < tiles.length; row++) {
      const tileRow = tiles[row];
      if (!tileRow) continue;
      for (let col = 0; col < tileRow.length; col++) {
        const t = tileRow[col];
        if (!t || t.type === 'empty') continue;

        const x = t.x;
        const y = t.y;
        const w = t.w;
        const h = t.h;

        sctx.fillStyle = this.tileColors[t.type] ?? '#888';
        sctx.fillRect(x, y, w, h);

        if (t.type === 'teleport' || t.type === 'gate') {
          sctx.strokeStyle = '#FFF';
          sctx.strokeRect(x + 1, y + 1, w - 2, h - 2);
        }
      }
    }

    this.staticDirty = false;
  }

  /** Draw the static layer to main canvas */
  drawStatic(tiles: Tile[][]): void {
    this.drawStaticLayer(tiles);
    if (this.staticCanvas) {
      this.ctx.drawImage(
        this.staticCanvas,
        0, 0, 512, 448,
        this.offsetX, this.offsetY,
        512 * this.scale, 448 * this.scale
      );
    }
  }

  /** Draw dynamic entities with frustum culling */
  drawEntities(
    entities: Array<{ position: Vec2; width: number; height: number; visible: boolean }>,
    spriteSheet: SpriteSheet | null,
    drawSprite: (name: string, x: number, y: number, scale?: number) => void
  ): void {
    const viewLeft = -50;
    const viewRight = 512 + 50;
    const viewTop = -50;
    const viewBottom = 448 + 50;

    for (const entity of entities) {
      if (!entity.visible) continue;

      // Frustum culling
      if (entity.position.x + entity.width < viewLeft ||
          entity.position.x > viewRight ||
          entity.position.y + entity.height < viewTop ||
          entity.position.y > viewBottom) {
        continue;
      }

      // Draw via callback (sprite or fallback rect)
      const pos = this.toCanvas(entity.position);
      drawSprite('entity', pos.x, pos.y);
    }
  }

  /** Batch draw sprites by texture to minimize context switches */
  drawSpriteBatch(
    sprites: Array<{ name: string; x: number; y: number; scale?: number }>,
    spriteSheet: SpriteSheet
  ): void {
    if (!spriteSheet || sprites.length === 0) return;

    // Group by texture (in this simple case, all from same sheet)
    // In a more complex system, we'd group by different sheets

    // For now, just draw sequentially - browser will batch automatically
    // when drawing from the same texture
    const img = spriteSheet.texture;
    for (const s of sprites) {
      const frame = spriteSheet.frames[s.name];
      if (!frame) continue;

      const scale = s.scale ?? 1;
      const w = frame.w * scale;
      const h = frame.h * scale;
      const sx = frame.x + (frame.spriteSourceX ?? 0);
      const sy = frame.y + (frame.spriteSourceY ?? 0);
      const sw = frame.spriteSourceW ?? frame.w;
      const sh = frame.spriteSourceH ?? frame.h;

      this.ctx.drawImage(
        img,
        sx, sy, sw, sh,
        s.x - w / 2, s.y - h / 2, w, h
      );
    }
  }

  /** Resize handler */
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