# Working without Anthropic API (Claude Pro UI is enough)

Claude **Pro** (claude.ai) does **not** include the Anthropic **API** key used by
scripts. You do not need the API for this pipeline.

## Recommended production path (no API)

```
You (Claude.ai / PowerPoint / Keynote)
        |  export .pptx  (with speaker notes filled)
        v
python cli.py import-pptx path/to/deck.pptx --topic "My video"
        |
        v
python cli.py run --project <id> --from-stage voice --voice <your_clone_id>
        |
        v
final.mp4 + transcript + chapters + shorts ...
```

Stages **scriptwriter** and **slidebuilder** are skipped because the deck and
outline already exist.

---

## Option A — Import an existing PPTX (best)

1. Create slides in Claude.ai, PowerPoint, Google Slides, Keynote, etc.
2. **Critical:** put the full narration in **speaker notes** per slide
   (natural speech, not bullet fragments).
3. Export / save as `.pptx`.
4. Import:

```bash
python cli.py import-pptx ./my-deck.pptx --topic "Docker networking" --voice mohit
python cli.py run --project <printed-id> --from-stage voice
```

`import-pptx` will:

- copy the file to `projects/<id>/slides.pptx`
- extract titles/bullets/notes into `outline.json`
- write a starter `seo.json` (you can edit tags/title anytime)

If notes are empty, the importer synthesizes weak notes from on-slide text and
logs a warning — fix notes and re-import for pro quality.

---

## Option B — Import outline JSON (then build PPTX here)

1. In Claude.ai, paste the system prompt from
   `modules/scriptwriter/prompts/outline_prompt.md`.
2. Ask for **JSON only** matching the schema.
3. Save as `outline.json`.
4. Optionally save SEO JSON from `seo_metadata_prompt.md`.

```bash
python cli.py import-outline ./outline.json --topic "My topic" --seo ./seo.json
python cli.py run --project <id> --only slidebuilder
python cli.py run --project <id> --from-stage voice --voice mohit
```

---

## Option C — Anthropic API later (optional)

If you later buy API credits:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python cli.py run --topic "..." --voice mohit
```

Without the key, scriptwriter automatically uses a local stub outline (fine for
architecture tests, not for publishing).

---

## SEO without API

After import, edit `projects/<id>/seo.json` by hand:

- `title`, `description`, `tags`, `thumbnail_text`

Or leave defaults; chapters stage still fills timestamps after transcription.

---

## Minimal publish path checklist

1. `prepare-voice` with your clean audio (see `docs/VOICE_CLONING.md`)
2. `import-pptx` with speaker notes
3. `run --from-stage voice`
4. Review `final.mp4`, edit `seo.json` / `chapters.txt`
5. Publisher dry-run or YouTube OAuth upload
