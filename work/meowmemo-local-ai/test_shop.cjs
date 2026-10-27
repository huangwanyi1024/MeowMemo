const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const root=require('node:path').resolve(__dirname,'../../outputs/meowmemo-prototype');
const settings=new Map(),memories=new Map();let fail=false;
// Transactional test double: commit both stores only on success.
const db={transaction(){const a=new Map(settings),b=new Map(memories);let aborted=false;const tx={abort(){aborted=true;queueMicrotask(()=>tx.onabort?.())},objectStore(name){const store=name==='settings'?a:b;return{get(key){const req={};queueMicrotask(()=>{req.result=structuredClone(store.get(key));req.onsuccess?.();if(!aborted)queueMicrotask(()=>{if(fail){tx.error=new Error('Simulated storage failure');tx.onabort?.();return}settings.clear();for(const [k,v]of a)settings.set(k,v);memories.clear();for(const [k,v]of b)memories.set(k,v);tx.oncomplete?.()})});return req},put(value){store.set(value.id,structuredClone(value))},add(value){if(store.has(value.id))throw new Error('Duplicate memory');store.set(value.id,structuredClone(value))}}}};return tx}};
let feedback='';const sandbox={console,structuredClone,setTimeout,File,Blob,navigator:{},Date,document:{querySelectorAll:()=>[]}};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(root+'/shop.js','utf8'),sandbox);
vm.runInContext(`const state={shop:emptyShop(),storageReady:true};const db=externalDB;const $=()=>({close(){}});function render(){}function route(){}function toast(s){report(s)}function openPlacement(){};`,Object.assign(sandbox,{externalDB:db,report:s=>feedback=s}));
(async()=>{
 await vm.runInContext("saveRewardedMemory({id:'one',title:'Memory'})",sandbox);
 assert.equal(settings.get('shop').value.balance,2);assert(memories.has('one'));
 await vm.runInContext("changeShop(w=>awardTreats(w,'share','one'))",sandbox);
 await vm.runInContext("changeShop(w=>awardTreats(w,'share','one'))",sandbox);
 assert.equal(settings.get('shop').value.balance,7,'share reward only once');
 await assert.rejects(vm.runInContext("redeemItem('mouse')",sandbox));assert.equal(settings.get('shop').value.balance,7);
 for(let i=2;i<=5;i++)await vm.runInContext(`saveRewardedMemory({id:'${i}'})`,sandbox);
 assert.equal(settings.get('shop').value.balance,15);
 await vm.runInContext("redeemItem('mouse')",sandbox);assert.equal(settings.get('shop').value.balance,0);assert.deepEqual(settings.get('shop').value.owned,['mouse']);
 await vm.runInContext("redeemItem('mouse')",sandbox);assert.equal(settings.get('shop').value.balance,0,'no double charge');
 await vm.runInContext("placeShopItem('mouse','sofa')",sandbox);assert.equal(settings.get('shop').value.placements.mouse,'sofa');
 await vm.runInContext("placeShopItem('mouse','desk')",sandbox);assert.equal(settings.get('shop').value.placements.mouse,'sofa','invalid placement ignored');
 await vm.runInContext("placeShopItem('mouse',null)",sandbox);assert.equal(settings.get('shop').value.placements.mouse,undefined);
 fail=true;await assert.rejects(vm.runInContext("saveRewardedMemory({id:'failed'})",sandbox));assert(!memories.has('failed'));assert.equal(settings.get('shop').value.balance,0,'failure cannot mint rewards');fail=false;
 await assert.rejects(vm.runInContext("saveRewardedMemory({id:'one'})",sandbox));assert.equal(settings.get('shop').value.balance,0,'duplicate cannot mint rewards');
 const bad=vm.runInContext("cleanShop({balance:-3,owned:['evil','mouse'],placements:{mouse:'desk'},events:{'share:one':true,'bad':true}})",sandbox);assert.equal(bad.balance,0);assert.equal(bad.owned.length,1);assert.equal(bad.placements.mouse,undefined);assert.equal(Object.keys(bad.events).length,1);
 // Cancellation must not award a share, even after a card has been prepared.
 vm.runInContext("state.memories=[{id:'cancelled',title:'Test',date:'2026-10-26',media:[],capture:null}];async function serializeMedia(){return null}async function makeShareCard(){return new Blob(['test'],{type:'image/png'})}function esc(s){return String(s||'')}function formatDate(){return 'Oct 26'}function downloadBlob(){throw new Error('Unexpected download')}",sandbox);
 sandbox.navigator.canShare=()=>true;sandbox.navigator.share=async()=>{const e=new Error('Canceled');e.name='AbortError';throw e};await vm.runInContext("shareMemory('cancelled')",sandbox);assert(!settings.get('shop').value.events['share:cancelled']);assert.match(feedback,/canceled/);
 await vm.runInContext("grantTestTreats()",sandbox);await vm.runInContext("grantTestTreats()",sandbox);assert.equal(settings.get('shop').value.balance,40,'test credit is exactly once');
 console.log('PASS: +2 post, +5 first share, duplicate protection, balance, redemption, valid placements, put-away, atomic rollback, import validation and canceled share.');
})().catch(e=>{console.error(e);process.exit(1)});
