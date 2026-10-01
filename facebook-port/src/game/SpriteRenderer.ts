/**
 * SpriteRenderer — Canvas 2D sprite sheet rendering
 * Ported from SKSpriteNode rendering.
 *
 * Sprite sheet format: JSON atlas + PNG sprite sheet
 * Atlas entry: { frame: { x, y, w, h }, rotated, trimmed, spriteSourceSize, sourceSize }
 *
 * Each sprite in the sheet is referenced by name, with frames that define the
 * clipped drawing region from the source PNG.
 */

import type { Vec2 } from '../types/GameTypes';

export interface SpriteFrame {
  name: string;
  x: number;
  y: number;
  w: number;
  h: number;
  rotated: boolean;
  trimmed: boolean;
  spriteSourceX: number;
  spriteSourceY: number;
  spriteSourceW: number;
  spriteSourceH: number;
}

export interface SpriteSheet {
  frames: Record<string, SpriteFrame>;
  texture: HTMLImageElement;
}

export class SpriteRenderer {
  private ctx: CanvasRenderingContext2D;
  private sheet: SpriteSheet;

  constructor(sheet: SpriteSheet, ctx: CanvasRenderingContext2D) {
    this.sheet = sheet;
    this.ctx = ctx;
  }

  drawSprite(
    name: string,
    x: number,
    y: number,
    angle: number = 0,
    flipX: boolean = false,
    flipY: boolean = false,
    scale: number = 1
  ): void {
    const frame = this.sheet.frames[name];
    if (!frame) {
      console.warn(`Sprite frame not found: ${name}`);
      return;
    }

    const { x: fx, y: fy, w: fw, h: fh } = frame;
    const img = this.sheet.texture;

    this.ctx.save();
    this.ctx.translate(x + fw / 2 * scale, y + fh / 2 * scale);
    if (angle !== 0) {
      this.ctx.rotate(angle);
    }
    if (flipX) this.ctx.scale(-1, 1);
    if (flipY) this.ctx.scale(1, -1);

    // Draw from the atlas frame rect
    const srcX = fx + (frame.spriteSourceX ?? 0);
    const srcY = fy + (frame.spriteSourceY ?? 0);
    const srcW = frame.spriteSourceW ?? fw;
    const srcH = frame.spriteSourceH ?? fh;

    this.ctx.drawImage(
      img,
      srcX, srcY, srcW, srcH,
      (fw / 2) * -scale,
      (fh / 2) * -scale,
      fw * scale,
      fh * scale
    );

    this.ctx.restore();
  }

  drawRotated(
    name: string,
    x: number,
    y: number,
    angle: number,
    flipX: boolean = false,
    flipY: boolean = false
  ): void {
    const frame = this.sheet.frames[name];
    if (!frame) return;

    const { x: fx, y: fy, w: fw, h: fh } = frame;
    const img = this.sheet.texture;

    this.ctx.save();
    this.ctx.translate(x + fw / 2, y + fh / 2);
    this.ctx.rotate(angle);
    if (flipX) this.ctx.scale(-1, 1);
    if (flipY) this.ctx.scale(1, -1);

    this.ctx.drawImage(
      img,
      fx, fy, fw, fh,
      -fw / 2,
      -fh / 2,
      fw,
      fh
    );

    this.ctx.restore();
  }
}