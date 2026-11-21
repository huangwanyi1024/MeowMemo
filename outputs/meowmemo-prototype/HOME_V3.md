# Home V3 — interactive Peach Milk cat room

Local implementation on `feature/peach-milk-ui`. No commits or pushes performed.

## Files and integration

- `home-v3.js`: declarative resting spots, artwork mapping, session state, independent timers, fade transitions, accessible cat cards and adapters to existing memory/audio actions.
- `app.js`: activates V3 only for the main Home room when the original room and Peach Milk mode are selected; calls lifecycle synchronization after rendering; delegates V3 actions and playback indicators.
- `shop.js`: accepts an optional room-specific placement map. Existing owned items and transactions are unchanged.
- `styles.css`: V3-only scene, sprite, card, touch-target, idle/fade and reduced-motion styling. The scene preserves its 1672 × 941 aspect ratio with no cover cropping. Container-relative artwork sizing is independent of 44px minimum targets.
- `index.html`, `build_standalone.py`, `meowmemo.html`: load/package the new module and local assets. The standalone is approximately 19.6 MB including existing original journal media.
- `work/meowmemo-local-ai/test_home_v3.cjs`: 22 focused behavioral tests using an isolated VM, controllable timers and DOM doubles.

## Asset validation

Original V3 and Peach Milk packs remain unchanged. Copied 11 PNGs into `assets/home-v3/`: cat-free `backgrounds/living_room_empty.png`; all nine cat poses in `cats/` (orange, gray and cream × sitting, sleeping, playing); and `props/bed.png`.

The 1672 × 941 background was visually inspected and contains furniture but no cats or labels. All nine cat sprites and the bed have real alpha channels, with transparent pixels and no baked checkerboards. The cream sleeping sprite has a stray fragment at its right edge; a documented 6% CSS clip excludes that fragment without rewriting the original artwork. Some feather/mouse prop crops contain stray edge marks and were excluded. Other unneeded toys/box were not copied. Playing poses already contain toys, so an additional toy is not placed on top of them. A bed appears only when its resting spot is occupied. Existing owned shop decorations remain visible and interactive.

No replacement artwork was generated. The supplied sleeping sprites include illustrated Z marks; these are part of the provided artwork rather than application text.

## Cat behavior and resting spots

The first two actual `state.cats` profiles are used, without changing them. Zero profiles produce no cat sprites and a profile entry point. Coat-color metadata selects orange, gray or cream artwork; missing metadata uses a deterministic hash of the existing cat ID. No fake names, memories or sounds are created.

Feet anchors were measured against the supplied background (normalized x/y):

- Sofa cushion: .305 / .775, sitting or sleeping, width .155, layer 4.
- Cat tree: .780 / .235, sitting or sleeping, width .105, layer 3.
- Window-side floor: .505 / .610, sitting or sleeping, width .105, layer 2.
- Rug: .700 / .940, sitting, sleeping or playing, width .135, layer 6.
- Cat bed: .880 / .965, sleeping or sitting, width .135, layer 7.
- Toy corner: .415 / .990, playing or sitting, width .110, layer 6.

Each spot holds one cat. Existing profile spot preferences seed the initial placement; explicit subsequent profile spot edits take priority over session roaming. Each cat owns one independently randomized 20–45 second timeout: Every scheduled tick now commits an observable change: pose cycles use all three sprites and relocate to a compatible surface when needed; every third transition explicitly moves to a free spot. The original 40% no-op selection and indefinite focus/card suppression were removed. Movement fades out for 180ms and then replaces the pose/anchor; sprites never slide across the room. The destination is reserved before fading, preventing a race between cats. Breathing is subtle. Reduced motion disables idle animation and fade duration.

Timers pause/clean up when navigating away, hiding the page or leaving V3 mode; page restoration resumes them. Other modal dialogs pause transitions. Open cat cards and focused cats no longer pause the state machine: the button is retained, its image/style are updated in place, and the open card status is refreshed. Repeated renders do not create duplicate timers or event listeners.

## Interaction and persistence

A cat button opens a compact, nonmodal card below the scene so the room stays visible. It shows the real cat name/photo, pose/location and associated memory count. View Memories uses the existing cat filter; Add Memory opens Record with that cat selected; Play Saved Sound uses the existing configured/favorite audio through `tapSound` and `playMemory`. Missing audio is explicitly labeled. Close and Escape restore focus to the triggering cat.

