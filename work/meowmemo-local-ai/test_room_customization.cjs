const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'../../outputs/meowmemo-prototype');
const sandbox={console,structuredClone,Date,Math,Map,WeakMap,Blob,URL,AbortSignal,crypto:require('node:crypto').webcrypto,
 document:{addEventListener(){},querySelector(){return{addEventListener(){}}}},window:{addEventListener(){}},location:{hostname:'127.0.0.1',protocol:'http:',hash:''},setTimeout,clearTimeout,setInterval(){}};
vm.createContext(sandbox);
for(const file of ['scene.js','captions.js','shop.js','rooms.js','app.js'])vm.runInContext(fs.readFileSync(path.join(root,file),'utf8').replace(/\ninitialize\(\);\s*$/,''),sandbox);
(async()=>{
 for(const type of ['living','bedroom','bathroom','other']){
  sandbox.type=type;
  const room=vm.runInContext("cleanRoom({id:'test-room',name:'My room',...roomTemplate(type)})",sandbox);sandbox.room=room;
  assert.equal(room.type,type);assert.ok(room.objects.length>=3);
  vm.runInContext("state.rooms={activeId:'test-room',items:[room]}",sandbox);
  const cats=vm.runInContext('roomCatLayouts(state.cats)',sandbox);
  assert.equal(cats.length,2);assert.notDeepEqual([cats[0].x,cats[0].y],[cats[1].x,cats[1].y]);
  for(const c of cats){assert.ok(c.left>=0&&c.left+c.width<=100);assert.ok(c.top>=0&&c.top<95)}
  assert.ok(vm.runInContext('viewRoom()',sandbox).includes('Customize room'));
  assert.ok(vm.runInContext('customRoomSVG(room,true)',sandbox).includes('room-draft-floor'));
 }
 vm.runInContext("state.rooms={activeId:'original',items:[]}",sandbox);
 assert.ok(vm.runInContext('viewRoom()',sandbox).includes('Your irregular living room'));
 assert.equal(vm.runInContext("cleanRoom({id:'bad',type:'__proto__'})",sandbox),null);
 const sanitized=vm.runInContext("cleanRoom({id:'\"<bad>',type:'living',wall:'red;script',objects:[{kind:'sofa',x:-100,y:1000,size:10},{kind:'__proto__'}]})",sandbox);
 assert.equal(sanitized.objects.length,1);assert.equal(sanitized.objects[0].x,10);assert.equal(sanitized.objects[0].y,93);assert.equal(sanitized.objects[0].size,1.4);assert.equal(sanitized.wall,'#fff1d7');assert.equal(sanitized.id,'bad');
 vm.runInContext("state.rooms={activeId:'original',items:[]};storage=async()=>{throw Error('Storage full')}",sandbox);
 await assert.rejects(()=>vm.runInContext("saveRoomSettings({activeId:'new',items:[]})",sandbox),/Storage full/);
 assert.equal(vm.runInContext('state.rooms.activeId',sandbox),'original');
 sandbox.blobToData=async blob=>`data:${blob.type};base64,${Buffer.from(await blob.arrayBuffer()).toString('base64')}`;
 sandbox.dataToBlob=value=>new Blob([Buffer.from(value.split(',')[1],'base64')],{type:'image/jpeg'});
 sandbox.photo=new Blob(['original image bytes'],{type:'image/jpeg'});
 vm.runInContext("blobToData=globalThis.blobToData;dataToBlob=globalThis.dataToBlob;state.rooms={activeId:'saved',items:[cleanRoom({id:'saved',name:'Bedroom',photo,type:'bedroom',...roomTemplate('bedroom')})]}",sandbox);
 const backup=await vm.runInContext('serializeRoomSettings()',sandbox);sandbox.backup=backup;
 const restored=vm.runInContext('deserializeRoomSettings(backup)',sandbox);
 assert.equal(restored.activeId,'saved');assert.equal(await restored.items[0].photo.text(),'original image bytes');
 assert.equal(restored.items[0].objects.length,vm.runInContext('state.rooms.items[0].objects.length',sandbox));
 console.log('PASS: four room templates, original scene preserved, safe furniture bounds, two-cat anchors, photo backup roundtrip and atomic save failure.');
})().catch(e=>{console.error(e);process.exit(1)});
