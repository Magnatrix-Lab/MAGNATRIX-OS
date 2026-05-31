#!/usr/bin/env python3
"""
protocol/mimo_channel_native.py — MAGNATRIX-OS MIMO Channel Simulator

AMATI from CCMimoLink (SimonLeen22) + cMIMO (lasseufpa) + 5G MIMO patterns.
Pure Python, stdlib only. Zero dependencies.

MIMO (Multiple-Input Multiple-Output) wireless communication channel simulation
for P2P mesh network optimization and signal processing.
"""
from __future__ import annotations

import csv
import math
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ChannelType(Enum):
    RAYLEIGH = "rayleigh"
    RICIAN = "rician"
    AWGN = "awgn"


@dataclass
class MIMOConfig:
    num_rx: int = 4
    num_tx: int = 4
    snr_db: float = 20.0
    channel_type: ChannelType = ChannelType.RAYLEIGH
    rician_k_factor: float = 3.0
    carrier_freq_hz: float = 2.6e9
    bandwidth_hz: float = 20e6
    num_symbols: int = 1000
    modulation: str = "QPSK"


@dataclass
class MIMOMetrics:
    ser: float = 0.0
    ber: float = 0.0
    snr_db: float = 0.0
    evm_db: float = 0.0
    capacity_bps_hz: float = 0.0
    condition_number: float = 0.0
    eigenvalues: List[float] = field(default_factory=list)


@dataclass
class SimulationResult:
    config: MIMOConfig = field(default_factory=MIMOConfig)
    metrics: MIMOMetrics = field(default_factory=MIMOMetrics)
    channel_matrix: List[List[complex]] = field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: float = 0.0


class NoiseGenerator:
    @staticmethod
    def generate(num_samples: int, noise_power_db: float) -> List[complex]:
        noise_power = 10 ** (noise_power_db / 10.0)
        noise_std = math.sqrt(noise_power / 2)
        return [complex(random.gauss(0, noise_std), random.gauss(0, noise_std)) for _ in range(num_samples)]

    @staticmethod
    def snr_to_noise_power(snr_db: float, signal_power: float = 1.0) -> float:
        return signal_power / (10 ** (snr_db / 10.0))


class MIMOChannel:
    @staticmethod
    def generate_rayleigh(num_rx: int, num_tx: int) -> List[List[complex]]:
        return [[complex(random.gauss(0, 1/math.sqrt(2)), random.gauss(0, 1/math.sqrt(2))) for _ in range(num_tx)] for _ in range(num_rx)]

    @staticmethod
    def generate_rician(num_rx: int, num_tx: int, k_factor_db: float) -> List[List[complex]]:
        k_factor = 10 ** (k_factor_db / 10.0)
        k_sqrt = math.sqrt(k_factor / (k_factor + 1))
        scatter_sqrt = 1 / math.sqrt(k_factor + 1)
        los = [[k_sqrt for _ in range(num_tx)] for _ in range(num_rx)]
        scatter = [[scatter_sqrt * complex(random.gauss(0, 1/math.sqrt(2)), random.gauss(0, 1/math.sqrt(2))) for _ in range(num_tx)] for _ in range(num_rx)]
        return [[los[i][j] + scatter[i][j] for j in range(num_tx)] for i in range(num_rx)]

    @staticmethod
    def generate(config: MIMOConfig) -> List[List[complex]]:
        if config.channel_type == ChannelType.RAYLEIGH:
            return MIMOChannel.generate_rayleigh(config.num_rx, config.num_tx)
        elif config.channel_type == ChannelType.RICIAN:
            return MIMOChannel.generate_rician(config.num_rx, config.num_tx, config.rician_k_factor)
        else:
            return [[1.0 + 0j for _ in range(config.num_tx)] for _ in range(config.num_rx)]

    @staticmethod
    def apply_noise(channel_matrix: List[List[complex]], snr_db: float) -> List[List[complex]]:
        num_rx = len(channel_matrix)
        num_tx = len(channel_matrix[0])
        noise_power = NoiseGenerator.snr_to_noise_power(snr_db)
        noise_std = math.sqrt(noise_power / 2)
        return [[channel_matrix[i][j] + complex(random.gauss(0, noise_std), random.gauss(0, noise_std)) for j in range(num_tx)] for i in range(num_rx)]


