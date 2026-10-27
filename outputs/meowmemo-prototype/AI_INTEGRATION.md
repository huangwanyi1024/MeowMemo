# Next stage: audio inference and personalized creative copy

These two features intentionally remain separate. A local acoustic API is now connected through bash start-local-ai.sh. No cloud caption API is connected.

## 1. Owner observations / 主人确认

`playfulFeedback()` in `app.js` collects `food`, `brushing`, `isolation`, `other`, or `unknown`. Icons always have descriptive text. The small cat blinks after a choice and tilts when the owner chooses unknown.

Saved memory fields:

```js
{
  confirmed: 'food',
  feedback: {
    label: 'food',
    source: 'owner',
    confirmedAt: 'ISO date or null if no explicit selection'
  },
  inferenceStatus: 'not-analyzed',
  modelVersion: null
}
```

Personal tags (`tags`) are a separate field. Choosing a bowl/brush/room does not create a model prediction. `unknown` is a valid observation, not an error. Existing memories can be corrected in Edit details.

When real inference is added, pass the actual original audio to an acoustic model/API. Persist the model's raw output, model version, evidence and abstention separately from `confirmed` and `feedback`. The UI may display a tentative suggestion; only an owner's action updates the observation. Never use a generated caption as an inference result.

## 2. Creative captions / 猫咪嘴替

`captions.js` exports the application-level function:

```js
await generateFunCaption({
  catId,
  context,          // owner-confirmed label; unknown stays unknown
  contextSource: 'owner',
  personality,      // owner-selected fictional expression style
  ownerStyle,       // everyday / academic / fitness / work / gaming
  language,        // en / zh
  variant,
  catDescription,   // owner's profile note, not currently parsed by templates
  inferenceStatus
})
```

It currently uses `builtinCaptionProvider.generate()`, an offline catalog: 5 situation labels × 5 cat voices × 5 owner styles × 2 languages × 3 variants. The 750 combinations use selected labels only; they do not understand or classify audio. Freeform profile notes are retained for a later provider but are not semantically interpreted by the current templates.

Future AI-copy providers should accept the same normalized input. Invoke them from a server endpoint with a protected API key, never from a key embedded in this HTML. Return the same caption object with `source: 'ai-copy'`, a real `generatorVersion`, and `forFun: true`. On a network/provider failure, offer a clearly labeled built-in fallback; do not present fallback text as AI-generated.

The language model may style the owner's chosen situation and profile description. It must not invent a diagnosis, assert inferred emotion, interpret an unknown situation as hunger, or represent its text as a literal translation. Keep captions short and allow owner editing.

## 3. Persisted caption and profiles

Each memory's `funCaption` is a snapshot:

```js
{
  text, catId, context, personality, ownerStyle, language, variant,
  source: 'builtin-template' /* or owner-edited / ai-copy */,
  generatorVersion: 'builtin-v1',
  basedOn: 'owner-observation',
  forFun: true,
  createdAt
}
```

`Make it yours` saves `source: 'owner-edited'` and `editedAt`. New captions are generated only on saving a new memory or pressing the explicit generation button. Reopening a memory or editing a profile must not overwrite a saved caption. If the situation label changes, the caption shows a refresh hint; it is not silently regenerated.

Each cat has `personality` plus the existing freeform `note`. Global owner preferences use the settings entry `owner`, containing `style` and `language`. They are not acoustic labels. Existing profiles merge defaults without discarding birthday, photos, waiting location or tap sound.

JSON backups include `funCaption`, owner observations, cat voices and owner preferences. Old backups remain importable with neutral defaults. Original audio/image/video blobs are retained unchanged.

## 4. Playback and UI

- Memory detail: cat avatar, creative caption, source label, cat/language controls, another-version/edit actions, then original media playback.
- No text-to-speech or generated meow. The caption is not read aloud.
- Home tap sound continues using a real per-cat audio memory. Tiny triangular-mouth animation is atmosphere, not lip synchronization.
- All sources retain a visible **For fun / not a literal translation** label. Model inference, when connected, needs its own separate evidence/status UI.
- Together stays a further-development concept preview; this update does not add sharing.

