#!/usr/bin/env tsx
/**
 * Asset Conversion Script
 *
 * Converts Exolon assets for Facebook Gaming HTML5 port:
 * - TMX files → JSON level data
 * - PNG sprite sheets → JSON atlases + optimized PNGs
 *
 * Usage: npm run convert-assets
 */

import { parseStringPromise } from 'xml2js';
import { readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync } from 'fs';
import { join, extname, basename } from 'path';
import { createCanvas, loadImage } from 'canvas';
import { gunzipSync, inflateSync } from 'zlib';
import { Buffer } from 'buffer';

// Configuration
const SOURCE_DIR = '/home/pall/projects/exolon/Exolon/Resources';
const OUTPUT_DIR = '/home/pall/projects/exolon/facebook-port/public/assets';
const LEVELS_OUTPUT = join(OUTPUT_DIR, 'levels');
const SPRITES_OUTPUT = join(OUTPUT_DIR, 'sprites');

interface TMXMap {
  width: number;
  height: number;
  tilewidth: number;
  tileheight: number;
  tilesets: TMXTileset[];
  layers: TMXLayer[];
  objectgroups: TMXObjectGroup[];
  properties?: Record<string, string>;
}

interface TMXTileset {
  firstgid: number;
  name: string;
  tilewidth: number;
  tileheight: number;
  image: { source: string; width: number; height: number };
  margin: number;
  spacing: number;
  tilecount: number;
  columns: number;
}

interface TMXLayer {
  name: string;
  width: number;
  height: number;
  data: string | number[];
  encoding?: string;
  compression?: string;
  opacity: number;
  visible: boolean;
  properties?: Record<string, string>;
}

interface TMXObjectGroup {
  name: string;
  objects: TMXObject[];
}

interface TMXObject {
  id: number;
  name: string;
  type?: string;
  x: number;
  y: number;
  width: number;
  height: number;
  properties?: TMXProperty[];
  gid?: number;
}

interface TMXProperty {
  name: string;
  value: string;
  type?: string;
}

interface LevelData {
  zoneNumber: number;
  stage: number;
  width: number;
  height: number;
  tileWidth: number;
  tileHeight: number;
  tiles: TileData[][];
  playerStart: { x: number; y: number };
  actionMarkers: ActionMarker[];
}

interface TileData {
  type: string;
  x: number;
  y: number;
  w: number;
  h: number;
  meta?: Record<string, unknown>;
}

interface ActionMarker {
  type: string;
  x: number;
  y: number;
  width: number;
  height: number;
  properties: Record<string, unknown>;
}

interface SpriteAtlas {
  frames: Record<string, SpriteFrame>;
  meta: {
    image: string;
    size: { w: number; h: number };
    scale: string;
  };
}

interface SpriteFrame {
  frame: { x: number; y: number; w: number; h: number };
  rotated: boolean;
  trimmed: boolean;
  spriteSourceSize: { x: number; y: number; w: number; h: number };
  sourceSize: { w: number; h: number };
}

// Tile type mapping from TMX properties
const TILE_TYPE_MAP: Record<string, string> = {
  'solid': 'solid',
  'destroyable': 'destroyable',
  'turret': 'turret',
  'mine': 'mine',
  'teleport': 'teleport',
  'ammo': 'ammo_box',
  'grenade': 'grenade_box',
  'sphere_home': 'sphere_home',
  'pump': 'pump',
  'rocket_launcher': 'rocket_launcher',
  'changing_room': 'changing_room',
  'beacon': 'beacon',
  'force_field': 'force_field',
  'stage_end': 'stage_end',
  'torch': 'torch',
  'flashing': 'flashing',
  'gate': 'gate',
};

const OBJECT_TYPE_MAP: Record<string, string> = {
  'turret': 'turret',
  'mine': 'mine',
  'teleport': 'teleport',
  'ammo_box': 'ammo_box',
  'grenade_box': 'grenade_box',
  'sphere_home': 'sphere_home',
  'pump': 'pump',
  'rocket_launcher': 'rocket_launcher',
  'changing_room': 'changing_room',
  'beacon': 'beacon',
  'force_field': 'force_field',
  'stage_end': 'stage_end',
  'torch': 'torch',
  'flashing': 'flashing',
  'player_start': 'player_start',
  'ship': 'player_start',
  'gate': 'gate',
};

function ensureDir(dir: string): void {
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
}

