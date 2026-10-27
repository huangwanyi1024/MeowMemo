const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'../../outputs/meowmemo-prototype'),closeHandlers=[];
const sandbox={console,structuredClone,Date,Math,Map,WeakMap,Blob,URL,AbortSignal,crypto:require('node:crypto').webcrypto,
 document:{addEventListener(){},querySelector(){return{addEventListener(type,fn){if(type==='close')closeHandlers.push(fn)},querySelectorAll(){return[]}}}},window:{addEventListener(){}},location:{hostname:'127.0.0.1',protocol:'http:',hash:''},setTimeout,clearTimeout,setInterval(){}};
vm.createContext(sandbox);
for(const file of ['scene.js','captions.js','shop.js','rooms.js','app.js'])vm.runInContext(fs.readFileSync(path.join(root,file),'utf8').replace(/\ninitialize\(\);\s*$/,''),sandbox);
(async()=>{
 sandbox.audio=new Blob(['original meow bytes'],{type:'audio/wav'});sandbox.photo=Object.assign(new Blob(['original image bytes'],{type:'image/jpeg'}),{name:'cats.jpg'});sandbox.video=Object.assign(new Blob(['original video bytes'],{type:'video/mp4'}),{name:'cats.mp4'});
 vm.runInContext("state.memories=[{id:'audio',title:'Dinner',note:'Waiting for dinner',tags:['Together'],catIds:['orange','tabby'],capture:{kind:'audio',blob:audio},media:[],confirmed:'food',funCaption:{text:'Our dinner truce',source:'owner-edited'},analysis:{status:'uncertain'}}];memoryEdit={id:'audio',originalCount:0,media:[]};state.shop.balance=27",sandbox);
 const source=vm.runInContext('state.memories[0]',sandbox),capture=source.capture,caption=source.funCaption,analysis=source.analysis;
 assert.equal(vm.runInContext("stageMemoryAttachments([photo],'image').added",sandbox),1);
 assert.equal(vm.runInContext("stageMemoryAttachments([video],'video').added",sandbox),1);
 assert.equal(source.media.length,0); // staging never writes the memory
 sandbox.persisted=null;
 vm.runInContext("storage=async(store,mode,op)=>op({put(record){persisted=record;return{}}})",sandbox);
 await vm.runInContext("persistMemoryEdits('audio',{title:'Dinner'})",sandbox);
 assert.equal(source.media.length,2);assert.equal(source.capture,capture);assert.equal(source.funCaption,caption);assert.equal(source.analysis,analysis);
 assert.deepEqual([...source.tags],['Together']);assert.equal(await source.media[0].blob.text(),'original image bytes');assert.equal(await source.capture.blob.text(),'original meow bytes');
 assert.equal(vm.runInContext('state.shop.balance',sandbox),27);assert.equal(vm.runInContext('memoryEdit',sandbox),null);
 assert.ok(vm.runInContext('thumb(state.memories[0])',sandbox).startsWith('<img'));
 vm.runInContext("memoryEdit={id:'audio',originalCount:2,media:[...state.memories[0].media]};stageMemoryAttachments([photo],'image');storage=async()=>{throw Error('Storage full')}",sandbox);
 await assert.rejects(()=>vm.runInContext("persistMemoryEdits('audio',{title:'changed'})",sandbox),/Storage full/);
 assert.equal(source.title,'Dinner');assert.equal(source.media.length,2);assert.equal(vm.runInContext('memoryEdit.media.length',sandbox),3);
 closeHandlers.at(-1)();assert.equal(vm.runInContext('memoryEdit',sandbox),null);assert.equal(source.media.length,2);
 vm.runInContext("memoryEdit={id:'audio',originalCount:9,media:Array.from({length:9},()=>({kind:'image',src:'original.jpg'}))}",sandbox);
 const limited=vm.runInContext("stageMemoryAttachments([photo,photo,photo],'image')",sandbox);assert.equal(limited.added,1);assert.ok(limited.message.includes('10'));assert.equal(vm.runInContext('memoryEdit.media.length',sandbox),10);
 vm.runInContext("memoryEdit={id:'audio',originalCount:0,media:[]}",sandbox);
 const invalid=vm.runInContext("stageMemoryAttachments([{type:'text/plain',size:10},{type:'image/jpeg',size:51*1024*1024}],'image')",sandbox);assert.equal(invalid.added,0);assert.ok(invalid.message.includes('50 MB'));
 console.log('PASS: append original photos/videos to saved audio memory; no edits before save; preserve audio/caption/tags/analysis/rewards; failed-save retry and cancel; limits; cover updates.');
})().catch(e=>{console.error(e);process.exit(1)});