class ChannelCovarianceMatrix:
    @staticmethod
    def compute(channel_matrix: List[List[complex]]) -> List[List[complex]]:
        num_rx = len(channel_matrix)
        num_tx = len(channel_matrix[0])
        ccm = [[0j for _ in range(num_tx)] for _ in range(num_tx)]
        for j in range(num_tx):
            for k in range(num_tx):
                for i in range(num_rx):
                    ccm[j][k] += channel_matrix[i][j].conjugate() * channel_matrix[i][k]
        for j in range(num_tx):
            for k in range(num_tx):
                ccm[j][k] /= num_rx
        return ccm


class SVDecomposer:
    @staticmethod
    def power_iteration(matrix: List[List[complex]], num_iterations: int = 50) -> Tuple[float, List[complex]]:
        n = len(matrix[0])
        v = [complex(random.random(), random.random()) for _ in range(n)]
        norm = math.sqrt(sum(abs(x)**2 for x in v))
        v = [x / norm for x in v]

        for _ in range(num_iterations):
            Av = [0j for _ in range(n)]
            for j in range(n):
                for i in range(len(matrix)):
                    for k in range(n):
                        Av[j] += matrix[i][j].conjugate() * matrix[i][k] * v[k]
            norm = math.sqrt(sum(abs(x)**2 for x in Av))
            if norm > 0:
                v = [x / norm for x in Av]

        Av = [0j for _ in range(n)]
        for j in range(n):
            for i in range(len(matrix)):
                for k in range(n):
                    Av[j] += matrix[i][j].conjugate() * matrix[i][k] * v[k]
        sigma = math.sqrt(sum(abs(v[j] * Av[j]) for j in range(n)))
        return sigma, v


class CapacityCalculator:
    @staticmethod
    def calculate_capacity(singular_values: List[float], snr_db: float, num_tx: int) -> float:
        snr_linear = 10 ** (snr_db / 10.0)
        capacity = 0.0
        for sigma in singular_values:
            lambda_i = sigma ** 2
            capacity += math.log2(1 + (snr_linear / num_tx) * lambda_i)
        return capacity

    @staticmethod
    def calculate_capacity_siso(snr_db: float) -> float:
        snr_linear = 10 ** (snr_db / 10.0)
        return math.log2(1 + snr_linear)


class Modulator:
    @staticmethod
    def qpsk_modulate(bits: List[int]) -> List[complex]:
        symbols = []
        for i in range(0, len(bits) - 1, 2):
            b1, b2 = bits[i], bits[i + 1]
            if b1 == 0 and b2 == 0:
                symbols.append(1 + 1j)
            elif b1 == 0 and b2 == 1:
                symbols.append(-1 + 1j)
            elif b1 == 1 and b2 == 0:
                symbols.append(1 - 1j)
            else:
                symbols.append(-1 - 1j)
        return symbols

    @staticmethod
    def qpsk_demodulate(symbols: List[complex]) -> List[int]:
        bits = []
        for s in symbols:
            b2 = 0 if s.real > 0 else 1
            b1 = 0 if s.imag > 0 else 1
            bits.extend([b1, b2])
        return bits


class MetricsAnalyzer:
    @staticmethod
    def calculate_ser(tx_symbols: List[complex], rx_symbols: List[complex]) -> float:
        errors = sum(1 for tx, rx in zip(tx_symbols, rx_symbols) if abs(tx - rx) > 0.5)
        return errors / len(tx_symbols) if tx_symbols else 0.0

    @staticmethod
    def calculate_ber(tx_bits: List[int], rx_bits: List[int]) -> float:
        errors = sum(1 for tx, rx in zip(tx_bits, rx_bits) if tx != rx)
        return errors / len(tx_bits) if tx_bits else 0.0

    @staticmethod
    def calculate_evm(tx_symbols: List[complex], rx_symbols: List[complex]) -> float:
        error_power = sum(abs(tx - rx) ** 2 for tx, rx in zip(tx_symbols, rx_symbols))
        signal_power = sum(abs(tx) ** 2 for tx in tx_symbols)
        if signal_power == 0:
            return -999.0
        return 10 * math.log10(error_power / signal_power)

    @staticmethod
    def condition_number(singular_values: List[float]) -> float:
        if not singular_values or singular_values[-1] == 0:
            return float("inf")
        return singular_values[0] / singular_values[-1]


