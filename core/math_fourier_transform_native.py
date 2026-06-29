"""Math Fourier Transform -- DFT, FFT, spectral analysis."""
from dataclasses import dataclass
from pathlib import Path
import json, math, cmath

@dataclass
class FourierResult:
    transform_id: str = ""
    frequencies: list[float] = None
    magnitudes: list[float] = None
    phases: list[float] = None

    def __post_init__(self):
        if self.frequencies is None:
            self.frequencies = []
        if self.magnitudes is None:
            self.magnitudes = []
        if self.phases is None:
            self.phases = []

class MathFourierTransform:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._results: list[FourierResult] = []
        self._persist_path = self.root / "math_fourier.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
                self._results = [FourierResult(**r) for r in data.get("results", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "results": [r.__dict__ for r in self._results]
        }, indent=2))

    def dft(self, data: list[float]) -> FourierResult:
        N = len(data)
        result = FourierResult(transform_id=f"dft_{len(self._results)}")
        for k in range(N):
            sum_real = 0.0
            sum_imag = 0.0
            for n in range(N):
                angle = -2 * math.pi * k * n / N
                sum_real += data[n] * math.cos(angle)
                sum_imag += data[n] * math.sin(angle)
            magnitude = math.sqrt(sum_real ** 2 + sum_imag ** 2)
            phase = math.atan2(sum_imag, sum_real)
            result.frequencies.append(k)
            result.magnitudes.append(round(magnitude, 6))
            result.phases.append(round(phase, 6))
        self._results.append(result)
        self._save()
        return result

    def fft(self, data: list[float]) -> FourierResult:
        # Cooley-Tukey FFT (simplified for power-of-2)
        N = len(data)
        if N <= 1:
            return FourierResult(transform_id=f"fft_{len(self._results)}", frequencies=[0], magnitudes=[data[0]] if data else [0])
        if N % 2 != 0:
            return self.dft(data)
        even = self.fft(data[0::2])
        odd = self.fft(data[1::2])
        result = FourierResult(transform_id=f"fft_{len(self._results)}")
        for k in range(N // 2):
            angle = -2 * math.pi * k / N
            twiddle_real = math.cos(angle)
            twiddle_imag = math.sin(angle)
            t_real = twiddle_real * even.magnitudes[k] - twiddle_imag * even.phases[k]
            t_imag = twiddle_real * even.phases[k] + twiddle_imag * even.magnitudes[k]
            result.frequencies.append(k)
            result.magnitudes.append(round(even.magnitudes[k] + t_real, 6))
            result.phases.append(round(even.phases[k] + t_imag, 6))
        for k in range(N // 2):
            result.frequencies.append(k + N // 2)
            result.magnitudes.append(round(even.magnitudes[k] - t_real, 6))
            result.phases.append(round(even.phases[k] - t_imag, 6))
        self._results.append(result)
        self._save()
        return result

    def to_dict(self) -> dict:
        return {"result_count": len(self._results)}

    def get_stats(self) -> dict:
        return {"transforms": len(self._results)}

__all__ = ["MathFourierTransform", "FourierResult"]