## 5. Remaining work before the assignment's AI MVP

Add and evaluate genuine acoustic inference; report the planned cat-held-out evaluation, macro-F1 and confusion matrix where applicable; test abstention with silence/non-cat/noisy audio; write the model card; deploy HTTPS; run the pilot and prepare the demonstration video. This offline creative-copy update does not complete those requirements.


## 2026-10-26 update: actual local acoustic service

`work/meowmemo-local-ai/server.py` serves the UI and `/api/analyze` on loopback port 8765. It accepts the original audio/video as multipart `file`, decodes locally and returns actual acoustic results; it receives no cat name, profile, owner tags, images or situation labels. `/ai-lab` exposes labeled public test samples separately.

Record: `analyzeDraft` sends only the selected capture and guards against stale in-flight results after replacing a draft/capture. Memory: `analyzeMemory` persists `analysis`, `modelVersion`, `inferenceStatus`; owner `confirmed`, `feedback`, `funCaption` and original media are untouched. `cleanAnalysis` validates imported analysis metadata; backups include it. Replacing/removing a capture resets draft analysis.

Model ID `catmeows-local-v2`: YAMNet mean embeddings + MFCC + logistic regression, running on CPU. Test accuracy 40.0%, macro-F1 .372 on 6 held-out cats / 120 clips. v2 reuses the split after observing v1 failure: exploratory only. Since validation is weak, deployment suppresses context suggestions as uncertain; raw scores are experimental, not calibrated confidence. Model Card and complete failed baseline results are in work/meowmemo-local-ai/.

Caption provider remains built-in and clearly labeled. A future cloud copy API should still accept owner-confirmed context only; do not silently feed tentative model candidates into captions. No speech synthesis or synthetic cat recording was added. Local model deployment does not complete independent evaluation, pilot or public HTTPS deployment.


## 2026-10-26 update: opt-in personalized AI captions

Backend: `caption_service.py`, `/api/captions/status`, `/api/captions`. OpenAI Responses API, structured JSON text output, `store:false`, reasoning none, maximum 220 output tokens, one request per explicit action, no automatic retries. Default model gpt-6-luna; optional server-only gpt-6.1-terra. Credentials stay in backend `.env.local`/environment. Cloud captions are currently disabled; see the local-provider update below.

`CaptionInput` forbids extra fields, including media and model guesses. Personality and owner style are selected enums, context is only `owner`, unknown remains unknown; freeform notes are untrusted story data. Prompt prohibits literal translation, diagnosis and invented intent. These prompt constraints require live evaluation after configuration; mocked tests validate contracts only.

Frontend `generateFunCaption(input)` uses built-in by default; only `provider:'ai'` invokes the backend. AI payload includes `catDescription`, `ownerDescription`, `memoryTitle`, `memoryNote`, and selected enums. The server returns `source:'ai-copy'`, an actual model/provider version, and a `personalization` text snapshot. `cleanCaption` preserves that snapshot and editedAt through backup restoration. No fallback is misrepresented as AI.

Owner data adds `about` (max 500). My Cat preview is ephemeral and independent of saved observations/profiles. Preview generation does not create a memory. Memory detail AI generation saves the caption only; original recording, profile and acoustic result stay unchanged. Late responses do not reopen a closed or unrelated dialog.

Validation: 750 built-in combinations, old/new owner settings, text-only payload, unknown context, provenance round-trip, explicit provider errors, missing-key no-request behavior, upstream timeout/refusal/incomplete output, prompt data fields and server media rejection. Local-provider validation is recorded below; earlier OpenAI account testing found insufficient credit.


## 2026-10-26 · Local personalized captions / 本地个性化台词

