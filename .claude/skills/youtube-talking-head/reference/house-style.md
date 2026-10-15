# House style: numbers and rules

Distilled from "Nota yang Bocor" v2 (approved and published 2026-10-04) and the
user's feedback on v1. The reference edit they benchmark against is
youtube.com/watch?v=8Lz530r09WU (Raymond Chin).

## What the user rejected in v1 (do not repeat)

- Flat grey "studio" backdrop: looked amateur.
- The same overlay treatment over and over, glass panels, Plus Jakarta / mono
  "dashboard" fonts: looked like an AI template.
- Mid-phrase hesitations left in: heard as "macet" (stuttering).
- Only clicks and whooshes for sound: wanted music and curiosity-building effects.
- Thumbnail faces with squinting/sleepy eyes (open-eyed mid-speech is better).

## Background (plate)

- Raw: phone HEVC 4K. Crop 3340×1878 → 2560×1440 plate (camera headroom up to 1.33x).
- Matte: RVM resnet50, `downsample_ratio` 0.3; clip 0.06–0.92; choke 1 px; core
  erode 3 px; edge colour extended 7 px from the interior (no cream-wall rim).
- Grade (room look): wb gains [1.0, 1.15, 2.65], exposure −0.95 EV, contrast 1.4,
  shoulder 0.55, saturation 0.92, shadow tint [−0.012, 0.01, 0.02], neutral
  darken (grey hair sheen) amount 0.38.
- Light wrap 0.08, warm rim [1.0, 0.66, 0.38] strength 0.22 (stronger on the
  lamp side), grain bg 0.006 / fg 0.002.
- Room image: scaled to 92 %, extra lens blur, slightly darker/desaturated,
  bloom on practicals (`make_bg_room.py`).
- Tested and NOT worth a full re-render: finer matte + wall decontamination +
  noise matching (difference too small; source softness is the limit).

## Cuts (EDL v2)

- Pause detection −52 dBFS, min 0.20 s; classify by the word before the pause:
  mid-phrase (0.15, 0.08), comma (0.24, 0.13), sentence (0.32, 0.19) (+0.12 for
  long pauses). Frame grid 30 fps, 1600 samples per frame; 10 ms equal-power
  crossfades; room tone from the quietest second fills holds.
- Mistakes: reviewed list in `work/edl/approved_cuts.json` with reasons; verify
  each with `cut_words.py` (literal wav2vec2 CTC, `indonesian-nlp/wav2vec2-large-xlsr-indonesian`).
- Breathers: `INSERTS = [(word_end_source_s, secs, tag)]`, title 2.2 s, chapters
  2.8 s, placed in the first silent run after that word.
- Typical result: 595 s raw → 514 s, ~215 pause trims, ~14 mistake cuts.

## Camera framings (root `#cam`, transform-origin 50% 32%)

| Name | scale | x | y |
| --- | --- | --- | --- |
| WIDE | 1.0 | 0 | 0 |
| MED | 1.12 | 0 | 6 |
| CLOSE | 1.28 | 0 | 14 |
| SIDE_L (text right) | 1.25 | −230 | 0 |
| SIDE_R (text left) | 1.25 | +230 | 0 |

Rules: set new framing under full boards; slide 0.75 s `power2.inOut` into side
text; opposite sides pan 0.9 s directly; side→CLOSE cuts straight in; join
toggles only when jump ≥ 2.6 and no other change within 2 s; delay side content
that enters during a pan (≥ 0.75 s).

## Graphics vocabulary (`hflib2.py` + `ui2.css`)

- `caption(label, big, red=…)`: red label + heavy 84 px uppercase line, bottom
  centre; one word in a red block. Keep to one line (≤ ~30 chars; shrink to 74 px).
- `side(html, where)`: 740 px column at x 1110 (right) or 90 (left), from y 190.
  Kicker (typewriter) → items that appear on their words → a stamp or hand note.