async function parseTMX(filePath: string): Promise<TMXMap> {
  const xml = readFileSync(filePath, 'utf-8');
  const result = await parseStringPromise(xml, { explicitArray: false, mergeAttrs: true });
  const map = result.map;

  // Normalize layers: xml2js returns "layer" array, not "layers"
  const layers: TMXLayer[] = [];
  if (map.layer) {
    const layerArray = Array.isArray(map.layer) ? map.layer : [map.layer];
    for (const l of layerArray) {
      // Data content is in _ property when mergeAttrs=true, encoding/compression are direct properties
      let data: string | number[] = [];
      let encoding = 'base64';
      let compression: string | undefined;
      if (l.data) {
        if (typeof l.data === 'string') {
          data = l.data;
        } else if (l.data._) {
          data = l.data._;
        }
        encoding = l.data.encoding || 'base64';
        compression = l.data.compression;
      }
      // Handle properties - can be single object or array
      const props = l.properties?.property;
      let properties: Record<string, string> = {};
      if (props) {
        const propArray = Array.isArray(props) ? props : [props];
        properties = propArray.reduce((acc: Record<string, string>, p: any) => ({ ...acc, [p.name]: p.value }), {});
      }
      layers.push({
        name: l.name,
        width: parseInt(l.width, 10),
        height: parseInt(l.height, 10),
        data,
        encoding,
        compression,
        opacity: parseFloat(l.opacity) || 1,
        visible: l.visible !== '0',
        properties,
      });
    }
  }

  // Normalize objectgroups: xml2js returns "objectgroup" array
  const objectgroups: TMXObjectGroup[] = [];
  if (map.objectgroup) {
    const ogArray = Array.isArray(map.objectgroup) ? map.objectgroup : [map.objectgroup];
    for (const og of ogArray) {
      const objects: TMXObject[] = [];
      if (og.object) {
        const objArray = Array.isArray(og.object) ? og.object : [og.object];
        for (const obj of objArray) {
          // Handle properties - can be single object or array
          const objProps = obj.properties?.property;
          let properties: Record<string, string> = {};
          if (objProps) {
            const propArray = Array.isArray(objProps) ? objProps : [objProps];
            properties = propArray.reduce((acc: Record<string, string>, p: any) => ({ ...acc, [p.name]: p.value }), {});
          }
          objects.push({
            id: parseInt(obj.id, 10),
            name: obj.name || '',
            type: obj.type,
            x: parseFloat(obj.x),
            y: parseFloat(obj.y),
            width: parseFloat(obj.width) || 0,
            height: parseFloat(obj.height) || 0,
            properties,
            gid: obj.gid ? parseInt(obj.gid, 10) : undefined,
          });
        }
      }
      objectgroups.push({
        name: og.name,
        objects,
      });
    }
  }

  // Normalize tilesets: xml2js returns "tileset" (single or array)
  const tilesets: TMXTileset[] = [];
  if (map.tileset) {
    const tsArray = Array.isArray(map.tileset) ? map.tileset : [map.tileset];
    for (const ts of tsArray) {
      tilesets.push({
        firstgid: parseInt(ts.firstgid, 10),
        name: ts.name,
        tilewidth: parseInt(ts.tilewidth, 10),
        tileheight: parseInt(ts.tileheight, 10),
        image: {
          source: ts.image?.source || '',
          width: parseInt(ts.image?.width, 10) || 0,
          height: parseInt(ts.image?.height, 10) || 0,
        },
        margin: parseInt(ts.margin, 10) || 0,
        spacing: parseInt(ts.spacing, 10) || 0,
        tilecount: parseInt(ts.tilecount, 10) || 0,
        columns: parseInt(ts.columns, 10) || 0,
      });
    }
  }

  return {
    width: parseInt(map.width, 10),
    height: parseInt(map.height, 10),
    tilewidth: parseInt(map.tilewidth, 10),
    tileheight: parseInt(map.tileheight, 10),
    tilesets,
    layers,
    objectgroups,
    properties: map.properties?.property?.reduce((acc: Record<string, string>, p: any) => ({ ...acc, [p.name]: p.value }), {}) || {},
  };
}

