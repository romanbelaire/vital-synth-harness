from __future__ import annotations

import array
import math
import wave
from pathlib import Path


def analyze_wav(path: Path) -> dict[str, float | int]:
    """Return lightweight, reproducible descriptors without third-party DSP."""
    with wave.open(str(path), "rb") as wav:
        channels, width, rate, frames = wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()
        raw = wav.readframes(frames)
    if width not in (1, 2, 4):
        raise ValueError(f"Unsupported PCM sample width: {width}")
    code = {1: 'B', 2: 'h', 4: 'i'}[width]
    values = array.array(code)
    values.frombytes(raw)
    scale = float((1 << (width * 8 - 1)) - 1)
    samples = [((value - 128) / 128.0 if width == 1 else value / scale) for value in values[::channels]]
    if not samples:
        raise ValueError("WAV contains no samples")
    rms = math.sqrt(sum(s * s for s in samples) / len(samples))
    peak = max(abs(s) for s in samples)
    crossings = sum((a >= 0) != (b >= 0) for a, b in zip(samples, samples[1:]))
    # A small DFT gives a robust brightness proxy, without claiming semantic recognition.
    window = samples[: min(len(samples), 4096)]
    n = len(window)
    if n < 8:
        centroid = 0.0
    else:
        mags = []
        for k in range(1, n // 2):
            real = sum(window[t] * math.cos(2 * math.pi * k * t / n) for t in range(n))
            imag = sum(window[t] * math.sin(2 * math.pi * k * t / n) for t in range(n))
            mags.append((k * rate / n, math.hypot(real, imag)))
        total = sum(magnitude for _, magnitude in mags)
        centroid = sum(freq * magnitude for freq, magnitude in mags) / total if total else 0.0
    return {"sample_rate": rate, "channels": channels, "frames": frames,
            "duration_seconds": round(frames / rate, 4), "peak": round(peak, 6),
            "rms": round(rms, 6), "zero_crossing_rate": round(crossings * rate / max(frames - 1, 1), 3),
            "spectral_centroid_hz": round(centroid, 2)}