- `full(inner)`: dark textured board; `.take` wrapper wipes with clip-path so
  taped items wipe with it; `chain_out` hands over to the next board; `cut=True`
  for a hard-cut punch card ("WHY NOT?").
- `chapter_card`: paper + paperclip, red "CHAPTER 0X", typewriter title with
  cursor, handwritten sub, chapter index on top.
- `shot(...)`: real screenshot (from `real_assets/`), tilted ±1–2.5°, two tape
  strips, highlighter sweeps (multiply yellow) and red marker ellipses.
- Recurring diagram (the 5-step staircase) returns at each step with the
  current step circled, done steps ticked, later steps dimmed; a cost version
  closes the section.
- Number boards: content must land within ~0.5 s after the wipe (QC flags empty
  boards); counters for money; riser + impact on the biggest number.
- Phone notification = the viewer's own future app ("Aplikasi lo"), never a real brand.
- Currency: "Rp" keeps its case inside uppercase styles (`.rp`, auto in build2).

Pacing: ~55 beats for 8.5 min; side ≈ 40 %, full ≈ 28 % of runtime; no stretch
> 18 s without a graphic, but leave several clean talking stretches of 4–10 s.

## Sound

- Music: `make_audio2.py` sections from `work/music_plan.json` (intro = hook, break
  = breathers, groove, outro last ~10 s); bed levelled to voice median −14 dB;
  breathers +5 dB swell; full stop for the punchline card.
- SFX trims measured against voice: impact ×0.6, paper ×0.7; typewriter keys
  gain 0.3–0.35 for long lines; check no SFX sits > 3 dB over speech for long.
- Mix: two-pass loudnorm −14 LUFS, −1.5 dBTP (`make_mix.sh`).

## QC checklist (all must pass before saying "done")

- `npx hyperframes lint` 0 errors; `node scripts/validate-beat-sync.mjs <project>` all OK.
- Root keeps `data-start="0"` (lint) even though preflight complains about it.
- Plate chunk `data-duration` = rounded end − rounded start (else 0.0001 s overlap).
- `npx hyperframes snapshot . --describe false --at <every beat end>`; never let
  it call Gemini.
- Render `--quality high` (~17–20 min for 8.5 min), then `qc_render2.py`: frame
  count = EDL, A/V offset 0, −14 LUFS, no pops, empty-board runs < 0.5 s;
  "black edge" hits are usually the dark room walls (inspect, don't assume).
- Strips over every transition; check face never covered; hero frames sheet.

## Upload package

- Research: YouTube search via the built-in browser (extract results from
  `ytInitialData`), view thumbnails at `i.ytimg.com/vi/<id>/hqdefault.jpg`.
- Title ≤ ~65 chars, everyday words + one spoken number; thumbnail carries the
  other number (e.g. title "Modal Rp300 Ribu", thumbnail "Rp14,9 JT/BULAN").
- Thumbnails 1280×720 JPG: 2–4 words huge (Archivo 900, yellow #FFD43B for money,
  white, red label), face on the right with warm glow, one object on the left
  (receipt with marker circle, arrow), readable at 246 px wide.
- Description: hook + keywords in the first two lines, what's covered, chapters
  (0:00 first, each ≥ 10 s, one per line), tools with links, estimate
  disclaimer, comment question, 3 hashtags; plus tags and a pinned comment.
  Chapters only become links after publishing.

## Machine notes (Windows, this PC)

- Python venv at a short path (location is in Claude's memory for this PC); `import torch` before
  faster-whisper (cuBLAS DLLs); feed numpy audio (PyAV issue).
- NVENC unavailable → libx264; CUDA decode works, crop on CPU.
- Studio reads media with a 2 GiB cap → 4 plate chunks, bounds inside breathers.
- Stopping a background render leaves node + chrome-headless: `taskkill /T /F`
  the `hyperframes.mjs render` PID.
- OpenCV 5 has no Haar cascades: face/eye positions come from the matte + dark
  blobs (`thumbnail/retouch.py`).
