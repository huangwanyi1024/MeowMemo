// Contract checks without browser storage or paid API traffic.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const web=path.resolve(__dirname,'../../outputs/meowmemo-prototype');
const sandbox={console,structuredClone,Date,Math,Map,WeakMap,Blob,URL,AbortSignal,
 location:{hostname:'127.0.0.1',protocol:'http:',hash:''},
 document:{querySelector:()=>({addEventListener(){}}),addEventListener(){}},
 window:{addEventListener(){}},setInterval(){},setTimeout,clearTimeout};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(web,'captions.js'),'utf8'),sandbox);
vm.runInContext(fs.readFileSync(path.join(web,'shop.js'),'utf8'),sandbox);
vm.runInContext(fs.readFileSync(path.join(web,'app.js'),'utf8').replace(/\ninitialize\(\);\s*$/,''),sandbox);
(async()=>{
 const old=vm.runInContext("normalizeOwner({style:'fitness',language:'zh'})",sandbox);
 assert.equal(old.about,'');assert.equal(old.style,'fitness');
 const saved=vm.runInContext("normalizeOwner({style:'academic',language:'en',about:'A grad student who lifts.'})",sandbox);
 assert.equal(saved.about,'A grad student who lifts.');
 const base={catId:'orange',context:'food',personality:'clingy',ownerStyle:'academic',language:'en',catDescription:'A talkative cat',ownerDescription:'Grad student',memoryTitle:'Study time',memoryNote:'Finishing an assignment',memoryTags:['Together','StudyBuddy'],catName:'Miso',participantNames:['Miso','Nori'],variant:0};
 for(const language of ['en','zh'])for(const context of ['food','brushing','isolation','other','unknown'])for(const personality of ['polite','clingy','direct','bossy','goofy'])for(const ownerStyle of ['everyday','academic','fitness','work','gaming'])for(let variant=0;variant<3;variant++){
  sandbox.input={...base,language,context,personality,ownerStyle,variant};
  const cap=await vm.runInContext('generateFunCaption(input)',sandbox);
  assert.equal(cap.source,'builtin-template');assert.ok(cap.text.length>0);assert.equal(cap.context,context);
 }
 let sent;
 sandbox.input={...base,context:'unknown',provider:'ai',inferenceStatus:'uncertain',audio:'must not send'};
 sandbox.fetch=async(url,options)=>{sent=JSON.parse(options.body);return{ok:true,json:async()=>({...base,text:'A tiny mystery worth keeping.',source:'ai-copy',forFun:true,context:'unknown',personalization:{memoryNote:base.memoryNote,memoryTags:base.memoryTags,participantNames:base.participantNames,catName:base.catName}})}};
 const cap=await vm.runInContext('generateFunCaption(input)',sandbox);
 assert.equal(cap.source,'ai-copy');assert.equal(sent.context,'unknown');
 assert.equal(sent.ownerDescription,base.ownerDescription);assert.equal(sent.memoryNote,base.memoryNote);assert.deepEqual(sent.memoryTags,base.memoryTags);assert.equal(sent.catName,base.catName);assert.deepEqual(sent.participantNames,base.participantNames);
 assert.ok(!('audio' in sent));assert.ok(!('inferenceStatus' in sent));assert.ok(!('provider' in sent));
 sandbox.cap=cap;
 assert.equal(vm.runInContext("cleanCaption(cap,['orange']).personalization.memoryNote",sandbox),base.memoryNote);
 assert.equal(vm.runInContext("cleanCaption(cap,['orange']).personalization.memoryTags.join(',')",sandbox),base.memoryTags.join(','));

 const choices=Array.from({length:5},(_,i)=>({angle:`Angle ${i}`,text:`Fish treaty ${i}`}));
 sandbox.input={...base,provider:'ai',count:5,avoidTexts:['Previous wording'],participantDetails:['Miso: clingy older sister']};
 sandbox.fetch=async(url,options)=>{sent=JSON.parse(options.body);return{ok:true,json:async()=>({...base,text:choices[0].text,options:choices,source:'ai-copy',forFun:true})}};
 const batch=await vm.runInContext('generateFunCaption(input)',sandbox);
 assert.equal(sent.count,5);assert.deepEqual(sent.avoidTexts,['Previous wording']);assert.equal(sent.participantDetails.length,1);
 sandbox.batch=batch;
 assert.equal(vm.runInContext("cleanCaption(batch,['orange']).options.length",sandbox),5);
 assert.equal(vm.runInContext("cleanCaptionBatches({'orange:en':batch},['orange'])['orange:en'].options[4].text",sandbox),choices[4].text);
 // Hidden pool rotates one caption per click, fetches only when exhausted or stale,
 // and persists its cursor without consuming the caller's pool before storage succeeds.
 let poolCalls=0;
 sandbox.fetch=async(url,options)=>{poolCalls++;return{ok:true,json:async()=>({...base,text:`Round ${poolCalls} version 0`,options:choices.map((o,i)=>({...o,text:`Round ${poolCalls} version ${i}`})),source:'ai-copy',forFun:true})}};
 let pool=null,currentText='old caption',shown=[];
 for(let i=0;i<5;i++){
  sandbox.pool=pool;sandbox.currentText=currentText;
  const before=JSON.stringify(pool);
  const next=await vm.runInContext('nextAICaption(input,pool,currentText)',sandbox);
  assert.equal(JSON.stringify(pool),before);
  pool=next.batch;currentText=next.caption.text;shown.push(currentText);
 }
 assert.equal(poolCalls,1);assert.equal(new Set(shown).size,5);
 sandbox.pool=pool;sandbox.currentText=currentText;
 const sixth=await vm.runInContext('nextAICaption(input,pool,currentText)',sandbox);
 assert.equal(poolCalls,2);assert.ok(!shown.includes(sixth.caption.text));
 sandbox.pool=sixth.batch;
 assert.equal(vm.runInContext("cleanCaptionBatches({'orange:en':pool},['orange'])['orange:en'].usedTexts.length",sandbox),1);
 assert.equal(vm.runInContext("cleanCaption(pool,['orange']).poolSignature",sandbox),sixth.batch.poolSignature);
 sandbox.input={...sandbox.input,memoryNote:'A changed story'};
 await vm.runInContext('nextAICaption(input,pool,currentText)',sandbox);assert.equal(poolCalls,3);
 sandbox.input={...sandbox.input,personality:'bossy'};
 await vm.runInContext('nextAICaption(input,pool,currentText)',sandbox);assert.equal(poolCalls,4);
 sandbox.catSVG=()=>'';sandbox.icon=()=>'';
 sandbox.memory={id:'rotation-test',catIds:['orange'],title:'Together',note:'',tags:[],funCaption:{...batch,text:'Visible caption'},captionBatches:{'orange:en':batch}};
 const panel=vm.runInContext('captionPanel(memory)',sandbox);
 assert.ok(panel.includes('Generate AI caption'));assert.ok(panel.includes('Visible caption'));
 assert.ok(!panel.includes('caption-choice'));assert.ok(!panel.includes('Pick your favorite'));
 assert.ok(!panel.includes('Generate 5'));
 sandbox.fetch=async()=>({ok:true,json:async()=>({...base,text:'Bad batch',options:[choices[0]],source:'ai-copy',forFun:true})});
 await assert.rejects(()=>vm.runInContext('generateFunCaption(input)',sandbox),/five different/);
 sandbox.input={...base,provider:'ai'};
 sandbox.fetch=async()=>({ok:false,json:async()=>({detail:'AI is not configured.'})});
 await assert.rejects(()=>vm.runInContext('generateFunCaption(input)',sandbox),/not configured/);
 vm.runInContext("state.memories=[{id:'food',title:'Dinner',note:'',tags:[],catIds:['orange'],place:'tree',confirmed:'food',favorite:true,date:'2026-10-26'},{id:'old',title:'Old',note:'',tags:[],catIds:['orange'],place:'sofa',date:'2026-10-25'},{id:'other',title:'Desk',note:'',tags:[],catIds:['tabby'],place:'desk',confirmed:'other',date:'2026-10-24'}];state.contextFilter='food'",sandbox);
 assert.equal(vm.runInContext('filteredMemories().map(m=>m.id).join()',sandbox),'food');
 vm.runInContext("state.contextFilter='unknown'",sandbox);assert.equal(vm.runInContext('filteredMemories().map(m=>m.id).join()',sandbox),'old');
 vm.runInContext("state.contextFilter='other';state.catFilter='orange'",sandbox);assert.equal(vm.runInContext('filteredMemories().length',sandbox),0);
 vm.runInContext("state.contextFilter='food';state.catFilter='orange';state.filter='favorites';state.locationFilter='tree'",sandbox);assert.equal(vm.runInContext('filteredMemories().length',sandbox),1);
 console.log('PASS: 750 built-in combinations; old/new owner settings; text-only AI payload; unknown context; caption backup metadata; no silent AI fallback.');
})().catch(e=>{console.error(e);process.exit(1)});
