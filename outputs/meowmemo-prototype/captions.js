/* Entertainment copy only. This provider never classifies sound or translates a cat. */
const PERSONALITIES={polite:'Polite & gentle',clingy:'Clingy & sweet',direct:'Straight to the point',bossy:'Little boss',goofy:'A little goofy'};
const OWNER_STYLES={everyday:'Everyday life',academic:'Academic / research',fitness:'Fitness buddy',work:'Work / office',gaming:'Gaming buddy'};
const CONTEXTS={food:{emoji:'🐟',label:'Waiting for food',short:'Food'},brushing:{emoji:'🪮',label:'Being brushed',short:'Brushing'},isolation:{emoji:'🏠',label:'Alone / unfamiliar room',short:'Isolation'},other:{emoji:'💬',label:'Something else',short:'Other'},unknown:{emoji:'❔',label:'Not sure',short:'Unknown'}};
const defaultOwner={style:'everyday',language:'en',about:''};
const CAPTION_LINES={
  "en": {
    "food": {
      "polite": [
        "Could I have a little more fish, please?",
        "Excuse me, is the kitchen still open?",
        "A small second serving would be lovely."
      ],
      "clingy": [
        "One tiny snack, pretty please? I brought my cutest face.",
        "Just a little fish? I will supervise from right here.",
        "Can dinner happen next to you? With extra fish?"
      ],
      "direct": [
        "Bowl empty. Please refill.",
        "Food first. Details later.",
        "I checked. Still no dinner."
      ],
      "bossy": [
        "The bowl is empty. Explain.",
        "I have moved dinner forward. To now.",
        "Your snack supervisor is waiting."
      ],
      "goofy": [
        "I looked in the bowl. The food has gone invisible.",
        "Is this an all-you-can-imagine buffet?",
        "My bowl and I have a scheduling problem."
      ]
    },
    "brushing": {
      "polite": [
        "A gentle brush, if you have a moment?",
        "Thank you for the little grooming appointment.",
        "May we take this one brushstroke at a time?"
      ],
      "clingy": [
        "A little brush, and can you stay close?",
        "Grooming together counts as quality time, right?",
        "Just you, me, and my impressive collection of fluff."
      ],
      "direct": [
        "Brush time. Gently, please.",
        "One small grooming session.",
        "Please attend to the fluff."
      ],
      "bossy": [
        "The fluff requires your attention.",
        "Your grooming supervisor has arrived.",
        "One appointment. Excellent service expected."
      ],
      "goofy": [
        "Some assembly required. Mostly fluff.",
        "Please return all loose clouds to their owner.",
        "I appear to be producing another cat."
      ]
    },
    "isolation": {
      "polite": [
        "Could you keep me company for a little while?",
        "A familiar face would be very welcome.",
        "May we explore this little corner together?"
      ],
      "clingy": [
        "Can you stay right here with me?",
        "I saved the spot next to me for you.",
        "A little company, pretty please?"
      ],
      "direct": [
        "New room. Please stay nearby.",
        "Could use a familiar face here.",
        "Company would be nice."
      ],
      "bossy": [
        "You are requested in this room.",
        "I have reserved your company.",
        "This room needs one more human."
      ],
      "goofy": [
        "This room did not come with instructions.",
        "I may need a tour guide. A familiar one.",
        "Excuse me, where do we keep the familiar humans?"
      ]
    },
    "other": {
      "polite": [
        "A little moment with you.",
        "Thank you for keeping this little memory.",
        "May we save this one for later?"
      ],
      "clingy": [
        "Can this little moment last a bit longer?",
        "Here with you. That is a good place to be.",
        "A little memory, just for us."
      ],
      "direct": [
        "Keep this one.",
        "One small moment. Saved.",
        "You, me, this moment."
      ],
      "bossy": [
        "This moment is approved for keeping.",
        "Please file this under: us.",
        "My personal archivist is doing well."
      ],
      "goofy": [
        "An extremely important ordinary moment.",
        "No grand plan. Just a little cat moment.",
        "Please keep this for future scientific giggles."
      ]
    },
    "unknown": {
      "polite": [
        "One little moment, a story only you can tell.",
        "May we keep this little moment anyway?",
        "There is room for a note, whenever you remember."
      ],
      "clingy": [
        "You can keep our little moment, even without a label.",
        "A little moment, just for us to remember.",
        "No perfect explanation needed to keep this one."
      ],
      "direct": [
        "Moment saved. Context: not sure.",
        "A little moment. No label needed.",
        "Keep the moment. Add the story later."
      ],
      "bossy": [
        "File this under: a little mystery.",
        "A little mystery, approved for the archive.",
        "You may keep this moment without solving it."
      ],
      "goofy": [
        "A tiny mystery with whiskers.",
        "The plot is unclear. The memory can stay.",
        "One small unsolved meow-ment."
      ]
    }
  }
};
const STYLE_NOTES={
  "en": {
    "academic": {
      "food": [
        "Proposal: move dinner forward. Peer review is welcome.",
        "Observation: an empty bowl. Proposed intervention: dinner.",
        "A small research grant, payable in fish, would help."
      ],
      "brushing": [
        "A short study in applied fluff management.",
        "Field notes: one brush, many tiny clouds.",
        "Please archive this grooming session."
      ],
      "isolation": [
        "Fieldwork is easier with a familiar research assistant.",
        "A familiar co-investigator is requested.",
        "New environment, familiar company. A promising study design."
      ],
      "other": [
        "A field note from our everyday life.",
        "Filed under: ordinary moments worth studying.",
        "A tiny contribution to the archive of us."
      ],
      "unknown": [
        "The hypothesis can wait. Keep the observation.",
        "No conclusion yet. The original moment is worth saving.",
        "An open question for our little archive."
      ]
    },
    "fitness": {
      "food": [
        "Today’s protein allocation appears to be missing.",
        "Could dinner be my post-stretch snack?",
        "A little fish fits my very unofficial meal plan."
      ],
      "brushing": [
        "Recovery day includes a little fluff care.",
        "A little grooming between stretches.",
        "Today’s routine: stretch, brush, repeat."
      ],
      "isolation": [
        "A familiar workout buddy would be nice.",
        "Could we take this little break together?",
        "Company counts as a good rest-day plan."
      ],
      "other": [
        "Adding this to our daily routine.",
        "A little rest between all those big stretches.",
        "Today’s tiny win: a moment together."
      ],
      "unknown": [
        "No need to turn every moment into a performance metric.",
        "Just keeping one little moment from the routine.",
        "A label-free little break."
      ]
    },
    "work": {
      "food": [
        "Agenda item one: an earlier dinner.",
        "Requesting a snack break at your earliest convenience.",
        "Could we put dinner at the top of today’s priorities?"
      ],
      "brushing": [
        "A grooming appointment has entered the calendar.",
        "A short break for fluff maintenance.",
        "Today’s agenda includes a little grooming."
      ],
      "isolation": [
        "Requesting an in-person check-in.",
        "Could we make this a quick team visit?",
        "One familiar colleague, please."
      ],
      "other": [
        "A tiny entry in our shared daily log.",
        "A small moment outside the to-do list.",
        "Saving this for the end-of-day highlights."
      ],
      "unknown": [
        "No meeting needed. We can add a note later.",
        "Pending context. Original moment retained.",
        "An open item in the little moments log."
      ]
    },
    "gaming": {
      "food": [
        "Snack quest available. Reward: my excellent company.",
        "Dinner inventory: suspiciously low.",
        "A small food delivery would restore the snack inventory."
      ],
      "brushing": [
        "Side quest: tidy the fluff.",
        "Grooming mini-quest accepted.",
        "One brush, a surprising amount of loot."
      ],
      "isolation": [
        "Could use a familiar co-op partner here.",
        "New area. Familiar teammate requested.",
        "Please join this little exploration party."
      ],
      "other": [
        "A little moment worth saving in our game log.",
        "Checkpoint saved: us, at home.",
        "An ordinary side quest with my favorite teammate."
      ],
      "unknown": [
        "Mystery side quest. No solution required yet.",
        "An unlabeled collectible for our memory log.",
        "Save the checkpoint. The explanation can wait."
      ]
    }
  }
};
const builtinCaptionProvider={
 id:'builtin-template',version:'builtin-v1',
 async generate(input){
  const language='en',context=CONTEXTS[input.context]?input.context:'unknown';
  const personality=PERSONALITIES[input.personality]?input.personality:'polite',style=OWNER_STYLES[input.ownerStyle]?input.ownerStyle:'everyday';
  const variant=Math.max(0,Number(input.variant)||0)%3;
  const base=CAPTION_LINES[language][context][personality][variant];
  const extra=style==='everyday'?'':STYLE_NOTES[language][style][context][variant];
  return {text:base+(extra?' '+extra:''),catId:input.catId,context,personality,ownerStyle:style,language,variant,source:'builtin-template',generatorVersion:this.version,forFun:true,basedOn:'owner-observation',createdAt:new Date().toISOString()};
 }
};
// Cloud copy is explicit and text-only. Saving a memory still defaults to built-in copy.
let captionAIStatus={available:false,checked:false,model:'gpt-6-luna',localOnly:false,provider:'OpenAI',message:'AI connection has not been checked.'};
async function checkCaptionAI(){
 if(!['127.0.0.1','localhost'].includes(location.hostname)||location.protocol!=='http:'){
  captionAIStatus={...captionAIStatus,available:false,checked:true,message:'Open bash start-local-ai.sh to configure AI captions.'};return captionAIStatus;
 }
 try{const r=await fetch('/api/captions/status',{signal:AbortSignal.timeout(4000)});if(!r.ok)throw Error('Unavailable');const value=await r.json();captionAIStatus={available:value.available===true,checked:true,model:String(value.model||'gpt-6-luna'),localOnly:value.localOnly===true,provider:String(value.provider||'OpenAI'),message:String(value.message||'AI is unavailable.')};}
 catch(e){captionAIStatus={...captionAIStatus,available:false,checked:true,message:'AI captions are unavailable. bash start-local-ai.sh; built-in captions still work.'};}
 return captionAIStatus;
}
async function generateFunCaption(input){
 if(input.provider!=='ai')return builtinCaptionProvider.generate(input);
 if(!['127.0.0.1','localhost'].includes(location.hostname)||location.protocol!=='http:')throw Error('bash start-local-ai.sh to use AI captions.');
 const payload={count:input.count===5?5:1,participantDetails:(input.participantDetails||[]).slice(0,5).map(t=>String(t).slice(0,1100)),avoidTexts:(input.avoidTexts||[]).slice(0,10).map(t=>String(t).slice(0,600)),catId:String(input.catId||'orange').slice(0,50),context:CONTEXTS[input.context]?input.context:'unknown',contextSource:'owner',personality:PERSONALITIES[input.personality]?input.personality:'polite',ownerStyle:OWNER_STYLES[input.ownerStyle]?input.ownerStyle:'everyday',language:'en',variant:Math.max(0,Math.min(100000,Number(input.variant)||0)),catDescription:String(input.catDescription||'').slice(0,1000),ownerDescription:String(input.ownerDescription||'').slice(0,500),memoryTitle:String(input.memoryTitle||'').slice(0,100),memoryNote:String(input.memoryNote||'').slice(0,1500),previousText:String(input.previousText||'').slice(0,600),memoryTags:(Array.isArray(input.memoryTags)?input.memoryTags:String(input.memoryTags||'').split(/[,，#\n]+/)).map(t=>String(t).trim().slice(0,50)).filter(Boolean).slice(0,20),catName:String(input.catName||'').slice(0,50),participantNames:(Array.isArray(input.participantNames)?input.participantNames:[]).map(n=>String(n).slice(0,50)).slice(0,5)};
 let r;try{r=await fetch('/api/captions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:AbortSignal.timeout(captionAIStatus.localOnly?190000:55000)})}catch(e){throw Error('AI could not connect. Your current caption is unchanged. Try a built-in version instead.');}
 let value;try{value=await r.json()}catch(e){throw Error('AI captions need the local backend. bash start-local-ai.sh.')}
 if(!r.ok)throw Error(typeof value.detail==='string'?value.detail:'AI could not generate a caption. Your current caption is unchanged.');
 if(value.source!=='ai-copy'||value.forFun!==true||typeof value.text!=='string'||!value.text.trim())throw Error('AI did not return a usable caption.');
 if(input.count===5&&(!Array.isArray(value.options)||value.options.length!==5||new Set(value.options.map(o=>o.text)).size!==5))throw Error('AI did not return five different options. Your saved caption is unchanged.');
 return value;
}
