// Presentation integration checks: real state, safe markup and portable assets.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'../../outputs/meowmemo-prototype');
const sandbox={console,structuredClone,Date,Math,Map,WeakMap,Blob,URL,URLSearchParams,AbortSignal,crypto:require('node:crypto').webcrypto,
 document:{addEventListener(){},querySelector(){return{addEventListener(){}}}},window:{addEventListener(){}},location:{hostname:'127.0.0.1',protocol:'http:',hash:''},setTimeout,clearTimeout,setInterval(){}};
vm.createContext(sandbox);
for(const file of ['scene.js','captions.js','shop.js','rooms.js','home-v3.js','app.js'])vm.runInContext(fs.readFileSync(path.join(root,file),'utf8').replace(/\ninitialize\(\);\s*$/,''),sandbox);
assert.match(vm.runInContext('viewRoom()',sandbox),/v3-room-art/);
assert.equal((vm.runInContext('viewRoom()',sandbox).match(/data-v3-cat=/g)||[]).length,2,'both stored cat controls remain');
vm.runInContext('peachRoomEnabled=false',sandbox);
assert.match(vm.runInContext('viewRoom()',sandbox),/storybook-room/,'classic scene still usable');
vm.runInContext("state.rooms={activeId:'mine',items:[cleanRoom({id:'mine',name:'My bedroom',...roomTemplate('bedroom')})]}",sandbox);
assert.match(vm.runInContext('viewRoom()',sandbox),/custom-room-art/,'custom rooms use saved layout');
assert.doesNotMatch(vm.runInContext('viewRoom()',sandbox),/peach-room-art/);
sandbox.memory={id:'test',title:'<a private moment>',date:'2026-11-18',catIds:['orange'],media:[{kind:'video'}],tags:[],note:'Test',place:'sofa'};
let card=vm.runInContext('memoryCard(memory)',sandbox);
assert.match(card,/&lt;a private moment&gt;/,'stored title is safely escaped');
assert.match(card,/Video memory · No audio recording/,'video attachments are not mislabeled photos');
assert.match(card,/More actions for/);
const portable=fs.readFileSync(root+'/meowmemo.html','utf8');
const script=portable.split('<script>\n')[1].split('\n</script>')[0];
new vm.Script(script,{filename:'portable-meowmemo.js'});
const assetLine=script.split('\n')[0];const assetContext=vm.createContext({});vm.runInContext(assetLine,assetContext);
const assets=vm.runInContext('ASSETS',assetContext);
for(const match of script.matchAll(/ASSETS\["([^"]+)"\]/g))assert(assets[match[1]],`embedded image exists: ${match[1]}`);
assert(assets['assets/peach-milk/backgrounds/living_room_scene.png'].startsWith('data:image/png;base64,'));
assert(!portable.includes('src="assets/peach-milk/'),'standalone image paths are embedded');
assert(!portable.includes("url('assets/peach-milk/"),'standalone CSS/font URLs are embedded');
console.log('PASS: real cat controls, classic/custom scenes, safe real-memory markup, video labels and standalone image/font embedding.');
