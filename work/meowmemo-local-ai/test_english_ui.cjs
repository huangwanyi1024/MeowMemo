const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'../../outputs/meowmemo-prototype');
const sandbox={console,structuredClone,Date,Math,Map,WeakMap,Blob,URL,URLSearchParams,AbortSignal,crypto:require('node:crypto').webcrypto,
 document:{addEventListener(){},querySelector(){return{addEventListener(){}}}},window:{addEventListener(){}},location:{hostname:'127.0.0.1',protocol:'http:',hash:''},setTimeout,clearTimeout,setInterval(){}};
vm.createContext(sandbox);
for(const file of ['scene.js','captions.js','shop.js','rooms.js','home-v3.js','app.js'])vm.runInContext(fs.readFileSync(path.join(root,file),'utf8').replace(/\ninitialize\(\);\s*$/,''),sandbox);
(async()=>{
 const legacy={id:'legacy',title:'我们的日常',note:'请保留这段文字',tags:['互动'],catIds:['orange'],date:'2026-11-18',place:'sofa',media:[],favorite:true,funCaption:{text:'这是我保存的台词',language:'zh',catId:'orange',source:'owner-edited'}};
 sandbox.legacy=legacy;
 vm.runInContext("state.owner=normalizeOwner({language:'zh',style:'everyday',about:'我的介绍'});state.cats[0].name='虎皮';state.memories=[legacy]",sandbox);
 const before=vm.runInContext('JSON.stringify({owner:state.owner,cats:state.cats,memories:state.memories})',sandbox);
 assert.equal(vm.runInContext('captionView(legacy).language',sandbox),'en');
 assert.equal(vm.runInContext("captionInput(legacy,'orange','zh').language",sandbox),'en');
 const markup=vm.runInContext('captionPanel(legacy)+ownerStyleForm()+memoryCard(legacy)',sandbox);
 assert(markup.includes(legacy.funCaption.text));assert(markup.includes(legacy.note));assert(markup.includes('虎皮'));assert(!markup.includes('>中文<'));
 assert.equal(vm.runInContext("cleanCaption(legacy.funCaption,['orange']).language",sandbox),'zh');
 assert.equal(vm.runInContext("cleanCaption(legacy.funCaption,['orange']).text",sandbox),legacy.funCaption.text);
 assert.equal(vm.runInContext('JSON.stringify({owner:state.owner,cats:state.cats,memories:state.memories})',sandbox),before,'rendering must not migrate or translate stored content');
 const builtin=await vm.runInContext("generateFunCaption({language:'zh',context:'food',personality:'polite',ownerStyle:'everyday',catId:'orange'})",sandbox);
 assert.equal(builtin.language,'en');assert(!/\p{Script=Han}/u.test(builtin.text));
 let payload;
 sandbox.fetch=async(url,options)=>{payload=JSON.parse(options.body);return{ok:true,json:async()=>({source:'ai-copy',forFun:true,text:'A little moment with you.',language:'en'})}};
 await vm.runInContext("generateFunCaption({provider:'ai',language:'zh',catId:'orange',catName:'虎皮',memoryNote:'请保留故事',context:'other'})",sandbox);
 assert.equal(payload.language,'en');assert.equal(payload.catName,'虎皮');assert.equal(payload.memoryNote,'请保留故事');
 for(const file of ['app.js','captions.js','rooms.js','shop.js','scene.js','index.html','styles.css'])assert(!/\p{Script=Han}/u.test(fs.readFileSync(path.join(root,file),'utf8')),`${file}: hardcoded non-English UI`);
 assert.match(fs.readFileSync(root+'/index.html','utf8'),/lang="en-US"/);
 console.log('PASS: English UI/templates/new AI requests; legacy names, notes, tags, captions and language metadata preserved without writes.');
})().catch(e=>{console.error(e);process.exit(1)});