class MIMOSimulator:
    def __init__(self, config: Optional[MIMOConfig] = None):
        self.config = config or MIMOConfig()
        self.results: List[SimulationResult] = []
        self._lock = threading.Lock()

    def run_single(self) -> SimulationResult:
        start = time.time()
        config = self.config
        H = MIMOChannel.generate(config)
        H_noisy = MIMOChannel.apply_noise(H, config.snr_db)
        sigma, v = SVDecomposer.power_iteration(H)
        capacity = CapacityCalculator.calculate_capacity([sigma], config.snr_db, config.num_tx)
        num_bits = config.num_symbols * 2
        tx_bits = [random.randint(0, 1) for _ in range(num_bits)]
        tx_symbols = Modulator.qpsk_modulate(tx_bits)
        rx_symbols = []
        for i in range(config.num_rx):
            y = sum(H_noisy[i][j] * tx_symbols[j % len(tx_symbols)] for j in range(config.num_tx))
            rx_symbols.append(y)
        rx_bits = Modulator.qpsk_demodulate(rx_symbols[:len(tx_symbols)])
        metrics = MIMOMetrics()
        metrics.ser = MetricsAnalyzer.calculate_ser(tx_symbols[:len(rx_symbols)], rx_symbols[:len(tx_symbols)])
        metrics.ber = MetricsAnalyzer.calculate_ber(tx_bits[:len(rx_bits)], rx_bits[:len(tx_bits)])
        metrics.evm_db = MetricsAnalyzer.calculate_evm(tx_symbols[:len(rx_symbols)], rx_symbols[:len(tx_symbols)])
        metrics.capacity_bps_hz = capacity
        metrics.snr_db = config.snr_db
        metrics.condition_number = MetricsAnalyzer.condition_number([sigma])
        metrics.eigenvalues = [sigma**2]
        result = SimulationResult(
            config=config, metrics=metrics, channel_matrix=H,
            duration_ms=(time.time() - start) * 1000, timestamp=time.time())
        with self._lock:
            self.results.append(result)
        return result

    def run_batch(self, num_runs: int = 10) -> List[SimulationResult]:
        return [self.run_single() for _ in range(num_runs)]

    def export_csv(self, path: str) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["run", "num_rx", "num_tx", "snr_db", "channel_type", "ser", "ber", "capacity_bps_hz", "evm_db", "condition_number", "duration_ms"])
            for i, result in enumerate(self.results):
                writer.writerow([i + 1, result.config.num_rx, result.config.num_tx, result.config.snr_db, result.config.channel_type.value, result.metrics.ser, result.metrics.ber, result.metrics.capacity_bps_hz, result.metrics.evm_db, result.metrics.condition_number, result.duration_ms])

    def get_summary(self) -> Dict[str, Any]:
        if not self.results:
            return {}
        capacities = [r.metrics.capacity_bps_hz for r in self.results]
        sers = [r.metrics.ser for r in self.results]
        bers = [r.metrics.ber for r in self.results]
        return {"num_runs": len(self.results), "avg_capacity": sum(capacities) / len(capacities), "avg_ser": sum(sers) / len(sers), "avg_ber": sum(bers) / len(bers), "max_capacity": max(capacities), "min_capacity": min(capacities)}


if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS MIMO Channel Simulator — Self-Test")
    print("=" * 60)
    config = MIMOConfig(num_rx=4, num_tx=4, snr_db=20, channel_type=ChannelType.RAYLEIGH)
    H = MIMOChannel.generate(config)
    assert len(H) == 4 and len(H[0]) == 4
    print("[1] Channel generated: {}x{}".format(len(H), len(H[0])))
    ccm = ChannelCovarianceMatrix.compute(H)
    print("[2] CCM computed: {}x{}".format(len(ccm), len(ccm[0])))
    sigma, v = SVDecomposer.power_iteration(H)
    print("[3] Power iteration: sigma={:.3f}".format(sigma))
    capacity = CapacityCalculator.calculate_capacity([sigma], 20, 4)
    print("[4] Capacity: {:.2f} bps/Hz".format(capacity))
    bits = [0, 0, 0, 1, 1, 0, 1, 1]
    symbols = Modulator.qpsk_modulate(bits)
    demod = Modulator.qpsk_demodulate(symbols)
    assert demod == bits
    print("[5] QPSK mod/demod OK")
    sim = MIMOSimulator(config)
    result = sim.run_single()
    print("[6] SER={:.4f}, BER={:.4f}, Capacity={:.2f}".format(result.metrics.ser, result.metrics.ber, result.metrics.capacity_bps_hz))
    sim.export_csv("/tmp/mimo_results.csv")
    print("[7] CSV exported")
    print("All tests passed")
