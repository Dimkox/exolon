/**
 * TMXTileRenderer — Canvas 2D tile rendering from TMX-converted JSON.
 *
 * TMX → JSON conversion produces: { zones: number, width: number, height: number,
 * tiles: Tile[][], playerStart: Vec2, actionMarkers: Vec2[] }
 *
 * Original TMX uses:
 * - Tile definitions: tilesets with tilewidth/tileheight, image source, margin, spacing
 * - Action markers: objectgroups with x, y, width, height, and properties
 * - Multiple layers: background, foreground, collision, etc.
 *
 * The converter keeps: solid/destroyable/turret/mine/teleport/etc. tile types,
 * plus all action marker properties for gameplay logic.
 */

import type { Tile, LevelData, Vec2 } from '../types/GameTypes';

export interface TMXLayer {
  name: string;
  tiles: number[][]; // tile index grid, 0 = empty
  opacity: number;
  visible: boolean;
}

export interface TMXTileset {
  firstgid: number;
  source: string; // PNG sprite sheet path
  tilewidth: number;
  tileheight: number;
  margin: number;
  spacing: number;
}

export interface TMXObject {
  id: number;
  name: string;
  type?: string;
  x: number;
  y: number;
  width: number;
  height: number;
  properties: Record<string, unknown>;
}

export class TMXTileRenderer {
  private ctx: CanvasRenderingContext2D;
  private sheet: HTMLImageElement | null;
  private tileWidth: number;
  private tileHeight: number;
  private tilesets: Map<number, TMXTileset> = new Map();
  private layers: TMXLayer[] = [];

  constructor(ctx: CanvasRenderingContext2D, image: HTMLImageElement) {
    this.ctx = ctx;
    this.sheet = image;
    this.tileWidth = 25; // default, set from LevelData
    this.tileHeight = 30; // default
  }

  setTileWidth(w: number, h: number): void {
    this.tileWidth = w;
    this.tileHeight = h;
  }

  loadLevelData(level: LevelData): void {
    this.layers = [
      { name: 'background', tiles: Array.from({ length: level.tiles.length }, (_, i) =>
        Array.from({ length: level.tiles[i].length }, (_, j) => level.tiles[i][j].type !== 'empty' ? 1 : 0)
      ), opacity: 1, visible: true },
    ];
    // Build tilesets from level meta if available
  }

  /** Get the sheet X/Y index for a tile type */
  private getTileSheetPos(type: string): { sx: number; sy: number } {
    const typeMap: Record<string, { sx: number; sy: number }> = {
      solid: { sx: 0, sy: 0 },
      destroyable: { sx: 1, sy: 0 },
      turret: { sx: 2, sy: 0 },
      mine: { sx: 3, sy: 0 },
      teleport: { sx: 4, sy: 0 },
      ammo_box: { sx: 5, sy: 0 },
      grenade_box: { sx: 6, sy: 0 },
      sphere_home: { sx: 7, sy: 0 },
      pump: { sx: 8, sy: 0 },
      rocket_launcher: { sx: 9, sy: 0 },
      changing_room: { sx: 10, sy: 0 },
      beacon: { sx: 11, sy: 0 },
      force_field: { sx: 12, sy: 0 },
      stage_end: { sx: 13, sy: 0 },
      torch: { sx: 14, sy: 0 },
      flashing: { sx: 15, sy: 0 },
      gate: { sx: 16, sy: 0 },
    };
    return typeMap[type] ?? { sx: 0, sy: 0 };
  }

  drawTiles(tiles: Tile[], canvasW: number, canvasH: number): void {
    if (!this.sheet) return;

    const scaleX = canvasW / 512;
    const scaleY = canvasH / 448;
    const cellW = this.tileWidth * scaleX;
    const cellH = this.tileHeight * scaleY;

    for (let i = 0; i < tiles.length; i++) {
      const t = tiles[i];
      if (!t || t.type === 'empty') continue;

      const pos = this.getTileSheetPos(t.type);
      if (!pos) continue;
      const sx = cellW * pos.sx;
      const sy = cellH * pos.sy;

      // Draw at position with scaling
      this.ctx.drawImage(
        this.sheet,
        sx, sy, cellW, cellH,
        t.x * cellW, t.y * cellH, cellW, cellH
      );
    }
  }

  drawLayer(layer: TMXLayer, camX: number, camY: number, scale: number): void {
    if (!this.sheet || !layer.visible) return;

    const cellW = this.tileWidth * scale;
    const cellH = this.tileHeight * scale;

    for (let row = 0; row < layer.tiles.length; row++) {
      for (let col = 0; col < layer.tiles[row].length; col++) {
        const tileIdx = layer.tiles[row][col];
        if (tileIdx === 0) continue; // skip empty

        const pos = this.getTileSheetPos('solid'); // simplified
        const x = col * cellW - camX;
        const y = row * cellH - camY;

        if (x + cellW < 0 || x > 512 * scale || y + cellH < 0 || y > 448 * scale) continue;

        this.ctx.drawImage(
          this.sheet,
          pos.sx * this.tileWidth, pos.sy * this.tileHeight,
          this.tileWidth, this.tileHeight,
          x, y, cellW, cellH
        );
      }
    }
  }
}