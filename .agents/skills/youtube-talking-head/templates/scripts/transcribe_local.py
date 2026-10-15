"""Local verbatim transcription with faster-whisper (no upload, no API key).

Writes the kit's common word format:
  { text, language, audio_duration_secs, model, words: [{text, start, end, probability}] }
"""
import json
import sys
from pathlib import Path

import torch  # noqa: F401  (loads the CUDA/cuDNN DLLs CTranslate2 needs on Windows)
from faster_whisper import WhisperModel

src = Path(sys.argv[1])
out = Path(sys.argv[2])
model_name = sys.argv[3] if len(sys.argv) > 3 else "large-v3"

model = WhisperModel(model_name, device="cuda", compute_type="float16")
# A disfluent prompt nudges Whisper to keep fillers and restarts verbatim.
prompt = ("Eh, jadi, um, ya kan, gitu. Eh, maksudnya, apa namanya, uh, "
          "kita, kita coba lagi ya. Hmm.")
import numpy as np
import soundfile as sf

# Feed samples directly: faster-whisper's PyAV decode path breaks with av>=17.
audio, sr = sf.read(str(src), dtype="float32")
assert sr == 16000, "expects 16 kHz mono wav"
if audio.ndim > 1:
    audio = audio.mean(axis=1)
segments, info = model.transcribe(
    np.ascontiguousarray(audio), language="id", word_timestamps=True, beam_size=5,
    condition_on_previous_text=False, initial_prompt=prompt,
    vad_filter=True, vad_parameters={"min_silence_duration_ms": 400, "speech_pad_ms": 200},
)
words, texts, segs = [], [], []
for s in segments:
    texts.append(s.text.strip())
    segs.append({"start": round(s.start, 3), "end": round(s.end, 3), "text": s.text.strip(),
                 "avg_logprob": round(s.avg_logprob, 3), "no_speech_prob": round(s.no_speech_prob, 3)})
    for w in s.words or []:
        t = w.word.strip()
        if not t:
            continue
        words.append({"text": t, "start": round(w.start, 3), "end": round(w.end, 3),
                      "probability": round(w.probability, 3)})
    print(f"[{s.start:7.2f}-{s.end:7.2f}] {s.text.strip()}", flush=True)

data = {"text": " ".join(texts), "language": info.language,
        "audio_duration_secs": round(info.duration, 3), "model": f"faster-whisper {model_name}",
        "words": words, "segments": segs}
out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", out, len(words), "words", flush=True)
