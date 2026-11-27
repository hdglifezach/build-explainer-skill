"""transcribe.py - word timestamps with faster-whisper (local, free).

  python -X utf8 transcribe.py audio/vo.wav [--model small.en] [--vocab "Term1,Term2"] [--device auto|cpu|cuda]

Writes <wav dir>/<wav stem>.scan/ears.json  {"segments":[{"s","e","text","words":[{"w","s","e"}]}]}
and        <wav dir>/<wav stem>.scan/ears.md  (one line per word with times).
The film's spec.py reads audio/vo.scan/ears.json. --vocab lists names/terms to bias recognition.
"""
import argparse
import json
from pathlib import Path


def pick_device(want):
    if want != "auto":
        return want, ("float16" if want == "cuda" else "int8")
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:
        pass
    return "cpu", "int8"


def transcribe(wav, model="small.en", vocab="", device="auto"):
    from faster_whisper import WhisperModel
    dev, ctype = pick_device(device)
    try:
        m = WhisperModel(model, device=dev, compute_type=ctype)
        segs, _ = m.transcribe(str(wav), word_timestamps=True, language="en" if model.endswith(".en") else None,
                               initial_prompt=(", ".join(x.strip() for x in vocab.split(",") if x.strip()) or None),
                               condition_on_previous_text=False)
        segs = list(segs)
    except Exception as e:
        if dev != "cuda":
            raise
        print(f"cuda failed ({e}); retrying on cpu")
        m = WhisperModel(model, device="cpu", compute_type="int8")
        segs, _ = m.transcribe(str(wav), word_timestamps=True, language="en" if model.endswith(".en") else None,
                               initial_prompt=(", ".join(x.strip() for x in vocab.split(",") if x.strip()) or None),
                               condition_on_previous_text=False)
        segs = list(segs)
    out = []
    for s in segs:
        words = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)} for w in (s.words or [])]
        out.append({"s": round(s.start, 3), "e": round(s.end, 3), "text": s.text.strip(), "words": words})
    return {"segments": out}


def write(data, wav):
    wav = Path(wav)
    d = wav.parent / (wav.stem + ".scan")
    d.mkdir(parents=True, exist_ok=True)
    (d / "ears.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf8")
    lines = ["# words", ""]
    for seg in data["segments"]:
        lines.append(f"## [{seg['s']:.2f}-{seg['e']:.2f}] {seg['text']}")
        for w in seg["words"]:
            lines.append(f"{w['s']:7.2f} {w['e']:7.2f}  {w['w']}")
        lines.append("")
    (d / "ears.md").write_text("\n".join(lines), encoding="utf8")
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("--model", default="small.en")
    ap.add_argument("--vocab", default="")
    ap.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    a = ap.parse_args()
    data = transcribe(a.wav, a.model, a.vocab, a.device)
    d = write(data, a.wav)
    n = sum(len(s["words"]) for s in data["segments"])
    print(f"{n} words -> {d / 'ears.json'}")


if __name__ == "__main__":
    main()
