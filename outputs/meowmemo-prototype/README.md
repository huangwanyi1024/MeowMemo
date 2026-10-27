# Frontend / 网页源码

See the repository root README for the complete setup and reviewer walkthrough. From repository root, run `python3 start.py --web` to preview or `python3 start.py --ai` after AI setup. Use the repository-root .sh launchers.

Edit `index.html`, `styles.css`, `scene.js`, `captions.js`, `shop.js`, `rooms.js`, `app.js` and `assets/`. Run `python3 outputs/meowmemo-prototype/build_standalone.py` from repository root to rebuild `meowmemo.html`.

Original example photographs are included. The approved Oct 26 journal snapshot in demo-data.js is bundled and embedded into meowmemo.html: six memories / three original recordings and profiles load into a completely new journal automatically. Later edits remain in IndexedDB, separate from the snapshot. Existing or intentionally emptied journals are never overwritten. Optional inference needs the local Python backend; creative captions and room-photo recognition additionally need local Ollama. Together is a future-development preview.
