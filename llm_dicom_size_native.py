"""Native stdlib module: DICOM Size Calculator
Calculates DICOM file sizes, transfer times, and storage requirements.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class Modality(Enum):
    CT = "ct"
    MRI = "mri"
    XRAY = "xray"
    ULTRASOUND = "ultrasound"
    PET = "pet"
    MAMMOGRAPHY = "mammography"

@dataclass
class DICOMSizeCalculator:
    modality: Modality
    matrix_x: int
    matrix_y: int
    bits_allocated: int
    num_slices: int
    num_frames: int = 1

    def bytes_per_pixel(self) -> int:
        return self.bits_allocated // 8

    def image_size_bytes(self) -> int:
        return self.matrix_x * self.matrix_y * self.bytes_per_pixel() * self.num_frames

    def total_study_size_mb(self) -> float:
        dicom_overhead = 1.1
        return (self.image_size_bytes() * self.num_slices * dicom_overhead) / (1024 * 1024)

    def transfer_time_sec(self, bandwidth_mbps: float) -> float:
        if bandwidth_mbps == 0:
            return 0.0
        return (self.total_study_size_mb() * 8) / bandwidth_mbps

    def compression_ratio(self, compressed_size_mb: float) -> float:
        if compressed_size_mb == 0:
            return 0.0
        return self.total_study_size_mb() / compressed_size_mb

    def storage_cost_per_month(self, cost_per_gb_month: float) -> float:
        if cost_per_gb_month == 0:
            return 0.0
        return (self.total_study_size_mb() / 1024) * cost_per_gb_month

    def stats(self, bandwidth_mbps: float = 100) -> Dict:
        return {
            "modality": self.modality.value,
            "matrix": f"{self.matrix_x}x{self.matrix_y}",
            "bits": self.bits_allocated,
            "slices": self.num_slices,
            "image_size_kb": round(self.image_size_bytes() / 1024, 1),
            "total_study_size_mb": round(self.total_study_size_mb(), 2),
            "transfer_time_sec": round(self.transfer_time_sec(bandwidth_mbps), 2),
        }

def run():
    dsc = DICOMSizeCalculator(modality=Modality.CT, matrix_x=512, matrix_y=512, bits_allocated=16, num_slices=200)
    print(dsc.stats())

if __name__ == "__main__":
    run()
