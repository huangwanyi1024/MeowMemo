const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../../outputs/meowmemo-prototype');
const sandbox={console:{log:console.log,error(){}},structuredClone,Date,Math,Map,WeakMap,Blob,URL,URLSearchParams,atob,btoa,AbortSignal,crypto:crypto.webcrypto,setTimeout,clearTimeout,setInterval(){},document:{addEventListener(){},querySelector(){return{addEventListener(){},querySelectorAll(){return[]}}}},window:{addEventListener(){}},location:{hostname:'127.0.0.1',protocol:'http:',hash:'',search:''},confirm(){throw Error('First-run must not prompt')}};
vm.createContext(sandbox);
for(const name of ['demo-data.js','scene.js','captions.js','shop.js','rooms.js','app.js'])vm.runInContext(fs.readFileSync(path.join(root,name),'utf8').replace(/\ninitialize\(\);\s*$/,''),sandbox);
const stores={memories:new Map(),settings:new Map()};let commits=0,fail=false;
sandbox.journal=stores;sandbox.makeTx=()=>{const pending={memories:new Map(stores.memories),settings:new Map(stores.settings)};const tx={objectStore(name){return{put(item){pending[name].set(item.id,item);return{}}}}};setTimeout(()=>{if(fail){tx.error=Error('Storage full');tx.onabort();return}for(const key of Object.keys(stores))stores[key]=pending[key];commits++;tx.oncomplete()},0);return tx;};
vm.runInContext("db={transaction:()=>makeTx()};openDB=async()=>db;storage=async(store,mode,operation)=>operation({getAll:()=>[...journal[store].values()],get:id=>journal[store].get(id),put:v=>journal[store].set(v.id,v)});render=()=>{};toast=()=>{};refreshCaptionConnection=()=>{}",sandbox);
(async()=>{
 assert.equal(vm.runInContext('shouldLoadDemo([],[])',sandbox),true);
 for(const expr of ['shouldLoadDemo([{id:"mine"}],[])','shouldLoadDemo([],[{id:"seeded",value:true}])','shouldLoadDemo([],[{id:"cats"}])'])assert.equal(vm.runInContext(expr,sandbox),false);
 await vm.runInContext('initialize()',sandbox);assert.equal(commits,1);assert.equal(stores.memories.size,6);assert.equal(stores.settings.get('seeded').value,true);
 const seed=vm.runInContext('MEOWMEMO_DEMO_BACKUP',sandbox);assert.equal(JSON.stringify(stores.settings.get('cats').value.map(c=>c.name)),JSON.stringify(seed.cats.map(c=>c.name)));
 let audio=0;
 for(const m of seed.memories){const saved=stores.memories.get(m.id);assert.equal(saved.title,m.title);assert.equal(saved.note,m.note);assert.equal(saved.duration,m.duration);assert.equal(saved.media.length,m.media.length);if(m.capture){audio++;assert.deepEqual(Buffer.from(await saved.capture.blob.arrayBuffer()),Buffer.from(m.capture.data.split(',')[1],'base64'));}for(let i=0;i<m.media.length;i++)assert.deepEqual(Buffer.from(await saved.media[i].blob.arrayBuffer()),Buffer.from(m.media[i].data.split(',')[1],'base64'));}
 assert.equal(audio,3);assert.equal(stores.settings.get('shop').value.balance,seed.shop.balance);
 const first=stores.memories.values().next().value;first.note='Reviewer edit retained';await vm.runInContext('initialize()',sandbox);assert.equal(commits,1);assert.equal(stores.memories.get(first.id).note,'Reviewer edit retained');
 stores.memories.clear();await vm.runInContext('initialize()',sandbox);assert.equal(stores.memories.size,0);assert.equal(commits,1);
 stores.settings.clear();fail=true;await vm.runInContext('initialize()',sandbox);assert.equal(stores.settings.size,0);assert.equal(stores.memories.size,0);assert.equal(commits,1);
 console.log('PASS: pristine first-run loads 6 memories / 3 original audio blobs; photos, profiles and shop retained; no repeat seed, no overwrite of reviewer edits or intentionally emptied journal; failure is atomic.');
})().catch(e=>{console.error(e);process.exit(1)});
