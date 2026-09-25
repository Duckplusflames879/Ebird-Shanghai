import fs from 'node:fs';
import assert from 'node:assert/strict';

const root = new URL('../', import.meta.url).pathname;
const html = fs.readFileSync(`${root}/index.html`, 'utf8');
const scriptPaths = [...html.matchAll(/<script src="([^"]+)"><\/script>/g)].map(m => m[1]);
const cssPaths = [...html.matchAll(/<link rel="stylesheet" href="([^"]+)">/g)].map(m => m[1]);
assert.equal(scriptPaths.length, 22);
assert.ok(scriptPaths.includes('js/modules/ebird.js'));
assert.ok(scriptPaths.indexOf('js/modules/ebird.js') < scriptPaths.indexOf('js/modules/hotspots.js'));
assert.ok(scriptPaths.includes('data/bird_details.js'));
assert.ok(scriptPaths.includes('js/modules/bird_profiles.js'));
assert.ok(scriptPaths.includes('js/auto_update.js'));
assert.deepEqual(scriptPaths.slice(0, 2), ['data/birds.js', 'data/latest_data.js']);
assert.equal(cssPaths.length, 5);
for (const rel of [...scriptPaths, ...cssPaths]) assert.ok(fs.existsSync(`${root}/${rel}`), `missing asset: ${rel}`);
const constants = fs.readFileSync(`${root}/js/constants.js`, 'utf8');
const router = fs.readFileSync(`${root}/js/router.js`, 'utf8');
for (const route of ['/home','/weather','/hotspots','/records','/lexicon','/settings']) {
  assert.ok(constants.includes(`'${route}'`), `missing route in constants: ${route}`);
  assert.ok(router.includes(`'${route}'`), `missing route in router: ${route}`);
}
assert.match(html, /<aside id="sidebar"/);
assert.match(html, /<section id="app"/);
console.log('PHASE 0 STATIC PASS');