function decodeLayerData(data: string, encoding: string, compression: string | undefined, width: number, height: number): number[] {
  let buffer: Buffer;

  if (encoding === 'csv') {
    // CSV encoding: comma-separated unsigned integers
    const values = data.trim().split(',').map(v => parseInt(v.trim(), 10));
    buffer = Buffer.alloc(values.length * 4);
    for (let i = 0; i < values.length; i++) {
      buffer.writeUInt32LE(values[i] || 0, i * 4);
    }
  } else {
    // Base64 encoding (with optional compression)
    buffer = Buffer.from(data, 'base64');

    // Decompress if needed - only if compression attribute is present
    if (compression === 'gzip') {
      buffer = gunzipSync(buffer);
    } else if (compression === 'zlib') {
      buffer = inflateSync(buffer);
    }
  }

  // Parse as 32-bit unsigned integers (little-endian)
  const expectedSize = width * height * 4;
  if (buffer.length < expectedSize) {
    const newBuffer = Buffer.alloc(expectedSize);
    buffer.copy(newBuffer);
    buffer = newBuffer;
  }

  const result = new Array(width * height);
  for (let i = 0; i < width * height; i++) {
    result[i] = buffer.readUInt32LE(i * 4);
  }
  return result;
}

function getTileTypeFromGID(gid: number, tilesets: TMXTileset[]): string | null {
  // Find which tileset this GID belongs to
  let tileset: TMXTileset | null = null;
  for (const ts of tilesets) {
    if (gid >= ts.firstgid && gid < ts.firstgid + ts.tilecount) {
      tileset = ts;
      break;
    }
  }
  if (!tileset) return null;

  // For now, return a generic type - in real use we'd check tile properties
  // This is simplified; the actual TMX has tile properties in the tileset
  return 'solid';
}

function convertTMXToLevel(map: TMXMap, zoneNumber: number): LevelData {
  const stage = Math.floor(zoneNumber / 25);
  const tileWidth = map.tilewidth;
  const tileHeight = map.tileheight;
  const mapWidth = map.width * tileWidth;
  const mapHeight = map.height * tileHeight;

  // Find collision layer
  const collisionLayer = map.layers.find(l =>
    l.name?.toLowerCase().includes('collision') ||
    l.name?.toLowerCase().includes('meta') ||
    l.name?.toLowerCase().includes('block')
  ) || map.layers[0];

  // Decode collision layer data (base64 + gzip/zlib)
  const collisionData = collisionLayer.data as string;
  const encoding = collisionLayer.encoding || 'base64';
  const compression = collisionLayer.compression; // No default - only decompress if attribute present
  const decodedGids = decodeLayerData(collisionData, encoding, compression, map.width, map.height);

  // Build tile grid
  const tiles: TileData[][] = Array.from({ length: map.height }, (_, y) =>
    Array.from({ length: map.width }, (_, x) => {
      const idx = y * map.width + x;
      const gid = decodedGids[idx] || 0;
      // GID 0 = empty, otherwise check tile properties for type
      // For now, use a simple mapping based on GID ranges
      let type = 'empty';
      if (gid > 0) {
        // These TMX files use a single tileset; tile types are in tile properties
        // which we don't fully parse. Use GID ranges as approximation.
        if (gid >= 1 && gid <= 20) type = 'solid';
        else if (gid >= 21 && gid <= 40) type = 'destroyable';
        else type = 'solid';
      }
      return {
        type,
        x: x * tileWidth,
        y: y * tileHeight,
        w: tileWidth,
        h: tileHeight,
      };
    })
  );

  // Extract action markers from object groups
  const actionMarkers: ActionMarker[] = [];
  let playerStart = { x: 16, y: 112 }; // default

  const objectGroups = Array.isArray(map.objectgroups) ? map.objectgroups : [];

  for (const og of objectGroups) {
    const objects = og.objects || [];
    for (const obj of objects) {
      const type = obj.type?.toLowerCase() || obj.name?.toLowerCase() || 'unknown';
      const mappedType = OBJECT_TYPE_MAP[type] || type;

      if (mappedType === 'player_start') {
        playerStart = { x: obj.x, y: obj.y };
      } else {
        // Handle properties as either array (old format) or plain object (new format)
        let properties: Record<string, unknown> = {};
        if (obj.properties) {
          if (Array.isArray(obj.properties)) {
            properties = obj.properties.reduce((acc, p) => ({ ...acc, [p.name]: p.value }), {});
          } else {
            properties = obj.properties as Record<string, unknown>;
          }
        }
        actionMarkers.push({
          type: mappedType,
          x: obj.x,
          y: obj.y,
          width: obj.width,
          height: obj.height,
          properties,
        });
      }
    }
  }

  return {
    zoneNumber,
    stage,
    width: mapWidth,
    height: mapHeight,
    tileWidth,
    tileHeight,
    tiles,
    playerStart,
    actionMarkers,
  };
}

