#!/usr/bin/env node
/** Bake the original SVG artwork into ordinary animated GIFs for GitHub. */
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {execFileSync} = require('node:child_process');
const {createRequire} = require('node:module');
const root = path.resolve(__dirname, '../..');
const sharp = createRequire(path.join(root, '.github/profile/package.json'))('sharp');
const assets = path.join(root, '.github/assets');
const manifestPath = path.join(assets, 'motion-manifest.json');
const frameCount = 48;
const duration = 6;
const budget = 8_000_000;
const hash = input => crypto.createHash('sha256').update(input).digest('hex');
const recipe = hash(Buffer.concat([
  fs.readFileSync(__filename),
  fs.readFileSync(path.join(__dirname, 'motion_frames.py')),
  fs.readFileSync(path.join(root, '.github/profile/package-lock.json')),
]));
sharp.cache(false);
sharp.concurrency(1);

function atomicWrite(file, data) {
  const temporary = file + '.tmp';
  try { fs.writeFileSync(temporary, data); fs.renameSync(temporary, file); }
  finally { if (fs.existsSync(temporary)) fs.unlinkSync(temporary); }
}

async function main() {
  const check = process.argv.includes('--check');
  const prior = fs.existsSync(manifestPath) ? JSON.parse(fs.readFileSync(manifestPath, 'utf8')) : {};
  const manifest = {version:1, recipe, assets:{}};
  let bytes = 0;
  const inputs = JSON.parse(execFileSync('python3', [path.join(__dirname, 'motion_frames.py'), assets, '--list']));
  for (const input of inputs) {
    const svg = fs.readFileSync(input, 'utf8');
    const file = input.replace(/\.svg$/, '.gif');
    const relative = path.relative(root, file).split(path.sep).join('/');
    const source = hash(svg);
    const old = prior.assets?.[relative];
    if (old && prior.recipe === recipe && old.source === source && fs.existsSync(file)
        && old.sha256 === hash(fs.readFileSync(file))) {
      const metadata = await sharp(file, {animated:true}).metadata();
      if (metadata.pages < 2 || metadata.loop !== 0) throw Error(`Not looping: ${relative}`);
      manifest.assets[relative] = old;
      bytes += fs.statSync(file).size;
      continue;
    }
    if (check) throw Error(`Animation export is stale or missing: ${relative}`);
    const sampled = JSON.parse(execFileSync('python3', [path.join(__dirname, 'motion_frames.py'), input,
      '--frames', String(frameCount), '--duration', String(duration)], {maxBuffer:64*1024*1024}));
    const frames = [];
    for (const frame of sampled.frames) {
      frames.push(await sharp(Buffer.from(frame)).ensureAlpha().raw().toBuffer());
    }
    if (new Set(frames.map(hash)).size < 2) throw Error(`Static animation: ${relative}`);
    // GIF delays use centiseconds: alternate 120/130ms for exactly six seconds.
    const delay = frames.map((_,i) => i % 2 ? 130 : 120);
    const buffer = await sharp(Buffer.concat(frames), {raw:{width:sampled.width,
      height:sampled.height*frames.length, channels:4, pageHeight:sampled.height}})
      .gif({loop:0, delay, colours:256, dither:0, effort:7, interFrameMaxError:0, interPaletteMaxError:0})
      .toBuffer();
    const metadata = await sharp(buffer, {animated:true}).metadata();
    if (metadata.pages < 2 || metadata.loop !== 0) throw Error(`Invalid GIF: ${relative}`);
    atomicWrite(file, buffer);
    manifest.assets[relative] = {source, sha256:hash(buffer), width:sampled.width,
      height:sampled.height, frames:metadata.pages, duration_ms:metadata.delay.reduce((a,b)=>a+b,0)};
    bytes += buffer.length;
    console.log(`Animated ${relative}: ${metadata.pages} frames, ${buffer.length} bytes`);
  }
  if (bytes > budget) throw Error(`Animations exceed ${budget} byte budget (${bytes})`);
  if (check) {
    if (JSON.stringify(prior) !== JSON.stringify(manifest)) throw Error('Motion manifest differs from source inventory');
  } else {
    for (const old of Object.keys(prior.assets || {})) {
      if (!(old in manifest.assets) && /^\.github\/assets\/(?:projects\/)?[\w-]+\.gif$/.test(old)) {
        const obsolete = path.join(root, old);
        if (fs.existsSync(obsolete)) fs.unlinkSync(obsolete);
      }
    }
    atomicWrite(manifestPath, JSON.stringify(manifest, null, 2)+'\n');
  }
  console.log(`${check?'Checked':'Exported'} ${Object.keys(manifest.assets).length} looping GIFs (${bytes}/${budget} bytes).`);
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
