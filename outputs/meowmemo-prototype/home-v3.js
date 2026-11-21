'use strict';
// Home-only, session-local behavior. No database writes or profile mutations.
const V3_ART = {
 orange:{sitting:'assets/home-v3/cats/orange_sitting.png',sleeping:'assets/home-v3/cats/orange_sleeping.png',playing:'assets/home-v3/cats/orange_playing.png'},
 gray:{sitting:'assets/home-v3/cats/gray_sitting.png',sleeping:'assets/home-v3/cats/gray_sleeping.png',playing:'assets/home-v3/cats/gray_playing.png'},
 cream:{sitting:'assets/home-v3/cats/cream_sitting.png',sleeping:'assets/home-v3/cats/cream_sleeping.png',playing:'assets/home-v3/cats/cream_playing.png'}
};
const V3_BACKGROUND='assets/home-v3/backgrounds/living_room_empty.png';
const V3_BED='assets/home-v3/props/bed.png';
// Feet anchors measured against the uncropped 1672 × 941 background.
const V3_SPOTS = {
 sofa:{x:.305,y:.775,width:.155,poses:['sitting','sleeping'],layer:4,label:'Sofa cushion'},
 tree:{x:.78,y:.235,width:.105,poses:['sitting','sleeping'],layer:3,label:'Cat tree'},
 desk:{x:.22,y:.43,width:.095,poses:['sitting','sleeping'],layer:3,label:'On the desk'},
 window:{x:.505,y:.61,width:.105,poses:['sitting','sleeping'],layer:2,label:'By the window'},
 rug:{x:.70,y:.94,width:.135,poses:['sitting','sleeping','playing'],layer:6,label:'On the rug'},
 bed:{x:.88,y:.965,width:.135,poses:['sleeping','sitting'],layer:7,label:'Cat bed'},
 toys:{x:.415,y:.99,width:.11,poses:['playing','sitting'],layer:6,label:'Toy corner'}
};
const V3_DECOR_SPOTS={sofa:[18,77],tree:[73,25],desk:[23,40],floor:[66,95],window:[50,54]};
const v3Runtime={cats:[],timers:new Map(),fades:new Set(),active:false,selected:null,trigger:null,pending:new Set(),counts:new Map(),ticks:new Map(),reasons:new Map(),autoTest:false};
function v3Hash(value){return Array.from(String(value||'')).reduce((h,c)=>(Math.imul(h,31)+c.codePointAt(0))>>>0,7)}
function v3Appearance(cat){
 const match=/^#([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(cat.color||'');
 if(match){const [r,g,b]=match.slice(1).map(v=>parseInt(v,16));if((r+g+b)/3>205)return 'cream';if(r>g*1.17&&r>b*1.3)return 'orange';return 'gray'}
 return ['orange','gray','cream'][v3Hash(cat.id)%3];
}
// Shared appearance resolution: saved profile values remain the single source of truth.
const V3_ACCESSORIES={bow:'assets/home-v3/accessories/bow.png',bandana:'assets/home-v3/accessories/bandana.png',collar:'assets/home-v3/accessories/collar.png'};
// Prepared sitting sprites have tight visible bounds plus a 2px transparent safety margin.
const V3_SITTING={
 orange:{stripes:{short:'assets/home-v3/appearance/orange_stripes_short.png',long:'assets/home-v3/appearance/orange_stripes_long.png'},patches:{short:'assets/home-v3/appearance/orange_patches_short.png',long:'assets/home-v3/appearance/orange_patches_long.png'},solid:{short:'assets/home-v3/appearance/orange_solid_short.png',long:'assets/home-v3/appearance/orange_solid_long.png'}},
 gray:{stripes:{short:'assets/home-v3/appearance/gray_stripes_short.png',long:'assets/home-v3/appearance/gray_stripes_long.png'},patches:{short:'assets/home-v3/appearance/gray_patches_short.png',long:'assets/home-v3/appearance/gray_patches_long.png'},solid:{short:'assets/home-v3/appearance/gray_solid_short.png',long:'assets/home-v3/appearance/gray_solid_long.png'}},
 cream:{stripes:{short:'assets/home-v3/appearance/cream_stripes_short.png',long:'assets/home-v3/appearance/cream_stripes_long.png'},patches:{short:'assets/home-v3/appearance/cream_patches_short.png',long:'assets/home-v3/appearance/cream_patches_long.png'},solid:{short:'assets/home-v3/appearance/cream_solid_short.png',long:'assets/home-v3/appearance/cream_solid_long.png'}},
};
// Neck offsets are calibrated separately for compact and fluffy sitting silhouettes.
// Sleeping/playing necks remain occluded, so their accessories stay hidden.
const V3_NECKS={
 short:{bow:{x:42,y:57,w:23},bandana:{x:42,y:57,w:31},collar:{x:42,y:56,w:27}},
 long:{bow:{x:41,y:58,w:24},bandana:{x:41,y:58,w:32},collar:{x:41,y:57,w:28}}
};
const V3_COAT_MASKS={sleeping:'assets/home-v3/coats/sleeping.png',playing:'assets/home-v3/coats/playing.png'};
const V3_COAT_COLORS={orange:'#edb06e',gray:'#aaa09b',cream:'#f7e7cb',dark:'#827772'};
const V3_MARK_COLORS={orange:'#b96f35',gray:'#675853',cream:'#bc9469',dark:'#4d403d'};
// Existing lightweight markings are retained only for the unsupported sleeping/playing variants.
const V3_MARKS={
 sleeping:{
  stripes:'<path d="M24 27l4 10M34 24l3 12M45 23l1 12M66 19l-3 13M78 24l-6 12M86 36l-8 9M76 68l8 6M65 80l4 8" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>',
  patches:'<path d="M21 27Q31 20 35 30L34 40Q26 46 22 39ZM67 19Q81 18 84 34L77 44Q65 41 63 31ZM67 69Q77 59 85 67L84 81Q72 90 64 80Z" fill="currentColor"/>'
 },
 playing:{
  stripes:'<path d="M33 40l3 9M43 39l2 10M54 39l-1 9M72 43l-3 12M83 48l-6 12M87 62l-7 8M76 10l9 3M77 22l12 3" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>',
  patches:'<path d="M30 41Q37 35 42 42L41 52Q32 57 29 49ZM70 42Q85 40 87 55L80 65Q67 65 67 54ZM78 9Q87 5 90 15L91 26Q79 30 77 21Z" fill="currentColor"/>'
 }
};
function v3ResolveAppearance(profile,pose='sitting'){
 const variant=v3Appearance(profile),resolvedPose=Object.hasOwn(V3_ART[variant],pose)?pose:'sitting';
 const accessory=Object.hasOwn(V3_ACCESSORIES,profile.accessory)?profile.accessory:'none';
 const pattern=['stripes','patches','solid'].includes(profile.pattern)?profile.pattern:'stripes';
 const coat=profile.color==='#635c57'?'dark':variant,fur=profile.fur==='long'?'long':'short';
 const sitting=resolvedPose==='sitting',neck=sitting&&accessory!=='none'?V3_NECKS[fur][accessory]:null;
 return {catId:profile.id,variant,pose:resolvedPose,pattern,fur,coatColor:V3_COAT_COLORS[coat],markColor:V3_MARK_COLORS[coat],mask:sitting?null:V3_COAT_MASKS[resolvedPose],sprite:sitting?V3_SITTING[variant][pattern][fur]:V3_ART.cream[resolvedPose],accessory,overlay:neck?{src:V3_ACCESSORIES[accessory],...neck}:null};
}
function v3Illustration(profile,pose='sitting',className='cat-preview'){
 const a=v3ResolveAppearance(profile,pose),overlay=a.overlay;
 const mask=`mask-image:url('${a.mask}');-webkit-mask-image:url('${a.mask}')`;
 return `<span class="cat-illustration ${className}" data-appearance-cat="${esc(a.catId)}" data-variant="${a.variant}" data-pose="${a.pose}" data-pattern="${a.pattern}" data-fur="${a.fur}" data-accessory="${a.accessory}" data-accessory-visible="${!!overlay}"><img class="cat-base ${a.pose==='sleeping'?'v3-trim-fragment':''}" src="${a.sprite}" alt="" draggable="false">${a.mask?`<span class="cat-coat" style="${mask};background:${a.coatColor}"></span>`:''}${!a.mask||a.pattern==='solid'?'':`<svg class="cat-markings" style="${mask};color:${a.markColor}" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">${V3_MARKS[a.pose][a.pattern]}</svg>`}${overlay?`<img class="cat-accessory" src="${overlay.src}" alt="" draggable="false" style="left:${overlay.x}%;top:${overlay.y}%;width:${overlay.w}%">`:''}</span>`;
}
// All static illustrations use the same saved appearance resolver as Home V3.
function catIllustration(cat){return v3Illustration(cat||{id:'decorative',color:'#e9dfcc',pattern:'solid',fur:'short'},'sitting','cat-preview')}
function v3InitialCats(profiles,previous=[],now=Date.now()){
 const occupied=new Set();return profiles.slice(0,2).map(cat=>{
  const old=previous.find(p=>p.catId===cat.id),preferred=(old?.profileSpot===cat.spot?old?.spotId:null)||({tv:'bed'}[cat.spot]||cat.spot);
  const spotId=V3_SPOTS[preferred]&&!occupied.has(preferred)?preferred:Object.keys(V3_SPOTS).find(id=>!occupied.has(id));occupied.add(spotId);
  const spot=V3_SPOTS[spotId],pose=old&&spot.poses.includes(old.pose)?old.pose:spot.poses.includes('sleeping')&&spotId==='sofa'?'sleeping':spot.poses[0];
  return {catId:cat.id,appearance:v3Appearance(cat),profileSpot:cat.spot,spotId,pose,lastTransitionAt:old?.lastTransitionAt??now};
 });
}
function v3NextCat(cat,all,random=Math.random,now=Date.now(),intent='auto'){
 const mode=intent==='auto'?(random()<.3?'move':'pose'):intent;
 const free=Object.keys(V3_SPOTS).filter(id=>id!==cat.spotId&&!all.some(c=>c.catId!==cat.catId&&c.spotId===id));
 let spotId=cat.spotId,pose=cat.pose;
 if(mode==='move'){
  if(free.length)spotId=free[Math.min(free.length-1,Math.floor(random()*free.length))];
  if(!V3_SPOTS[spotId].poses.includes(pose))pose=V3_SPOTS[spotId].poses[0];
 }else{
  // Cycle all three real assets. Relocate when the next pose needs a different surface.
  const poses=['sitting','sleeping','playing'];pose=poses[(poses.indexOf(cat.pose)+1)%poses.length];
  if(!V3_SPOTS[spotId].poses.includes(pose)){
   const suitable=free.filter(id=>V3_SPOTS[id].poses.includes(pose));
   if(suitable.length)spotId=suitable[Math.min(suitable.length-1,Math.floor(random()*suitable.length))];
   else pose=V3_SPOTS[spotId].poses.find(p=>p!==cat.pose)||cat.pose;
  }
 }
 return {...cat,spotId,pose,lastTransitionAt:now};
}
function v3Delay(random=Math.random){return 20000+Math.floor(random()*25001)}
function v3ReducedMotion(){return typeof window.matchMedia==='function'&&window.matchMedia('(prefers-reduced-motion: reduce)').matches}
function v3RenderCat(cat){
 const profile=state.cats.find(c=>c.id===cat.catId);if(!profile)return '';
 const spot=V3_SPOTS[cat.spotId];
 return `<button class="v3-cat v3-${cat.pose}${state.playingId?' playing':''}" data-action="v3-cat" data-cat="${esc(cat.catId)}" data-v3-cat="${esc(cat.catId)}" data-v3-spot="${cat.spotId}" data-v3-pose="${cat.pose}" style="--v3-x:${spot.x*100}%;--v3-y:${spot.y*100}%;--v3-width:${spot.width*100}%;--v3-art-width:${spot.width*100};z-index:${spot.layer}" aria-label="Visit ${esc(profile.name)} · ${cat.pose} · ${spot.label}" aria-haspopup="dialog" aria-expanded="${v3Runtime.selected===cat.catId}">${v3Illustration(profile,cat.pose,'v3-sprite')}<span class="v3-cat-name">${esc(profile.name)}</span></button>`;
}
function v3Bed(){return v3Runtime.cats.some(c=>c.spotId==='bed')?`<img class="v3-bed" src="${V3_BED}" alt="" draggable="false">`:''}
function homeV3Room(){
 v3Runtime.cats=v3InitialCats(state.cats,v3Runtime.cats);
 return `<section class="card room-card v3-room-card" aria-label="Interactive cat room"><div class="room-top"><span>${roomPicker()}</span><span class="muted">A little world of their own.</span></div><div class="v3-room" id="main-room"><img class="v3-room-art" src="${V3_BACKGROUND}" alt="Cat-free Peach Milk living room with a sofa, window, desk and cat tree" draggable="false"><div class="v3-props">${v3Bed()}</div>${roomDecor(V3_DECOR_SPOTS)}${v3Runtime.cats.map(v3RenderCat).join('')}${!v3Runtime.cats.length?'<div class="v3-empty"><p>Your little room is ready.</p><button class="button" data-action="route" data-page="cats">Cat Profile</button></div>':''}</div><div id="v3-cat-card" class="v3-cat-card" role="dialog" aria-label="Cat visit" hidden></div><div class="room-bottom"><span class="location-note">${icon('paw')}Tap a cat. Keep a little moment.</span><div class="room-edit-actions"><button class="button" data-action="room-customize">${icon('home')}Customize Room</button><button class="button" data-action="toggle-cat-editor">${icon('edit')}Edit Cats</button></div></div>${v3DebugPanel()}<p class="v3-scene-note">A playful illustration. Your cats settle into new spots from time to time.<button class="text-button scene-toggle" data-action="peach-scene-toggle">Use classic scene</button></p></section>`;
}
function v3CardHTML(profile){
 const cat=v3Runtime.cats.find(c=>c.catId===profile.id),sound=tapSound(profile),count=state.memories.filter(m=>m.catIds.includes(profile.id)).length;
 return `${profile.photo?`<img class="v3-portrait" src="${esc(urlFor(profile.photo))}" alt="${esc(profile.name)}">`:`<span class="v3-portrait illustrated-portrait">${catIllustration(profile)}</span>`}<div class="v3-card-heading"><h3>${esc(profile.name)}</h3><p>${cat?`${cat.pose[0].toUpperCase()+cat.pose.slice(1)} · ${V3_SPOTS[cat.spotId].label}`:'A little hello'} · ${count} ${count===1?'memory':'memories'}</p></div><button class="icon-btn" data-action="v3-close" aria-label="Close cat visit">${icon('close')}</button><div class="v3-card-actions"><button class="button" data-action="v3-memories" data-cat="${esc(profile.id)}">${icon('book')}View Memories</button><button class="button primary" data-action="v3-record" data-cat="${esc(profile.id)}">${icon('mic')}Add Memory</button>${sound?`<button class="button" data-action="v3-audio" data-cat="${esc(profile.id)}">${icon('play')}Play Saved Sound</button>`:`<span class="mini-note">${voiceMemories(profile).length?'No tap sound selected.':'No saved audio yet.'}</span>`}</div>`;
}
function v3OpenCard(id,trigger){
 const profile=state.cats.find(c=>c.id===id),card=document.querySelector('#v3-cat-card');if(!profile||!card)return;
 v3Runtime.selected=id;v3Runtime.trigger=trigger;card.innerHTML=v3CardHTML(profile);card.hidden=false;
 document.querySelectorAll('[data-v3-cat]').forEach(el=>el.setAttribute('aria-expanded',String(el.dataset.v3Cat===id)));
 card.querySelector('[data-action="v3-close"]')?.focus();
}
function v3CloseCard(restoreFocus=true){
 const card=document.querySelector('#v3-cat-card');if(card){card.hidden=true;card.innerHTML=''}
 document.querySelectorAll('[data-v3-cat]').forEach(el=>el.setAttribute('aria-expanded','false'));
 if(restoreFocus&&v3Runtime.trigger?.isConnected)v3Runtime.trigger.focus();v3Runtime.selected=null;v3Runtime.trigger=null;
}
function v3Stop(){
 for(const timer of v3Runtime.timers.values())clearTimeout(timer);for(const timer of v3Runtime.fades)clearTimeout(timer);
 v3Runtime.timers.clear();v3Runtime.fades.clear();v3Runtime.pending.clear();v3Runtime.active=false;v3Runtime.autoTest=false;v3CloseCard(false);
}
function v3PaintCat(button,next){
 const profile=state.cats.find(c=>c.id===next.catId),spot=V3_SPOTS[next.spotId];if(!profile)return;
 // Retain the focused button; update its actual image and scene-coordinate style in place.
 button.setAttribute('class',`v3-cat v3-${next.pose}${state.playingId?' playing':''}`);
 button.setAttribute('style',`--v3-x:${spot.x*100}%;--v3-y:${spot.y*100}%;--v3-width:${spot.width*100}%;--v3-art-width:${spot.width*100};z-index:${spot.layer}`);
 button.setAttribute('data-v3-spot',next.spotId);button.setAttribute('data-v3-pose',next.pose);
 button.setAttribute('aria-label',`Visit ${profile.name} · ${next.pose} · ${spot.label}`);
 const markup=v3RenderCat(next);button.innerHTML=markup.slice(markup.indexOf('>')+1,markup.lastIndexOf('</button>'));
 const props=document.querySelector('.v3-props');if(props)props.innerHTML=v3Bed();
 if(v3Runtime.selected===next.catId){const heading=document.querySelector('#v3-cat-card .v3-card-heading p');if(heading){const count=state.memories.filter(m=>m.catIds.includes(next.catId)).length;heading.textContent=`${next.pose[0].toUpperCase()+next.pose.slice(1)} · ${spot.label} · ${count} ${count===1?'memory':'memories'}`}}
}
function v3Transition(id,intent='auto',source='timer'){
 if(!v3Runtime.active||v3Runtime.pending.has(id))return false;
 const current=v3Runtime.cats.find(c=>c.catId===id),button=Array.from(document.querySelectorAll('[data-v3-cat]')).find(el=>el.dataset.v3Cat===id);
 if(!current||!button)return false;
 const count=v3Runtime.counts.get(id)||0;
 // A bounded move cadence prevents cats from staying on one surface indefinitely.
 const mode=intent==='auto'?((count+1)%3===0?'move':'pose'):intent;
 const next=v3NextCat(current,v3Runtime.cats,Math.random,Date.now(),mode);
 if(next.spotId===current.spotId&&next.pose===current.pose){v3Runtime.reasons.set(id,'No valid alternative');v3Schedule(id);v3RefreshDebug();return false}
 const timer=v3Runtime.timers.get(id);if(timer!==undefined)clearTimeout(timer);v3Runtime.timers.delete(id);
 v3Runtime.pending.add(id);button.classList.add('is-changing');
 v3Runtime.cats=v3Runtime.cats.map(c=>c.catId===id?next:c); // Reserve the destination before either cat can move.
 v3Runtime.reasons.set(id,`Rendering ${source} transition`);v3RefreshDebug();
 const fade=setTimeout(()=>{
  v3Runtime.fades.delete(fade);v3Runtime.pending.delete(id);
  if(!v3Runtime.active)return;
  if(button.isConnected){v3PaintCat(button,next);v3Runtime.counts.set(id,count+1);v3Runtime.reasons.set(id,`${source}: ${mode}`)}
  else v3Runtime.reasons.set(id,'Home rerendered');
  v3Schedule(id);v3RefreshDebug();
 },v3ReducedMotion()?0:180);v3Runtime.fades.add(fade);return true;
}
function v3Schedule(id){
 if(!v3Runtime.active||v3Runtime.timers.has(id)||v3Runtime.pending.has(id))return;
 const delay=v3Runtime.autoTest?3000:v3Delay();
 v3Runtime.timers.set(id,setTimeout(()=>{
  v3Runtime.timers.delete(id);if(!v3Runtime.active)return;
  v3Runtime.ticks.set(id,(v3Runtime.ticks.get(id)||0)+1);
  // Cat cards and keyboard focus no longer suppress transitions indefinitely.
  if(document.hidden||document.querySelector('#modal')?.open){v3Runtime.reasons.set(id,'Paused: hidden page or modal');v3Schedule(id);v3RefreshDebug();return}
  if(!v3Transition(id,'auto',v3Runtime.autoTest?'auto-test':'timer'))v3Schedule(id);
 },delay));
}
function v3DebugEnabled(){return typeof location!=='undefined'&&new URLSearchParams(location.search||'').get('debugCats')==='1'}
function v3DebugHTML(){
 const total=Array.from(v3Runtime.counts.values()).reduce((a,b)=>a+b,0);
 return `<div class="v3-debug-heading"><strong>Cat Behavior Debug</strong><span>Transitions: <b data-v3-transition-count>${total}</b></span></div><button class="button" data-action="v3-debug-auto" aria-pressed="${v3Runtime.autoTest}">Auto Test: ${v3Runtime.autoTest?'On':'Off'}</button><p>Auto Test forces a visible production transition for each cat every 3 seconds. Normal mode uses 20–45 seconds.</p>${v3Runtime.cats.map(cat=>{const profile=state.cats.find(c=>c.id===cat.catId),busy=v3Runtime.pending.has(cat.catId);return `<div class="v3-debug-cat"><strong>${esc(profile?.name||cat.catId)}</strong><span data-debug-cat="${esc(cat.catId)}">${cat.pose} · ${cat.spotId} · ${v3Runtime.counts.get(cat.catId)||0} transitions · ${v3Runtime.ticks.get(cat.catId)||0} timer ticks</span><small>${esc(v3Runtime.reasons.get(cat.catId)||'Ready')} · ${busy?'fading':v3Runtime.timers.has(cat.catId)?'timer scheduled':'timer idle'}</small><div><button class="button" data-action="v3-debug-pose" data-cat="${esc(cat.catId)}" aria-label="Next Pose: ${esc(profile?.name||cat.catId)}" ${busy?'disabled':''}>Next Pose</button><button class="button" data-action="v3-debug-move" data-cat="${esc(cat.catId)}" aria-label="Move Spot: ${esc(profile?.name||cat.catId)}" ${busy?'disabled':''}>Move Spot</button></div></div>`}).join('')}`;
}
function v3DebugPanel(){return v3DebugEnabled()?`<aside id="v3-debug" class="v3-debug" aria-label="Cat behavior debug">${v3DebugHTML()}</aside>`:''}
function v3RefreshDebug(){
 if(!v3DebugEnabled())return;const panel=document.querySelector('#v3-debug');if(!panel)return;
 const focused=document.activeElement,action=focused?.dataset?.action,cat=focused?.dataset?.cat,restore=panel.contains?.(focused);
 panel.innerHTML=v3DebugHTML();
 if(restore)Array.from(panel.querySelectorAll('[data-action]')).find(el=>el.dataset.action===action&&el.dataset.cat===cat)?.focus();
}
function v3ToggleAuto(){
 if(!v3DebugEnabled())return;
 v3Runtime.autoTest=!v3Runtime.autoTest;for(const timer of v3Runtime.timers.values())clearTimeout(timer);v3Runtime.timers.clear();
 for(const cat of v3Runtime.cats)v3Schedule(cat.catId);v3RefreshDebug();
}
function v3Sync(){
 if(state.page!=='home'||!document.querySelector('.v3-room')||document.hidden){v3Stop();return}
 const ids=new Set(v3Runtime.cats.map(c=>c.catId));for(const [id,timer]of v3Runtime.timers){if(!ids.has(id)){clearTimeout(timer);v3Runtime.timers.delete(id)}}
 v3Runtime.active=true;for(const cat of v3Runtime.cats)v3Schedule(cat.catId);
 // A full application render replaces the card; keep it closed rather than leaving stale focus.
 v3CloseCard(false);v3RefreshDebug();
}
async function v3Action(action,el){
 if(action==='v3-debug-auto'){v3ToggleAuto();return}
 const id=el.dataset.cat,profile=state.cats.find(c=>c.id===id);
 if(v3DebugEnabled()&&action==='v3-debug-pose'){v3Transition(id,'pose','debug');return}
 if(v3DebugEnabled()&&action==='v3-debug-move'){v3Transition(id,'move','debug');return}
 if(action==='v3-close'){v3CloseCard();return}if(!profile)return;
 if(action==='v3-cat'){v3OpenCard(id,el);return}
 if(action==='v3-memories'){v3CloseCard(false);state.catFilter=id;state.search='';state.filter='all';state.contextFilter='all';state.locationFilter='all';route('memories',true);return}
 if(action==='v3-record'){v3CloseCard(false);draft.catIds=[id];route('record');return}
 if(action==='v3-audio'){const sound=tapSound(profile);if(sound){v3CloseCard(false);await playMemory(sound.id,{keepPositions:true})}}
}
function v3Keydown(event){if(event.key==='Escape'&&v3Runtime.selected){event.preventDefault();v3CloseCard()}}
document.addEventListener('keydown',v3Keydown);
document.addEventListener('visibilitychange',()=>{if(document.hidden)v3Stop();else if(typeof state!=='undefined')v3Sync()});
window.addEventListener('pagehide',v3Stop);

window.addEventListener('pageshow',()=>{if(typeof state!=='undefined')v3Sync()});

function v3InactiveDebugPanel(){
 if(!v3DebugEnabled()||state.page!=='home'||(!customRoom()&&peachRoomEnabled))return '';
 return `<aside class="v3-debug" aria-label="Cat behavior debug"><strong>Cat Behavior Debug: V3 inactive</strong><p>${customRoom()?'A saved custom room is selected. Its existing pet behavior is preserved. Select Our living room to test Home V3.':'Classic scene is selected. Choose Use Peach Milk scene to run the V3 state machine.'}</p></aside>`;
}