async function convertLevels(): Promise<void> {
  console.log('Converting TMX levels...');
  ensureDir(LEVELS_OUTPUT);

  const tmxFiles = readdirSync(SOURCE_DIR)
    .filter(f => f.endsWith('.tmx'))
    .sort();

  for (const file of tmxFiles) {
    const match = file.match(/L(\d+)S(\d+)/i);
    if (!match) continue;

    const zoneStage = parseInt(match[1], 10);
    const zoneInStage = parseInt(match[2], 10);
    const zoneNumber = (zoneStage - 1) * 25 + (zoneInStage - 1);

    try {
      const map = await parseTMX(join(SOURCE_DIR, file));
      const level = convertTMXToLevel(map, zoneNumber);

      const outputPath = join(LEVELS_OUTPUT, `zone_${String(zoneNumber).padStart(3, '0')}.json`);
      writeFileSync(outputPath, JSON.stringify(level, null, 2));
      console.log(`  ✓ ${file} → zone_${String(zoneNumber).padStart(3, '0')}.json`);
    } catch (err) {
      console.error(`  ✗ Failed to convert ${file}:`, err);
    }
  }
}

async function generateSpriteAtlas(imagePath: string, outputName: string): Promise<void> {
  // Simple atlas generator - assumes uniform grid
  // In production, you'd use a proper texture packer
  const img = await loadImage(imagePath);
  const canvas = createCanvas(img.width, img.height);
  const ctx = canvas.getContext('2d');
  ctx.drawImage(img, 0, 0);

  // Assume 16x16 frames for now (adjust based on actual sprites)
  const frameWidth = 16;
  const frameHeight = 16;
  const cols = Math.floor(img.width / frameWidth);
  const rows = Math.floor(img.height / frameHeight);

  const frames: Record<string, SpriteFrame> = {};

  for (let row = 0; row < rows; row++) {
    for (let col = 0; col < cols; col++) {
      const index = row * cols + col;
      const name = `${outputName}_${String(index).padStart(3, '0')}`;

      frames[name] = {
        frame: {
          x: col * frameWidth,
          y: row * frameHeight,
          w: frameWidth,
          h: frameHeight,
        },
        rotated: false,
        trimmed: false,
        spriteSourceSize: {
          x: 0,
          y: 0,
          w: frameWidth,
          h: frameHeight,
        },
        sourceSize: {
          w: frameWidth,
          h: frameHeight,
        },
      };
    }
  }

  const atlas: SpriteAtlas = {
    frames,
    meta: {
      image: `${outputName}.png`,
      size: { w: img.width, h: img.height },
      scale: '1',
    },
  };

  const atlasPath = join(SPRITES_OUTPUT, `${outputName}.json`);
  writeFileSync(atlasPath, JSON.stringify(atlas, null, 2));

  // Copy PNG to output
  const pngBuffer = canvas.toBuffer('image/png');
  writeFileSync(join(SPRITES_OUTPUT, `${outputName}.png`), pngBuffer);

  console.log(`  ✓ ${basename(imagePath)} → ${outputName}.json + .png (${frames.length} frames)`);
}

async function convertSprites(): Promise<void> {
  console.log('Converting sprite sheets...');
  ensureDir(SPRITES_OUTPUT);

  const pngFiles = readdirSync(SOURCE_DIR)
    .filter(f => f.endsWith('.png') || f.endsWith('.gif'))
    .sort();

  for (const file of pngFiles) {
    const name = basename(file, extname(file)).toLowerCase().replace(/[^a-z0-9]/g, '_');
    try {
      await generateSpriteAtlas(join(SOURCE_DIR, file), name);
    } catch (err) {
      console.error(`  ✗ Failed to convert ${file}:`, err);
    }
  }
}

async function main(): Promise<void> {
  console.log('=== Exolon Asset Conversion ===');
  console.log(`Source: ${SOURCE_DIR}`);
  console.log(`Output: ${OUTPUT_DIR}`);
  console.log('');

  await convertLevels();
  console.log('');
  await convertSprites();
  console.log('');
  console.log('=== Conversion Complete ===');
}

main().catch(err => {
  console.error('Conversion failed:', err);
  process.exit(1);
});