The default caption provider on this Mac is now **Qwen3.5-4B via project-local Ollama**. No OpenAI credit or API key is required. The normal launcher / bash start-local-ai.sh starts the local backend and, when needed, its owned Ollama runtime. Use the existing http://127.0.0.1:8765/meowmemo.html origin to keep browser memories and profiles.

My Cat → Try their playful voice → Generate AI caption works in English and Chinese. Memory details can save local AI caption snapshots; preview does not save or change profiles. Built-in controls hide while AI is available. Automatic new-memory captions remain built-in until explicitly regenerated. Original media remains unchanged. Selected text goes only to loopback Ollama, with cloud disabled and no remote fallback.

Actual M5 / 16 GB check: roughly 4 GB model download, 5.2 GB runtime GPU memory, about 0.5–1.3 s for the sampled warm short captions; cold loading takes longer. Quality is imperfect: role confusion and invented details can occur. Manual editing remains available. This replaces the creative text generator only; acoustic model accuracy is unchanged. See work/meowmemo-local-ai/CAPTION_SETUP.md for setup, tests and optional cloud configuration. Portable frontend ZIP excludes models, runtime and credentials.


## Little shop integration

`shop.js` loads before `app.js` in source and standalone builds. It stores a validated `shop` record in the existing settings store. `saveRewardedMemory` atomically writes a new memory plus its +2 reward; explicit first sharing awards +5. Sharing uses selected original media only and never calls either AI provider. Backup includes shop state; import does not award treats. Keep owner labels, captions and acoustic results separate from reward events. Future server/account implementations should replace local wallet trust with server transactions if points gain external value.


Situation filtering uses `m.confirmed` (legacy missing → unknown), never an acoustic candidate. PNG sharing renders only cat names/date/title/first photo, recording-derived waveform and saved fictional caption. It does not invoke an AI provider. A missing caption uses a neutral fixed For fun line without saving or claiming a model output. Original media bytes remain unchanged.


Caption v2 story-first update: AI now receives bounded memoryTags, catName and participantNames from the selected memory. The current note/title/tags take precedence over personality and owner style; unknown classification no longer erases the explicit story. Old captions are excluded as local-model evidence. Local guards allow one local correction for unrelated study/food topics or human-narrator phrasing, then preserve existing text on failure. No cloud fallback, audio inference change or weight training. Freeform profiles are used by the local generator only when no current story is provided. Existing saved captions remain unchanged until explicit regeneration. Input snapshots retain tags/cast through backup import; a changed story/tag list shows a refresh hint. Details and actual fictional regression results are in work/meowmemo-local-ai/CAPTION_SETUP.md and artifacts/caption-grounding-v2-checks.json.


### Five creative choices
The AI request now sends count=5, selected cat/personality/style, current story/title/tags/context, participant profile text, and preceding options to avoid. The backend returns five choices in one batch. Generation preserves the saved caption; explicit selection saves one. Latest choices per cat/language survive reload and backup/restore. Local Qwen stays free and on-device; optional cloud uses one request per click. Small-model output remains fictional and requires user review.


### Single-caption rotation (current UI)
Generate AI caption now displays and saves exactly one result per click. Five options remain an internal pool, keyed by cat/language and a signature of story, tags, situation, personality, expression style and profiles. Each click consumes one unused option; exhaustion requests a fresh batch avoiding the preceding texts. Changed inputs invalidate the pool. Used-text progress and signatures persist through reload and backup/restore. Preview uses the same logic without saving a memory. There is no candidate list or selection step. Request/storage failures preserve the existing caption and pool progress.


### Room photo recognition
`GET /api/rooms/status` checks the installed local model's vision capability. `POST /api/rooms/analyze?roomType=living` accepts one multipart photo. Images are validated with Pillow, reduced to at most 768 px in a metadata-free JPEG copy, and sent only to loopback Ollama. The result is a bounded furniture list and approximate positions, rendered with editable SVG components. The original photo remains in browser storage. This is an experimental scene draft, not precise reconstruction. Scene editing and templates work without the service. See the backend ROOM_CUSTOMIZATION.md for contracts and checks.
