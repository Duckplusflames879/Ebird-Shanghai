import assert from 'node:assert/strict';
import fs from 'node:fs';

const ROOT = new URL('..', import.meta.url).pathname;
const source = fs.readFileSync(new URL('../js/auto_update.js', import.meta.url), 'utf8');
globalThis.window = globalThis;
globalThis.location = { protocol: 'http:' };
globalThis.EXTERNAL_DATA = { version: 1, app: 'shanghai-birding', hotspots: [] };
const calls = [];

class MockResponse {
  constructor(body, init={}) { this.body = body; this.status = init.status ?? 200; this.ok = this.status >= 200 && this.status < 300; }
  async json() { return JSON.parse(this.body); }
  async text() { return this.body; }
}

globalThis.fetch = async (url, options={}) => {
  calls.push({url: String(url), method: options.method || 'GET'});
  if (String(url).startsWith('/__auto_update')) {
    return new MockResponse(JSON.stringify({success:true, updated:true, skipped:false, message:'测试自动更新成功'}));
  }
  if (String(url).includes('data/latest_data.js?')) {
    return new MockResponse("window.EXTERNAL_DATA = {version:1, app:'shanghai-birding', sourceStatus:'ok', hotspots:[{id:'demo', name:'测试点'}]};");
  }
  throw new Error(`unexpected fetch: ${url}`);
};

new Function(source)();
assert.equal(typeof globalThis.AutoUpdater.run, 'function');
const result = await globalThis.AutoUpdater.run();
assert.equal(result.success, true);
assert.equal(result.updated, true);
assert.equal(calls[0].url, '/__auto_update');
assert.equal(calls[0].method, 'POST');
assert.equal(calls[1].url.startsWith('data/latest_data.js?'), true);
assert.equal(globalThis.EXTERNAL_DATA.hotspots[0].name, '测试点');
console.log('PHASE 23 AUTO UPDATE CLIENT PASS');
