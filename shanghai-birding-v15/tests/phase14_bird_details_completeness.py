import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPLOADED = Path('/mnt/data/921e6ab4-b714-4e6b-8f44-ebb33f43b570.js')

def hash_file(path): return hashlib.sha256(path.read_bytes()).hexdigest()

assert hash_file(ROOT / 'data/birds.js') == hash_file(UPLOADED)
node_script = r'''
const fs = require('fs');
const vm = require('vm');
const root = process.argv[1];
const ctx = { window: {} };
vm.createContext(ctx);
for (const rel of ['data/birds.js','data/bird_details.js','js/modules/bird_profiles.js']) {
  vm.runInContext(fs.readFileSync(root + '/' + rel, 'utf8'), ctx, {filename:rel});
}
const birds = ctx.window.BIRD_LEXICON;
const details = ctx.window.BIRD_DETAILS;
const profiles = birds.map(b => ctx.window.BirdProfiles.getLocal(b));
const required = ['id','name','family','genus','appearance','behavior','habitat','diet','migration'];
const forbidden = ['group','size','fieldMarks','voice','breeding','observationTips','identificationCaution','similarSpecies','dataBasis','scientificName','description','range','conservationStatus','imageUrl','wikipediaUrl','externalIds'];
if (birds.length !== 544) throw new Error('bird count mismatch');
if (Object.keys(details).length !== 544) throw new Error('detail count mismatch');
if (!birds.every(b => Object.prototype.hasOwnProperty.call(details,b.id))) throw new Error('missing detail id');
for (let i=0;i<birds.length;i++) {
  const b=birds[i], p=profiles[i], d=details[b.id];
  if (p.name!==b.name || p.family!==b.family || p.genus!==b.genus) throw new Error('taxonomy mismatch '+b.id);
  for (const key of required) if (typeof p[key] !== 'string' || !p[key].trim()) throw new Error('missing '+key+' '+b.id);
  for (const key of forbidden) if (Object.prototype.hasOwnProperty.call(d,key)) throw new Error('forbidden '+key+' '+b.id);
}
if (new Set(profiles.map(p=>p.appearance)).size <= 200) throw new Error('appearance too templated');
if (new Set(profiles.map(p=>p.behavior)).size <= 100) throw new Error('behavior too templated');
for (const rel of ['js/modules/bird_profiles.js','js/modules/lexicon.js']) {
  const source=fs.readFileSync(root+'/'+rel,'utf8');
  if (source.includes('BirdNET') || source.includes('taxonomy/api') || source.includes('fetchOnline')) throw new Error('network detail code remains '+rel);
}
'''
subprocess.run(['node','-e',node_script,str(ROOT)], check=True)
print('PHASE 14 PASS')
