#!/usr/bin/env bash
# Premix voice + music bed + SFX, then 2-pass loudnorm to -14 LUFS / -1.5 dBTP.
set -e
cd "$(dirname "$0")/../assets/audio"
ffmpeg -v error -y -i voice_master.wav -i music_bed.wav -i sfx.wav \
  -filter_complex "[0][1][2]amix=inputs=3:normalize=0:duration=first" -c:a pcm_f32le ../../work/audio/premix.wav
ffmpeg -hide_banner -i ../../work/audio/premix.wav -af loudnorm=I=-14:TP=-1.5:LRA=7:print_format=json -f null - 2>&1 \
  | sed -n '/{/,/}/p' > ../../work/audio/mix_ln.json
g() { grep "$1" ../../work/audio/mix_ln.json | grep -o '[-0-9.]*'; }
ffmpeg -v error -y -i ../../work/audio/premix.wav -af "loudnorm=I=-14:TP=-1.5:LRA=7:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true,aresample=48000:osf=s16:dither_method=triangular" \
  -c:a pcm_s16le final_mix.wav