No database stores, schema, keys or backend APIs were changed. V3 adds **no persistence writes**. Session poses/locations survive app rerenders but reset on reload; mapping remains stable across sessions and saved profile spot preferences remain the starting point. Runtime behavior never overwrites profile or room settings.

Saved custom rooms and classic mode retain their original layout, SVG pets and existing interactions. The new V3 state machine runs only on the new default Home artwork; it is intentionally not imposed on custom furniture layouts or the Memory page's mini-room.

## Verification

- `node --test work/meowmemo-local-ai/test_home_v3.cjs`: 33 tests passed, 0 failed. Coverage: zero/one/two cats, stable appearance, occupancy, pose validity, stay/pose/move transitions, bounded delays, card focus/Escape, missing media, real action adapters, reduced motion, pending-fade/navigation cleanup, repeated mounts, profile edits, visibility resume and unchanged source data/no storage writes.
- All eight existing frontend regression scripts passed, covering captions (750 combinations), memory media, room customization, room placement (25 combinations), shop/rewards, first-run data preservation, Peach Milk packaging and English UI.
- Standalone build and syntax/integration checks passed. Browser verification confirms the standalone loads the embedded V3 background and sprite assets.
- Browser screenshots at 375, 430, 768 and 1280px were captured and visually reviewed. A mobile cat-tree clipping issue was fixed by separating artwork size from touch-target size. Final 375px measurements show both targets at least 44px and both sprites/targets fully inside the scene. No horizontal overflow was detected at the four widths.
- Browser verified real cat-card opening, Escape/focus restoration and View Memories selecting the actual profile. A timed tree-to-rug transition was observed. No live recording or AI inference was performed.
- Screenshot files are outside the repo at `/private/tmp/meowmemo-v3/screenshots/`: `home-375.jpg`, `home-430.jpg`, `home-768.jpg`, `home-1280.jpg`, `interaction-375.jpg` (and standalone review if captured).

## Limits

Supplied art has only three coat families. Sitting uses 18 supplied color/pattern/fur variants. Dark maps to gray because no dark sprite was supplied. Sleeping/playing retain the neutral poses with coat-only color masks and vector markings; their fur silhouette is approximate. Accessories appear while sitting and are hidden for sleeping/playing poses where the neck is obscured. Profile data and the original editable SVG pets remain intact. Poses are static images with gentle CSS effects, not walking or skeletal animation. No new inventory, background service, model or database was introduced. Custom rooms keep their prior behavior. Existing app onboarding/profile initialization is unchanged; V3 itself creates no profiles. Browser audio permission/device-specific playback still warrants a manual check before release.

## Behavior investigation and developer diagnostics

The original implementation had valid timers and assets, but a 40% no-op chance after each 20–45 second timeout could create arbitrarily long apparent inactivity. Open cat cards paused both cats indefinitely; returning focus to a cat after closing its card could also pause that cat indefinitely. This investigation verified an actual production timer tick, image URL changes, and rendered spot changes in the browser.

`?debugCats=1` enables a developer-only panel in either source or standalone HTML. It lists each real cat's pose/spot, committed transition count, timer ticks, and schedule/reason status. Next Pose and Move Spot call the same `v3Transition` → `v3NextCat` → `v3PaintCat` functions as production timers. Auto Test uses a 3000ms timer per cat plus the 180ms fade and guarantees a pose or spot change on every tick; turning it off restores normal delays. Counts increment only after applying the rendered update. Debug state is session-only and cleared when leaving Home. Other rooms/modes show an explicit inactive diagnostic instead of silently appearing broken.

Browser verification: Next Pose changed `orange_sitting.png` to `orange_sleeping.png`; Move Spot changed the rendered surface and coordinates. With a cat card open, Auto Test advanced the displayed counter from 4 to 24, updating both real sprites and positions while keeping the card open and its status current. A normal production timer tick was also observed. All nine source assets were validated as distinct PNGs. Focused regressions check actual rendered image markup/style updates, previous focus/card suppression, guaranteed fast transitions and cleanup. No IndexedDB writes or backend changes were introduced.

## Shared editor and room appearance

`v3ResolveAppearance` and `v3Illustration` render both the Edit Cats sitting preview and the live Home V3 sprite from the existing saved profile. Bow, bandana and collar PNGs are transparent overlays with per-variant neck anchors. No new storage keys or writes were introduced; existing autosave persists changes. Current pose/spot and running timers survive appearance edits. Desk now has its own resting anchor and remains eligible for automatic roaming.

