# Templates: pipeline for a new talking-head video

Copy into the new project, then adapt the marked constants:

```bash
P=video-projects/<slug>; S=.claude/skills/youtube-talking-head/templates
mkdir -p $P/scripts $P/assets/fonts $P/thumbnail $P/background $P/raw
cp $S/scripts/* $P/scripts/ && cp $S/assets/*.css $P/assets/ && cp $S/assets/fonts/*.woff2 $P/assets/fonts/
cp $S/thumbnail/*.py $P/thumbnail/
```

Room photo: `background/room_ref.png` (the user's own room; it is private, so
copy it from the previous project or ask the user, never into this skill).
GSAP: copy `assets/gsap.min.js` from any existing project.

## Adapt per video

| File | What to change |
| --- | --- |
| `scripts/plate.py` | `RAW` file name |
| `scripts/plate_config.json` | `crop` (head room), grade if the light differs, `chair_zones` (or empty) |
| `scripts/edl_build2.py` | `"source"` path, `INSERTS` (source end time of the last word before the title and each chapter) |
| `scripts/ctc_check.py` | path of the 16 kHz mono source wav |
| `scripts/make_transcript.py` | `SAFE` / `SEQ` corrections (brand names, verified mishearings) |
| `scripts/hflib2.py` | `SHOT` sizes of the screenshots used, `CHAPTERS` titles |
| `scripts/beats_v2.py` | write new for this script; pattern in `beats_example_nota_bocor.py` |
| `scripts/build2.py` | `<title>` and the root composition id |
| `scripts/make_srt.py`, `qc_render2.py` | output names |
| `thumbnail/make_thumbs.py` | texts, numbers, face frames, positions |

## Order (run from the project folder with the video venv; its path is in Claude's memory)

1. Orientation, lossless: `ffmpeg -display_rotation:v:0 0 -i <in.mov> -map 0 -c copy -movflags +faststart raw/<name>_landscape.mov`
2. `python scripts/transcribe_local.py` (faster-whisper large-v3, local)
3. `python scripts/make_bg_room.py`; optional `python scripts/clean_plate.py`;
   `python scripts/plate.py preview --times 30,120,300`; tune; `python scripts/plate.py full`
4. Mistake review (`cut-mistakes` skill + `python scripts/cut_words.py a:b ...`),
   write `work/edl/approved_cuts.json`; `python scripts/edl_build2.py`;
   `python scripts/make_transcript.py` (later text-only fixes: `--reuse`)
5. `python scripts/cut_plate.py`; `python scripts/join_jumps2.py`; encode the 4 chunks:
   `ffmpeg -i work/plate/plate_cut_video.mp4 -vf "trim=start_frame=A:end_frame=B,setpts=PTS-STARTPTS" -an -c:v libx264 -preset medium -crf 17 -tune film -pix_fmt yuv420p -g 30 -bf 2 -movflags +faststart assets/video/plate_N.mp4`
6. `python scripts/make_textures.py`; write `scripts/beats_v2.py`; `python scripts/build2.py`
7. `python scripts/make_audio2.py && bash scripts/make_mix.sh`
8. `npx hyperframes lint`; `node ../../scripts/validate-beat-sync.mjs .` (from repo root:
   `node scripts/validate-beat-sync.mjs video-projects/<slug>`);
   `npx hyperframes snapshot . --describe false --no-end --at <beat ends>`
9. `npx hyperframes render --quality high -o renders/<name>_final.mp4`;
   `python scripts/qc_render2.py renders/<name>_final.mp4`; write VERIFY.md
10. `python scripts/make_srt.py`; YouTube package; thumbnails:
    `python thumbnail/make_cutouts.py <t> ...`, `python thumbnail/retouch.py <tag> ...`,
    `python thumbnail/make_thumbs.py`

`test_hair.py` is the pattern for a 10-second A/B test of a compositor change
before committing to a full re-render.

Fonts in `assets/fonts/` (Archivo, Special Elite, Caveat) are SIL Open Font
License 1.1 fonts from Google Fonts (fonts.google.com).
