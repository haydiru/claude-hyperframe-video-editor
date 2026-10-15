"""Literal (non-cleaning) CTC transcription of short source windows, used to
verify whether a suspected repeated word was actually spoken."""
import sys
import numpy as np
import soundfile as sf
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

MID = "indonesian-nlp/wav2vec2-large-xlsr-indonesian"
proc = Wav2Vec2Processor.from_pretrained(MID)
model = Wav2Vec2ForCTC.from_pretrained(MID).to("cuda").eval()
a, sr = sf.read(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "work/audio/raw_16k_mono.wav"), dtype="float32")


def ctc(s, e):
    x = a[int(s * sr):int(e * sr)]
    inp = proc(x, sampling_rate=sr, return_tensors="pt").input_values.to("cuda")
    with torch.no_grad():
        logits = model(inp).logits[0]
    ids = logits.argmax(-1).cpu().numpy()
    # character timeline: collapse repeats, drop blanks, keep times
    blank = proc.tokenizer.pad_token_id
    step = (e - s) / len(ids)
    out, prev = [], None
    for i, t in enumerate(ids):
        if t != prev and t != blank:
            out.append((s + i * step, proc.tokenizer.convert_ids_to_tokens(int(t))))
        prev = t
    text = "".join(c for _, c in out).replace("|", " ")
    return text, out


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        s, e = map(float, arg.split(":"))
        text, chars = ctc(s, e)
        words, cur, t0 = [], "", None
        for t, c in chars:
            if c == "|":
                if cur:
                    words.append(f"{cur}@{t0:.2f}")
                cur, t0 = "", None
            else:
                if not cur:
                    t0 = t
                cur += c
        if cur:
            words.append(f"{cur}@{t0:.2f}")
        print(f"{s}-{e}: " + " ".join(words))