Focused verification: 33 Home V3 tests and 6 Edit Cats tests pass, covering shared preview markup, accessories, per-cat isolation, saved-value reload, and continued real timer transitions.

## Earlier sleeping/playing overlay calibration

Pattern was previously saved but ignored. The shared resolver now selects Stripes/Patches/Solid. The neutral supplied cream poses avoid the tabby sprites' baked-in stripes; three small alpha masks isolate light coat pixels from ink, facial features, pink ears and toys. A masked multiply layer supplies the coat color without a full-image filter. Tiny pose-specific SVG markings provide stripes or irregular patches; Solid adds none. Both editor and room use identical layers, including during production transitions. The original nine sprite files are unchanged. All patterns use the cream artwork's fluffy silhouette; fur-length controls remain saved but approximate.

Accessory alpha >64 bounds are within two pixels of each edge (bow 183×122, bandana 209×129, collar 172×130); trimming would not materially help. Visible sitting coat spans almost the whole canvas. Neck overlays now use 22% bow, 29% bandana, 25% collar widths at 52–53% height. Sleeping and playing explicitly hide overlays because their necks are obscured. Overlay proportions use the same frame in the editor and responsive room. The existing editor SVG width rule is overridden specifically for coat markings.

`python3 work/meowmemo-local-ai/build_cat_coat_masks.py` regenerates only the three derived masks (requires Pillow); the standalone builder needs no additional dependencies. Existing autosave, database keys, memories, profiles, and backend contracts are unchanged.

Browser calibration verified all three patterns on orange and gray, all three accessories through sitting/sleeping/playing, independent settings after reload, source and standalone mask embedding, cat cards, real pose/move controls, and Auto Test advancing from 14 to 34 after a pattern edit. Widths 375/430/768/1280 had no horizontal overflow. Preview marking widths match the actual illustration frame. No console errors were captured. 39 focused tests and all eight existing regression scripts pass. Browser screenshots were reviewed under `/private/tmp/meowmemo-pattern-fix/`. Live microphone recording and live AI inference were not exercised.

## Current sitting sprite integration

`V3_SITTING[color][pattern][fur]` selects one of 18 prepared sitting PNGs for both Edit Cats and Home V3. Saved color values map to orange/gray/cream; Dark uses the existing gray fallback. Pattern and fur are normalized through the existing finite options. Sitting renders the selected image directly, without approximate coat/pattern layers. Sleeping/playing retain their earlier real pose sprites and coat/pattern overlays; fur-length differences are not represented in those poses. Accessories hide while the neck is occluded. Returning to sitting restores the exact saved variant. No runtime timers, storage schema, user fields, names, photos, memories or backend APIs were changed.

The supplied individually segmented PNGs had missing outlines and some clipped fluffy edges. `work/meowmemo-local-ai/prepare_cat_appearance.py` recrops the intact source reference sheet, reconstructs alpha around the closed original ink contour, discards external fragments, and adds a 2px transparent safety margin. It generates only runtime copies under `assets/home-v3/appearance/`; all original packs stay intact. The 18 outputs have 0–255 alpha, complete bodies/ears/tails and reproducible hashes. No new illustrations were generated. Pillow is used only by this asset-preparation script, not by the application or standalone builder.

Accessory PNGs have negligible canvas padding. Prepared cat frames are tightly bounded, so accessory widths reference the visible illustration: Short bow/bandana/collar = 23/31/27%; Long = 24/32/28%. Neck centers are x42% (Short) and x41% (Long), at y56–58%. Both use the same inline width/position and preserved native accessory aspect ratio; the editor's old generic SVG/image rules do not override these layers. Browser screenshots were used to check every accessory with both fur lengths.

Verification: 39 focused tests (33 Home V3 + 6 editor) and all eight existing frontend regressions pass. Browser reviewed all 18 sitting combinations, six accessory/fur combinations, actual sleeping/playing/sitting restoration, normal timer ticks, Auto Test continuing after a fur edit, per-cat isolation and saved settings after refresh. Widths 375/430/768/1280 were inspected. Source and standalone assets were checked; screenshots are under `/private/tmp/meowmemo-fur-sync/`. Live microphone capture and AI inference were not exercised. Cream markings are intentionally soft in the supplied artwork. Fur/pattern silhouettes during non-sitting poses remain approximations; custom/classic rooms retain their earlier renderer.
