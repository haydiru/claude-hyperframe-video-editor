---
name: youtube-talking-head
description: The user's approved house style for editing their Indonesian talking-head YouTube videos (first used on "Nota yang Bocor", published 2026-10-04). Use whenever the user asks to edit a raw talking-head / YouTube video, even if they only say "edit video ini". Covers background replacement with their room, stutter-free cuts, reference-style motion graphics with breathers, synthesized music and SFX, QC, and the YouTube upload package (title, description, thumbnails).
---

# YouTube talking-head edit (approved house style)

The user approved this style after two rounds of feedback and does not want to
explain it again. Follow it by default; ask only about what is new in the video
(raw file path, rotation, chapters, anything they want different). Reply in
Indonesian. Load `edit-video`, `cut-silences`, `cut-mistakes`, `hyperframes`,
`hyperframes-cli`, and `gsap` for mechanics; where they conflict with this
skill on style, this skill wins.

Reference implementation: the published project `video-projects/talking-head-c025/`
(if it still exists) and the templates in this skill folder. Read
[house-style.md](reference/house-style.md) for every number and rule, and
[templates/README.md](templates/README.md) for the pipeline commands.

## The style in one screen

1. **Background**: the speaker is matted (RVM) and placed in the user's own room
   photo, pushed back and softly blurred, graded to the room (warm practicals,
   dark shirt, rim light, matched grain). Never a flat grey studio. Ask for the
   room image if `background/room_ref.png` is not in the new project.
2. **Cuts**: no "macet". Trim mid-phrase hesitations to ~0.11–0.15 s, commas
   ~0.20 s, sentence ends 0.30–0.42 s; cut false starts and stammers after a
   literal CTC check. Whisper invents doubled words at joins; trust CTC.
3. **Breathers**: insert 2.2–2.8 s silent holds before the title and before each
   chapter (not every point). Each carries a typewriter chapter card on paper
   with the chapter index (done chapters ticked) and a music swell; the beat
   drops when speech resumes.
4. **Graphics ("scrapbook noir")**: monochrome + one red (#E3262F), yellow only in
   thumbnails. Archivo 800–900 condensed uppercase, Special Elite (typewriter),
   Caveat (handwriting). Rotate graphic types: red-label captions, side text in
   the speaker's negative space (camera slides him 230 px at 1.25x), full dark
   boards with taped paper/notes, real screenshots taped and highlighted, a
   recurring diagram that returns (callbacks), number boards, a hard-cut red
   stamp for the punchline, a phone notification payoff. Leave clean talking
   stretches; never a graphic on every sentence.
5. **Camera**: WIDE/MED alternate on bigger jump cuts, CLOSE punch-ins on
   emphasis words, never two framing changes within 1 s, nothing entering over
   the face while the camera pans.
6. **Sound**: synthesized lo-fi bed (84 BPM, D minor) 14 dB under the voice,
   swelling in breathers, stopping dead on the punchline; SFX are typing, paper,
   marker, scribble, cash, risers into reveals, impacts on stamps. Mix to
   −14 LUFS / −1.5 dBTP.
7. **Packaging**: research the niche on YouTube in the built-in browser; titles
   use everyday words plus a number the speaker actually says (no jargon like
   "micro SaaS" in title/thumbnail). Make 2–3 thumbnails (big number + face +
   one object) for Test & compare; the user prefers open-eyed frames (even
   mid-speech) over closed-mouth frames with sleepy eyes; light retouch only.

## Workflow

1. Create `video-projects/<slug>/` (`npm run new-video -- <slug>`), copy the raw
   file into `raw/` (fix rotation losslessly, see templates/README.md), copy
   `templates/scripts`, `templates/assets`, `templates/thumbnail` into it and
   adapt the marked constants.
2. Transcribe locally (faster-whisper large-v3) unless the user picks a provider.
3. Build the room plate, preview a few frames, tune `plate_config.json`, render
   the full plate.
4. Review cuts with CTC, write `work/edl/approved_cuts.json`, set the chapter
   breathers (`INSERTS`), build the EDL and cut audio, retime the transcript.
5. Cut and chunk the plate, write `scripts/beats_v2.py` for the new script
   (use `beats_example_nota_bocor.py` as the pattern), run `build2.py`.
6. Generate music and SFX, mix, lint, validate beat sync, snapshot every beat
   with `--describe false`, fix, render `--quality high`, run `qc_render2.py`,
   inspect strips and hero frames, write VERIFY.md.
7. SRT, YouTube package (`renders/youtube_description.md`), thumbnails.
8. Do not upload; the user publishes. Before re-rendering a whole video for an
   uncertain improvement, show a 10-second A/B test first.

## Before the next recording (tell the user when relevant)

- Look into the lens: a beam-splitter teleprompter, or text right under the lens
  with the camera further back.
- Best background result: record in the real room so nothing is keyed; if
  keying, plain wall unlike skin/hair, 1–2 m behind, a back light on the hair,
  enough light for low ISO.
- Take a dedicated thumbnail photo with a deliberate expression.
