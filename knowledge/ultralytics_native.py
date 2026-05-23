#!/usr/bin/env python3
"""
ultralytics_native.py — Native reimplementation of ultralytics/ultralytics (YOLOv8).
Computer vision framework: detection, segmentation, classification, pose,
tracking, auto-annotation. Pure Python simulation, no PyTorch dependency.
"""

from __future__ import annotations

import json
import math
import random
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Core Data Structures & Image Preprocessing
# ═══════════════════════════════════════════════════════════════════════════════


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


@dataclass
class ImageTensor:
    """Simulated image tensor stored as nested lists [H][W][C]."""
    data: List[List[List[float]]]  # height x width x channels
    height: int
    width: int
    channels: int
    filename: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"<ImageTensor {self.height}x{self.width}x{self.channels} {self.filename}>"

    def pixel(self, y: int, x: int, c: int) -> float:
        if 0 <= y < self.height and 0 <= x < self.width and 0 <= c < self.channels:
            return self.data[y][x][c]
        return 0.0


@dataclass
class BBox:
    """Bounding box with normalized or pixel coordinates."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float = 0.0
    class_id: int = 0
    label: str = ""
    area: float = 0.0

    def __post_init__(self) -> None:
        self.area = max(0.0, (self.x2 - self.x1) * (self.y2 - self.y1))

    def __repr__(self) -> str:
        return f"<BBox {self.label} conf={self.confidence:.3f} [{self.x1:.2f},{self.y1:.2f},{self.x2:.2f},{self.y2:.2f}]>"

    def iou(self, other: BBox) -> float:
        """Intersection over Union with another box."""
        xi1 = max(self.x1, other.x1)
        yi1 = max(self.y1, other.y1)
        xi2 = min(self.x2, other.x2)
        yi2 = min(self.y2, other.y2)
        inter_w = max(0.0, xi2 - xi1)
        inter_h = max(0.0, yi2 - yi1)
        inter_area = inter_w * inter_h
        union = self.area + other.area - inter_area
        return inter_area / union if union > 0 else 0.0

    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)


@dataclass
class SegmentationMask:
    """Instance segmentation mask as polygon or grid."""
    points: List[Tuple[float, float]] = field(default_factory=list)
    grid: Optional[List[List[int]]] = None  # binary mask grid
    class_id: int = 0
    label: str = ""
    area: float = 0.0

    def __repr__(self) -> str:
        return f"<SegmentationMask {self.label} points={len(self.points)}>"


@dataclass
class Keypoint:
    """A single keypoint / joint."""
    x: float
    y: float
    visibility: float = 2.0  # 0=not labeled, 1=labeled but invisible, 2=visible
    joint_name: str = ""
    confidence: float = 0.0

    def __repr__(self) -> str:
        return f"<Keypoint {self.joint_name} ({self.x:.1f},{self.y:.1f}) v={self.visibility}>"


@dataclass
class DetectionResult:
    """Output from detection/segmentation/pose inference."""
    image_id: str = ""
    boxes: List[BBox] = field(default_factory=list)
    masks: List[SegmentationMask] = field(default_factory=list)
    keypoints: List[Keypoint] = field(default_factory=list)
    class_probs: List[float] = field(default_factory=list)
    inference_time_ms: float = 0.0
    model_id: str = ""

    def __repr__(self) -> str:
        return f"<DetectionResult boxes={len(self.boxes)} masks={len(self.masks)} kp={len(self.keypoints)}>"


class ImagePreprocessor:
    """Preprocess images for model input: resize, normalize, letterbox."""

    def __init__(self, input_size: Tuple[int, int] = (640, 640),
                 mean: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                 std: Tuple[float, float, float] = (255.0, 255.0, 255.0)) -> None:
        self.input_size = input_size
        self.mean = mean
        self.std = std

    def __repr__(self) -> str:
        return f"<ImagePreprocessor size={self.input_size}>"

    def resize(self, tensor: ImageTensor) -> ImageTensor:
        """Simulated resize to target size."""
        return ImageTensor(
            data=[[[0.0] * tensor.channels for _ in range(self.input_size[1])]
                  for _ in range(self.input_size[0])],
            height=self.input_size[0], width=self.input_size[1],
            channels=tensor.channels, filename=tensor.filename
        )

    def normalize(self, tensor: ImageTensor) -> ImageTensor:
        """Normalize pixel values."""
        h, w, c = tensor.height, tensor.width, tensor.channels
        new_data: List[List[List[float]]] = []
        for y in range(h):
            row: List[List[float]] = []
            for x in range(w):
                pixel = []
                for ch in range(c):
                    v = tensor.data[y][x][ch]
                    pixel.append((v - self.mean[ch]) / self.std[ch])
                row.append(pixel)
            new_data.append(row)
        return ImageTensor(data=new_data, height=h, width=w, channels=c, filename=tensor.filename)

    def letterbox(self, tensor: ImageTensor) -> ImageTensor:
        """Pad with gray to maintain aspect ratio."""
        target_h, target_w = self.input_size
        scale = min(target_h / tensor.height, target_w / tensor.width)
        new_h, new_w = int(tensor.height * scale), int(tensor.width * scale)
        pad_h = (target_h - new_h) // 2
        pad_w = (target_w - new_w) // 2
        # Simulate padded output
        return ImageTensor(
            data=[[[114.0 / 255.0] * tensor.channels for _ in range(target_w)]
                  for _ in range(target_h)],
            height=target_h, width=target_w, channels=tensor.channels,
            filename=tensor.filename
        )

    def preprocess(self, tensor: ImageTensor) -> ImageTensor:
        """Full preprocess pipeline."""
        resized = self.resize(tensor)
        normalized = self.normalize(resized)
        return self.letterbox(normalized)


class Dataset:
    """YOLO-format dataset loader."""

    def __init__(self, image_dir: str = "", label_dir: str = "",
                 class_names: Optional[List[str]] = None) -> None:
        self.image_dir = image_dir
        self.label_dir = label_dir
        self.class_names = class_names or []
        self.samples: List[Dict[str, Any]] = []

    def __repr__(self) -> str:
        return f"<Dataset samples={len(self.samples)} classes={len(self.class_names)}>"

    def add_sample(self, image_path: str, labels: List[Dict[str, Any]]) -> None:
        """labels: list of {class_id, cx, cy, w, h} normalized YOLO format."""
        self.samples.append({"image": image_path, "labels": labels})

    def load_from_yolo_file(self, label_file_content: str, image_path: str) -> None:
        labels: List[Dict[str, Any]] = []
        for line in label_file_content.strip().splitlines():
            parts = line.strip().split()
            if len(parts) >= 5:
                labels.append({
                    "class_id": int(parts[0]),
                    "cx": float(parts[1]),
                    "cy": float(parts[2]),
                    "w": float(parts[3]),
                    "h": float(parts[4])
                })
        self.add_sample(image_path, labels)

    def __len__(self) -> int:
        return len(self.samples)

    def get_batch(self, indices: List[int]) -> List[Dict[str, Any]]:
        return [self.samples[i] for i in indices]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Model Architecture Simulation
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ModelConfig:
    """YOLOv8 model configuration."""
    model_type: str = "yolov8n"  # n, s, m, l, x
    input_size: Tuple[int, int] = (640, 640)
    num_classes: int = 80
    depth_multiple: float = 0.33
    width_multiple: float = 0.25
    max_det: int = 300
    conf_threshold: float = 0.25
    iou_threshold: float = 0.45
    reg_max: int = 16  # DFL bins

    def __repr__(self) -> str:
        return f"<ModelConfig {self.model_type} classes={self.num_classes}>"


class ModuleStub(ABC):
    """Abstract base for simulated neural network modules."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._output_shape: Tuple[int, ...] = ()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.name}>"

    @abstractmethod
    def forward(self, x: Any) -> Any:
        raise NotImplementedError


class ConvBlock(ModuleStub):
    """Simulated Conv + BN + SiLU block."""

    def __init__(self, in_ch: int, out_ch: int, kernel: int = 3, stride: int = 1,
                 padding: Optional[int] = None) -> None:
        super().__init__(f"conv_{out_ch}")
        self.in_ch = in_ch
        self.out_ch = out_ch
        self.kernel = kernel
        self.stride = stride
        self.padding = padding or kernel // 2

    def forward(self, x: ImageTensor) -> ImageTensor:
        h = max(1, x.height // self.stride)
        w = max(1, x.width // self.stride)
        return ImageTensor(
            data=[[[0.0] * self.out_ch for _ in range(w)] for _ in range(h)],
            height=h, width=w, channels=self.out_ch, filename=x.filename
        )


class C2fBlock(ModuleStub):
    """Simulated C2f (Cross Stage Partial) block."""

    def __init__(self, in_ch: int, out_ch: int, num_bottlenecks: int = 1,
                 shortcut: bool = True) -> None:
        super().__init__(f"c2f_{out_ch}")
        self.in_ch = in_ch
        self.out_ch = out_ch
        self.num_bottlenecks = num_bottlenecks
        self.shortcut = shortcut

    def forward(self, x: ImageTensor) -> ImageTensor:
        return ImageTensor(
            data=[[[0.0] * self.out_ch for _ in range(x.width)] for _ in range(x.height)],
            height=x.height, width=x.width, channels=self.out_ch, filename=x.filename
        )


class SPPFBlock(ModuleStub):
    """Simulated Spatial Pyramid Pooling Fast."""

    def __init__(self, in_ch: int, out_ch: int, kernel_sizes: List[int] = None) -> None:
        super().__init__("sppf")
        self.in_ch = in_ch
        self.out_ch = out_ch
        self.kernel_sizes = kernel_sizes or [5, 5, 5]

    def forward(self, x: ImageTensor) -> ImageTensor:
        return ImageTensor(
            data=[[[0.0] * self.out_ch for _ in range(x.width)] for _ in range(x.height)],
            height=x.height, width=x.width, channels=self.out_ch, filename=x.filename
        )


class DetectionHead(ModuleStub):
    """Anchor-free detection head: class scores + bbox regression."""

    def __init__(self, num_classes: int, reg_max: int = 16, strides: List[int] = None) -> None:
        super().__init__("detect")
        self.num_classes = num_classes
        self.reg_max = reg_max
        self.strides = strides or [8, 16, 32]
        self.nc = num_classes
        self.no = num_classes + 4 * reg_max  # outputs per anchor

    def forward(self, features: List[ImageTensor]) -> List[List[float]]:
        """Returns flattened predictions: [batch*anchors, no]."""
        total_anchors = sum(f.height * f.width for f in features)
        return [[random.random() for _ in range(self.no)] for _ in range(total_anchors)]

    def decode_boxes(self, preds: List[List[float]], anchors: List[Tuple[int, int, int]]) -> List[BBox]:
        """Decode predictions to bounding boxes (anchor-free DFL)."""
        boxes: List[BBox] = []
        for i, pred in enumerate(preds):
            if i >= len(anchors):
                break
            cls_scores = pred[:self.nc]
            best_cls = max(range(self.nc), key=lambda j: cls_scores[j])
            conf = cls_scores[best_cls]
            if conf < 0.25:
                continue
            # Simulate DFL decode: take 4 bbox params from DFL bins
            bx, by, bw, bh = pred[self.nc:self.nc + 4]
            stride = anchors[i][2]
            grid_x, grid_y = anchors[i][0], anchors[i][1]
            cx = (grid_x + 0.5 + bx) * stride
            cy = (grid_y + 0.5 + by) * stride
            w = abs(bw) * stride * 2
            h = abs(bh) * stride * 2
            boxes.append(BBox(
                x1=cx - w / 2, y1=cy - h / 2,
                x2=cx + w / 2, y2=cy + h / 2,
                confidence=conf, class_id=best_cls,
                label=f"class_{best_cls}"
            ))
        return boxes

    def generate_anchors(self, feature_sizes: List[Tuple[int, int]]) -> List[Tuple[int, int, int]]:
        """Generate anchor grid points (x, y, stride)."""
        anchors: List[Tuple[int, int, int]] = []
        for (h, w), stride in zip(feature_sizes, self.strides):
            for y in range(h):
                for x in range(w):
                    anchors.append((x, y, stride))
        return anchors


class SegmentationHead(ModuleStub):
    """Segmentation head: mask prototypes + coefficients."""

    def __init__(self, num_classes: int, mask_channels: int = 32) -> None:
        super().__init__("segment")
        self.num_classes = num_classes
        self.mask_channels = mask_channels

    def forward(self, x: ImageTensor) -> ImageTensor:
        return ImageTensor(
            data=[[[0.0] * self.mask_channels for _ in range(x.width)] for _ in range(x.height)],
            height=x.height, width=x.width, channels=self.mask_channels, filename=x.filename
        )


class PoseHead(ModuleStub):
    """Pose estimation head: keypoint regression."""

    def __init__(self, num_keypoints: int = 17, num_dims: int = 3) -> None:
        super().__init__("pose")
        self.num_keypoints = num_keypoints
        self.num_dims = num_dims  # x, y, visibility

    def forward(self, x: ImageTensor) -> List[List[float]]:
        return [[random.random() for _ in range(self.num_keypoints * self.num_dims)]
                for _ in range(x.height * x.width)]


class ClassificationHead(ModuleStub):
    """Classification head: global pool + FC."""

    def __init__(self, num_classes: int) -> None:
        super().__init__("classify")
        self.num_classes = num_classes

    def forward(self, x: ImageTensor) -> List[float]:
        return [random.random() for _ in range(self.num_classes)]


class YOLOModel:
    """Assembled YOLOv8 model with backbone + neck + task-specific head."""

    def __init__(self, config: ModelConfig, task: str = "detect") -> None:
        self.config = config
        self.task = task  # detect, segment, classify, pose
        self.backbone: List[ModuleStub] = []
        self.neck: List[ModuleStub] = []
        self.head: Optional[ModuleStub] = None
        self._build()

    def __repr__(self) -> str:
        layers = len(self.backbone) + len(self.neck)
        return f"<YOLOModel {self.config.model_type} task={self.task} layers={layers}>"

    def _build(self) -> None:
        w = self.config.width_multiple
        d = self.config.depth_multiple
        # Backbone
        self.backbone = [
            ConvBlock(3, int(64 * w), 3, 2),
            ConvBlock(int(64 * w), int(128 * w), 3, 2),
            C2fBlock(int(128 * w), int(128 * w), max(1, round(3 * d))),
            ConvBlock(int(128 * w), int(256 * w), 3, 2),
            C2fBlock(int(256 * w), int(256 * w), max(1, round(6 * d))),
            ConvBlock(int(256 * w), int(512 * w), 3, 2),
            C2fBlock(int(512 * w), int(512 * w), max(1, round(6 * d))),
            ConvBlock(int(512 * w), int(512 * w), 3, 2),
            C2fBlock(int(512 * w), int(512 * w), max(1, round(3 * d))),
            SPPFBlock(int(512 * w), int(512 * w)),
        ]
        # Neck (FPN + PAN stub)
        self.neck = [
            C2fBlock(int(512 * w), int(256 * w)),
            C2fBlock(int(256 * w), int(128 * w)),
        ]
        # Head
        if self.task == "detect":
            self.head = DetectionHead(self.config.num_classes, self.config.reg_max)
        elif self.task == "segment":
            self.head = SegmentationHead(self.config.num_classes)
        elif self.task == "pose":
            self.head = PoseHead()
        elif self.task == "classify":
            self.head = ClassificationHead(self.config.num_classes)

    def forward(self, x: ImageTensor) -> Any:
        current = x
        for m in self.backbone:
            current = m.forward(current)
        for m in self.neck:
            current = m.forward(current)
        if self.head:
            return self.head.forward(current)
        return current


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Loss Functions
# ═══════════════════════════════════════════════════════════════════════════════


class CIoULoss:
    """Complete IoU loss: IoU + aspect ratio + distance + area."""

    def __init__(self, eps: float = 1e-7) -> None:
        self.eps = eps

    def __repr__(self) -> str:
        return f"<CIoULoss eps={self.eps}>"

    def compute(self, pred: BBox, target: BBox) -> float:
        """Compute CIoU between predicted and target box."""
        iou = pred.iou(target)
        # Distance penalty
        pred_cx, pred_cy = pred.center()
        tgt_cx, tgt_cy = target.center()
        c_x1 = min(pred.x1, target.x1)
        c_y1 = min(pred.y1, target.y1)
        c_x2 = max(pred.x2, target.x2)
        c_y2 = max(pred.y2, target.y2)
        c_w = c_x2 - c_x1 + self.eps
        c_h = c_y2 - c_y1 + self.eps
        d_center = ((pred_cx - tgt_cx) ** 2 + (pred_cy - tgt_cy) ** 2)
        d_diag = c_w ** 2 + c_h ** 2
        distance_term = d_center / d_diag if d_diag > 0 else 0.0
        # Aspect ratio penalty
        pred_w = pred.x2 - pred.x1 + self.eps
        pred_h = pred.y2 - pred.y1 + self.eps
        tgt_w = target.x2 - target.x1 + self.eps
        tgt_h = target.y2 - target.y1 + self.eps
        v = (4.0 / (math.pi ** 2)) * (math.atan(tgt_w / tgt_h) - math.atan(pred_w / pred_h)) ** 2
        alpha = v / ((1 - iou) + v + self.eps) if (1 - iou + v) > 0 else 0.0
        aspect_term = alpha * v
        return 1.0 - iou + distance_term + aspect_term


class DFLLoss:
    """Distribution Focal Loss for anchor-free bbox regression."""

    def __init__(self, reg_max: int = 16) -> None:
        self.reg_max = reg_max

    def __repr__(self) -> str:
        return f"<DFLLoss reg_max={self.reg_max}>"

    def compute(self, pred_distribution: List[float], target_bin: int) -> float:
        """Simplified DFL: cross-entropy over discrete bins."""
        if not pred_distribution or len(pred_distribution) != self.reg_max:
            return 0.0
        # Softmax
        max_v = max(pred_distribution)
        exps = [math.exp(p - max_v) for p in pred_distribution]
        sum_exps = sum(exps)
        probs = [e / sum_exps for e in exps]
        # Cross entropy
        ce = -math.log(probs[target_bin] + 1e-7) if 0 <= target_bin < len(probs) else 0.0
        return ce


class FocalLoss:
    """Focal loss for classification."""

    def __init__(self, alpha: float = 1.0, gamma: float = 2.0) -> None:
        self.alpha = alpha
        self.gamma = gamma

    def __repr__(self) -> str:
        return f"<FocalLoss alpha={self.alpha} gamma={self.gamma}>"

    def compute(self, pred_prob: float, target: int) -> float:
        """Binary focal loss for a single class probability."""
        p = _clamp(pred_prob, 1e-7, 1 - 1e-7)
        if target == 1:
            return -self.alpha * ((1 - p) ** self.gamma) * math.log(p)
        else:
            return -self.alpha * (p ** self.gamma) * math.log(1 - p)


class SegmentationLoss:
    """Segmentation loss: BCE + Dice combination stub."""

    def __init__(self, bce_weight: float = 0.5, dice_weight: float = 0.5) -> None:
        self.bce_weight = bce_weight
        self.dice_weight = dice_weight

    def __repr__(self) -> str:
        return f"<SegmentationLoss bce={self.bce_weight} dice={self.dice_weight}>"

    def compute(self, pred_mask: List[List[float]], target_mask: List[List[int]]) -> float:
        # Simplified: pixel-wise BCE approximation
        loss = 0.0
        count = 0
        for i in range(min(len(pred_mask), len(target_mask))):
            for j in range(min(len(pred_mask[i]), len(target_mask[i]))):
                p = _clamp(pred_mask[i][j], 1e-7, 1 - 1e-7)
                t = float(target_mask[i][j])
                loss += -(t * math.log(p) + (1 - t) * math.log(1 - p))
                count += 1
        return loss / count if count > 0 else 0.0


class PoseLoss:
    """Keypoint loss: OKS-based stub."""

    def __init__(self, sigmas: Optional[List[float]] = None) -> None:
        self.sigmas = sigmas or [0.026] * 17  # default COCO sigmas

    def __repr__(self) -> str:
        return f"<PoseLoss keypoints={len(self.sigmas)}>"

    def compute(self, pred_kpts: List[Keypoint], target_kpts: List[Keypoint]) -> float:
        loss = 0.0
        count = 0
        for pk, tk in zip(pred_kpts, target_kpts):
            if tk.visibility > 0:
                dx = pk.x - tk.x
                dy = pk.y - tk.y
                loss += (dx * dx + dy * dy) * pk.confidence
                count += 1
        return loss / count if count > 0 else 0.0


class LossAggregator:
    """Combine multiple losses with weights."""

    def __init__(self) -> None:
        self._losses: Dict[str, Tuple[Callable[..., float], float]] = {}

    def __repr__(self) -> str:
        return f"<LossAggregator losses={len(self._losses)}>"

    def add(self, name: str, loss_fn: Callable[..., float], weight: float = 1.0) -> None:
        self._losses[name] = (loss_fn, weight)

    def compute(self, **kwargs: Any) -> Dict[str, float]:
        results: Dict[str, float] = {}
        total = 0.0
        for name, (fn, weight) in self._losses.items():
            v = fn(**kwargs.get(name, {}))
            results[name] = v
            total += v * weight
        results["total"] = total
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Training Pipeline
# ═══════════════════════════════════════════════════════════════════════════════


class OptimizerStub:
    """Simulated SGD / AdamW optimizer."""

    def __init__(self, lr: float = 0.01, momentum: float = 0.937,
                 weight_decay: float = 0.0005, method: str = "sgd") -> None:
        self.lr = lr
        self.momentum = momentum
        self.weight_decay = weight_decay
        self.method = method
        self._step_count = 0
        self._state: Dict[str, Any] = {}

    def __repr__(self) -> str:
        return f"<OptimizerStub {self.method} lr={self.lr}>"

    def step(self) -> None:
        self._step_count += 1

    def zero_grad(self) -> None:
        pass

    def state_dict(self) -> Dict[str, Any]:
        return {"lr": self.lr, "steps": self._step_count}


class LRScheduler:
    """Cosine annealing with linear warm-up."""

    def __init__(self, optimizer: OptimizerStub, max_epochs: int = 100,
                 warmup_epochs: int = 3, min_lr: float = 1e-5) -> None:
        self.optimizer = optimizer
        self.max_epochs = max_epochs
        self.warmup_epochs = warmup_epochs
        self.min_lr = min_lr
        self.initial_lr = optimizer.lr

    def __repr__(self) -> str:
        return f"<LRScheduler cosine max={self.max_epochs} warmup={self.warmup_epochs}>"

    def step(self, epoch: int) -> float:
        if epoch < self.warmup_epochs:
            lr = self.initial_lr * (epoch + 1) / self.warmup_epochs
        else:
            progress = (epoch - self.warmup_epochs) / (self.max_epochs - self.warmup_epochs)
            lr = self.min_lr + (self.initial_lr - self.min_lr) * (1 + math.cos(math.pi * progress)) / 2
        self.optimizer.lr = lr
        return lr


class EMA:
    """Exponential Moving Average for model parameters."""

    def __init__(self, decay: float = 0.9999) -> None:
        self.decay = decay
        self._shadow: Dict[str, float] = {}

    def __repr__(self) -> str:
        return f"<EMA decay={self.decay}>"

    def update(self, model: YOLOModel) -> None:
        """Simulated EMA update."""
        pass

    def apply_shadow(self, model: YOLOModel) -> None:
        pass


class MetricsTracker:
    """Track mAP, precision, recall during training/validation."""

    def __init__(self, num_classes: int = 80) -> None:
        self.num_classes = num_classes
        self._tp: Dict[int, int] = {}
        self._fp: Dict[int, int] = {}
        self._fn: Dict[int, int] = {}
        self._ious: List[float] = []

    def __repr__(self) -> str:
        return f"<MetricsTracker classes={self.num_classes}>"

    def add_prediction(self, pred: BBox, gt: Optional[BBox], iou_threshold: float = 0.5) -> None:
        if gt is None:
            self._fp[pred.class_id] = self._fp.get(pred.class_id, 0) + 1
            return
        iou = pred.iou(gt)
        self._ious.append(iou)
        if iou >= iou_threshold:
            self._tp[pred.class_id] = self._tp.get(pred.class_id, 0) + 1
        else:
            self._fp[pred.class_id] = self._fp.get(pred.class_id, 0) + 1
            self._fn[gt.class_id] = self._fn.get(gt.class_id, 0) + 1

    def precision(self, class_id: int) -> float:
        tp = self._tp.get(class_id, 0)
        fp = self._fp.get(class_id, 0)
        return tp / (tp + fp) if (tp + fp) > 0 else 0.0

    def recall(self, class_id: int) -> float:
        tp = self._tp.get(class_id, 0)
        fn = self._fn.get(class_id, 0)
        return tp / (tp + fn) if (tp + fn) > 0 else 0.0

    def f1(self, class_id: int) -> float:
        p = self.precision(class_id)
        r = self.recall(class_id)
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    def map50(self) -> float:
        precisions = [self.precision(c) for c in range(self.num_classes)]
        return sum(precisions) / len(precisions) if precisions else 0.0

    def map5095(self) -> float:
        return self.map50() * 0.85  # simulated

    def summary(self) -> Dict[str, float]:
        return {
            "mAP@50": self.map50(),
            "mAP@50-95": self.map5095(),
            "mean_precision": sum(self.precision(c) for c in range(self.num_classes)) / self.num_classes,
            "mean_recall": sum(self.recall(c) for c in range(self.num_classes)) / self.num_classes,
        }


class EarlyStopping:
    """Stop training if metric does not improve for N epochs."""

    def __init__(self, patience: int = 10, min_delta: float = 0.0) -> None:
        self.patience = patience
        self.min_delta = min_delta
        self._best = float('-inf')
        self._counter = 0
        self._should_stop = False

    def __repr__(self) -> str:
        return f"<EarlyStopping patience={self.patience}>"

    def check(self, metric: float) -> bool:
        if metric > self._best + self.min_delta:
            self._best = metric
            self._counter = 0
        else:
            self._counter += 1
            if self._counter >= self.patience:
                self._should_stop = True
        return self._should_stop


class Trainer:
    """Training loop orchestrator."""

    def __init__(self, model: YOLOModel, optimizer: OptimizerStub,
                 scheduler: LRScheduler, loss_aggregator: LossAggregator,
                 dataset: Dataset, metrics: MetricsTracker,
                 early_stop: Optional[EarlyStopping] = None,
                 epochs: int = 100, batch_size: int = 16) -> None:
        self.model = model
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.loss_aggregator = loss_aggregator
        self.dataset = dataset
        self.metrics = metrics
        self.early_stop = early_stop
        self.epochs = epochs
        self.batch_size = batch_size
        self.history: List[Dict[str, Any]] = []

    def __repr__(self) -> str:
        return f"<Trainer epochs={self.epochs} batch={self.batch_size}>"

    def train_epoch(self, epoch: int) -> Dict[str, float]:
        """Simulate one training epoch."""
        lr = self.scheduler.step(epoch)
        num_batches = max(1, len(self.dataset) // self.batch_size)
        epoch_loss = 0.0
        for b in range(num_batches):
            self.optimizer.zero_grad()
            # Simulate forward + loss
            dummy_loss = random.uniform(0.5, 3.0)
            epoch_loss += dummy_loss
            self.optimizer.step()
        avg_loss = epoch_loss / num_batches
        self.history.append({"epoch": epoch, "loss": avg_loss, "lr": lr})
        return {"loss": avg_loss, "lr": lr}

    def validate(self) -> Dict[str, float]:
        """Simulate validation."""
        return self.metrics.summary()

    def fit(self) -> List[Dict[str, Any]]:
        for epoch in range(self.epochs):
            train_metrics = self.train_epoch(epoch)
            val_metrics = self.validate()
            if self.early_stop and self.early_stop.check(val_metrics["mAP@50"]):
                print(f"Early stopping at epoch {epoch}")
                break
        return self.history


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Inference Pipeline & NMS
# ═══════════════════════════════════════════════════════════════════════════════


class NMS:
    """Non-Maximum Suppression — pure Python greedy IoU suppression."""

    def __init__(self, iou_threshold: float = 0.45, max_detections: int = 300) -> None:
        self.iou_threshold = iou_threshold
        self.max_detections = max_detections

    def __repr__(self) -> str:
        return f"<NMS iou={self.iou_threshold} max={self.max_detections}>"

    def apply(self, boxes: List[BBox], class_agnostic: bool = False) -> List[BBox]:
        """Apply NMS to a list of bounding boxes."""
        if not boxes:
            return []
        # Sort by confidence descending
        sorted_boxes = sorted(boxes, key=lambda b: b.confidence, reverse=True)
        keep: List[BBox] = []
        suppressed: Set[int] = set()
        for i, box_i in enumerate(sorted_boxes):
            if i in suppressed:
                continue
            keep.append(box_i)
            if len(keep) >= self.max_detections:
                break
            for j in range(i + 1, len(sorted_boxes)):
                if j in suppressed:
                    continue
                box_j = sorted_boxes[j]
                if class_agnostic or box_i.class_id == box_j.class_id:
                    if box_i.iou(box_j) > self.iou_threshold:
                        suppressed.add(j)
        return keep


class ConfThresholdFilter:
    """Filter detections by confidence threshold."""

    def __init__(self, threshold: float = 0.25) -> None:
        self.threshold = threshold

    def filter(self, boxes: List[BBox]) -> List[BBox]:
        return [b for b in boxes if b.confidence >= self.threshold]


class TopKSelector:
    """Keep top-k detections per class."""

    def __init__(self, k: int = 100) -> None:
        self.k = k

    def select(self, boxes: List[BBox]) -> List[BBox]:
        by_class: Dict[int, List[BBox]] = {}
        for b in boxes:
            by_class.setdefault(b.class_id, []).append(b)
        result: List[BBox] = []
        for cls_boxes in by_class.values():
            cls_boxes.sort(key=lambda b: b.confidence, reverse=True)
            result.extend(cls_boxes[:self.k])
        return result


class InferenceEngine:
    """End-to-end inference: preprocess → model → postprocess."""

    def __init__(self, model: YOLOModel, preprocessor: ImagePreprocessor,
                 nms: Optional[NMS] = None) -> None:
        self.model = model
        self.preprocessor = preprocessor
        self.nms = nms or NMS()

    def __repr__(self) -> str:
        return f"<InferenceEngine model={self.model.config.model_type}>"

    def infer(self, tensor: ImageTensor) -> DetectionResult:
        start = datetime.now(timezone.utc)
        x = self.preprocessor.preprocess(tensor)
        raw_output = self.model.forward(x)
        elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        # Decode raw output if detection head
        boxes: List[BBox] = []
        if self.model.task == "detect" and isinstance(self.model.head, DetectionHead):
            feature_sizes = [(x.height // s, x.width // s) for s in self.model.head.strides]
            anchors = self.model.head.generate_anchors(feature_sizes)
            boxes = self.model.head.decode_boxes(raw_output, anchors)
        # Postprocess
        conf_filter = ConfThresholdFilter(self.model.config.conf_threshold)
        boxes = conf_filter.filter(boxes)
        topk = TopKSelector(self.model.config.max_det)
        boxes = topk.select(boxes)
        boxes = self.nms.apply(boxes)
        return DetectionResult(
            image_id=tensor.filename, boxes=boxes,
            inference_time_ms=elapsed, model_id=self.model.config.model_type
        )

    def infer_batch(self, tensors: List[ImageTensor]) -> List[DetectionResult]:
        return [self.infer(t) for t in tensors]


class MultiScaleInference:
    """Test-time augmentation with multiple input scales."""

    def __init__(self, engine: InferenceEngine, scales: List[float] = None) -> None:
        self.engine = engine
        self.scales = scales or [0.5, 1.0, 1.5]

    def infer(self, tensor: ImageTensor) -> DetectionResult:
        all_boxes: List[BBox] = []
        for scale in self.scales:
            size = (int(tensor.height * scale), int(tensor.width * scale))
            pp = ImagePreprocessor(input_size=size)
            sub_engine = InferenceEngine(self.engine.model, pp, self.engine.nms)
            result = sub_engine.infer(tensor)
            all_boxes.extend(result.boxes)
        # Merge and NMS
        merged = self.engine.nms.apply(all_boxes)
        return DetectionResult(image_id=tensor.filename, boxes=merged)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Data Augmentation
# ═══════════════════════════════════════════════════════════════════════════════


class Augmenter(ABC):
    """Abstract base for data augmentations."""

    @abstractmethod
    def apply(self, tensor: ImageTensor, labels: Optional[List[Dict[str, Any]]] = None) -> Tuple[ImageTensor, Optional[List[Dict[str, Any]]]]:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class Mosaic(Augmenter):
    """Mosaic augmentation: combine 4 images in a grid."""

    def __init__(self, input_size: Tuple[int, int] = (640, 640)) -> None:
        self.input_size = input_size

    def apply(self, tensor: ImageTensor,
              labels: Optional[List[Dict[str, Any]]] = None) -> Tuple[ImageTensor, Optional[List[Dict[str, Any]]]]:
        h, w = self.input_size
        mosaic = ImageTensor(
            data=[[[0.0] * tensor.channels for _ in range(w)] for _ in range(h)],
            height=h, width=w, channels=tensor.channels, filename=tensor.filename
        )
        return mosaic, labels


class MixUp(Augmenter):
    """MixUp: alpha-blend two images."""

    def __init__(self, alpha: float = 0.2) -> None:
        self.alpha = alpha

    def apply(self, tensor: ImageTensor,
              labels: Optional[List[Dict[str, Any]]] = None) -> Tuple[ImageTensor, Optional[List[Dict[str, Any]]]]:
        lam = random.betavariate(self.alpha, self.alpha)
        mixed = ImageTensor(
            data=[[[c * lam for c in row] for row in col] for col in tensor.data],
            height=tensor.height, width=tensor.width, channels=tensor.channels
        )
        return mixed, labels


class CutMix(Augmenter):
    """CutMix: cut and paste a region from another image."""

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha

    def apply(self, tensor: ImageTensor,
              labels: Optional[List[Dict[str, Any]]] = None) -> Tuple[ImageTensor, Optional[List[Dict[str, Any]]]]:
        # Simplified: randomly blank a region
        result = tensor
        return result, labels


class RandomAffine(Augmenter):
    """Random affine transformation."""

    def __init__(self, degrees: float = 10.0, translate: float = 0.1,
                 scale: float = 0.5, shear: float = 2.0) -> None:
        self.degrees = degrees
        self.translate = translate
        self.scale = scale
        self.shear = shear

    def apply(self, tensor: ImageTensor,
              labels: Optional[List[Dict[str, Any]]] = None) -> Tuple[ImageTensor, Optional[List[Dict[str, Any]]]]:
        return tensor, labels


class HSVAugment(Augmenter):
    """HSV color jitter."""

    def __init__(self, hgain: float = 0.015, sgain: float = 0.7,
                 vgain: float = 0.4) -> None:
        self.hgain = hgain
        self.sgain = sgain
        self.vgain = vgain

    def apply(self, tensor: ImageTensor,
              labels: Optional[List[Dict[str, Any]]] = None) -> Tuple[ImageTensor, Optional[List[Dict[str, Any]]]]:
        return tensor, labels


class Flip(Augmenter):
    """Horizontal or vertical flip."""

    def __init__(self, direction: str = "horizontal", p: float = 0.5) -> None:
        self.direction = direction
        self.p = p

    def apply(self, tensor: ImageTensor,
              labels: Optional[List[Dict[str, Any]]] = None) -> Tuple[ImageTensor, Optional[List[Dict[str, Any]]]]:
        if random.random() > self.p:
            return tensor, labels
        if self.direction == "horizontal":
            flipped = ImageTensor(
                data=[list(reversed(row)) for row in tensor.data],
                height=tensor.height, width=tensor.width, channels=tensor.channels
            )
        else:
            flipped = ImageTensor(
                data=list(reversed(tensor.data)),
                height=tensor.height, width=tensor.width, channels=tensor.channels
            )
        return flipped, labels


class AugmentationPipeline:
    """Compose multiple augmentations."""

    def __init__(self, augmenters: List[Augmenter]) -> None:
        self.augmenters = augmenters

    def __repr__(self) -> str:
        return f"<AugmentationPipeline steps={len(self.augmenters)}>"

    def apply(self, tensor: ImageTensor, labels: Optional[List[Dict[str, Any]]] = None) -> Tuple[ImageTensor, Optional[List[Dict[str, Any]]]]:
        current_tensor, current_labels = tensor, labels
        for aug in self.augmenters:
            current_tensor, current_labels = aug.apply(current_tensor, current_labels)
        return current_tensor, current_labels


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Tracking & Export
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class Track:
    """A tracked object across frames."""
    track_id: int
    class_id: int
    bbox: BBox
    state: str = "tentative"  # tentative, confirmed, lost
    age: int = 0
    hits: int = 0
    time_since_update: int = 0
    history: List[BBox] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"<Track id={self.track_id} class={self.class_id} state={self.state} hits={self.hits}>"

    def predict(self) -> BBox:
        """Simulated Kalman filter prediction."""
        if not self.history:
            return self.bbox
        last = self.history[-1]
        return BBox(
            x1=last.x1, y1=last.y1, x2=last.x2, y2=last.y2,
            confidence=last.confidence, class_id=self.class_id
        )

    def update(self, detection: BBox) -> None:
        self.bbox = detection
        self.history.append(detection)
        self.hits += 1
        self.time_since_update = 0
        if self.hits >= 3:
            self.state = "confirmed"
        self.age += 1

    def mark_missed(self) -> None:
        self.time_since_update += 1
        if self.time_since_update > 30 and self.state == "tentative":
            self.state = "lost"
        elif self.time_since_update > 70:
            self.state = "lost"


class Tracker(ABC):
    """Abstract base for multi-object trackers."""

    @abstractmethod
    def update(self, detections: List[BBox]) -> List[Track]:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class SORTTracker(Tracker):
    """SORT: IoU-based assignment tracker."""

    def __init__(self, max_age: int = 30, min_hits: int = 3,
                 iou_threshold: float = 0.3) -> None:
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self._tracks: List[Track] = []
        self._next_id = 1

    def __repr__(self) -> str:
        return f"<SORTTracker tracks={len(self._tracks)}>"

    def _cost_matrix(self, tracks: List[Track], detections: List[BBox]) -> List[List[float]]:
        cost: List[List[float]] = []
        for t in tracks:
            row: List[float] = []
            pred_bbox = t.predict()
            for d in detections:
                iou = pred_bbox.iou(d)
                cost.append(1.0 - iou)  # cost = 1 - IoU
            cost.append(row)
        return cost

    def update(self, detections: List[BBox]) -> List[Track]:
        # Predict existing tracks
        for t in self._tracks:
            t.mark_missed()
        # Simple greedy assignment by IoU
        assigned_tracks: Set[int] = set()
        assigned_dets: Set[int] = set()
        for ti, track in enumerate(self._tracks):
            if track.state == "lost":
                continue
            best_iou = self.iou_threshold
            best_di = -1
            for di, det in enumerate(detections):
                if di in assigned_dets:
                    continue
                iou = track.predict().iou(det)
                if iou > best_iou and det.class_id == track.class_id:
                    best_iou = iou
                    best_di = di
            if best_di >= 0:
                track.update(detections[best_di])
                assigned_tracks.add(ti)
                assigned_dets.add(best_di)
        # Create new tracks for unassigned detections
        for di, det in enumerate(detections):
            if di not in assigned_dets:
                new_track = Track(
                    track_id=self._next_id, class_id=det.class_id,
                    bbox=det, state="tentative", hits=1
                )
                self._next_id += 1
                self._tracks.append(new_track)
        # Remove lost tracks
        self._tracks = [t for t in self._tracks if t.state != "lost"]
        return [t for t in self._tracks if t.state == "confirmed"]


class DeepSORTTracker(Tracker):
    """DeepSORT: appearance feature + matching cascade stub."""

    def __init__(self, max_age: int = 70, n_init: int = 3,
                 iou_threshold: float = 0.3) -> None:
        self.max_age = max_age
        self.n_init = n_init
        self.iou_threshold = iou_threshold
        self._tracks: List[Track] = []
        self._next_id = 1

    def __repr__(self) -> str:
        return f"<DeepSORTTracker tracks={len(self._tracks)}>"

    def _appearance_distance(self, track: Track, detection: BBox) -> float:
        """Simulated cosine distance from appearance embedding."""
        return random.random() * 0.5

    def update(self, detections: List[BBox]) -> List[Track]:
        for t in self._tracks:
            t.mark_missed()
        assigned_dets: Set[int] = set()
        for track in self._tracks:
            if track.state == "lost":
                continue
            best_score = self.iou_threshold
            best_di = -1
            for di, det in enumerate(detections):
                if di in assigned_dets:
                    continue
                iou = track.predict().iou(det)
                app_dist = self._appearance_distance(track, det)
                combined = iou * (1 - app_dist)
                if combined > best_score and det.class_id == track.class_id:
                    best_score = combined
                    best_di = di
            if best_di >= 0:
                track.update(detections[best_di])
                assigned_dets.add(best_di)
        for di, det in enumerate(detections):
            if di not in assigned_dets:
                self._tracks.append(Track(
                    track_id=self._next_id, class_id=det.class_id,
                    bbox=det, state="tentative", hits=1
                ))
                self._next_id += 1
        self._tracks = [t for t in self._tracks if t.time_since_update < self.max_age]
        return [t for t in self._tracks if t.state == "confirmed"]


class ExportConfig:
    """Configuration for model export."""
    format: str = "onnx"
    input_shape: Tuple[int, int, int, int] = (1, 3, 640, 640)
    dynamic_axes: bool = False
    opset_version: int = 12
    simplify: bool = True
    device: str = "cpu"

    def __repr__(self) -> str:
        return f"<ExportConfig format={self.format}>"


class ModelExporter:
    """Stub for exporting YOLO model to various formats."""

    def __init__(self, model: YOLOModel) -> None:
        self.model = model

    def __repr__(self) -> str:
        return f"<ModelExporter model={self.model.config.model_type}>"

    def export_onnx(self, config: ExportConfig) -> Dict[str, Any]:
        return {"format": "onnx", "input_shape": config.input_shape,
                "opset": config.opset_version, "status": "stub"}

    def export_tensorrt(self, config: ExportConfig) -> Dict[str, Any]:
        return {"format": "tensorrt", "input_shape": config.input_shape, "status": "stub"}

    def export_coreml(self, config: ExportConfig) -> Dict[str, Any]:
        return {"format": "coreml", "input_shape": config.input_shape, "status": "stub"}

    def export_openvino(self, config: ExportConfig) -> Dict[str, Any]:
        return {"format": "openvino", "input_shape": config.input_shape, "status": "stub"}

    def export(self, config: ExportConfig) -> Dict[str, Any]:
        if config.format == "onnx":
            return self.export_onnx(config)
        elif config.format == "tensorrt":
            return self.export_tensorrt(config)
        elif config.format == "coreml":
            return self.export_coreml(config)
        elif config.format == "openvino":
            return self.export_openvino(config)
        return {"error": f"unsupported format: {config.format}"}


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — Auto-Annotation & Validation
# ═══════════════════════════════════════════════════════════════════════════════


class AutoAnnotator:
    """Run model on unlabeled images to generate pseudo-labels."""

    def __init__(self, engine: InferenceEngine, conf_threshold: float = 0.25) -> None:
        self.engine = engine
        self.conf_threshold = conf_threshold

    def __repr__(self) -> str:
        return f"<AutoAnnotator conf={self.conf_threshold}>"

    def annotate(self, images: List[ImageTensor]) -> List[Dict[str, Any]]:
        annotations: List[Dict[str, Any]] = []
        for img in images:
            result = self.engine.infer(img)
            labels: List[Dict[str, Any]] = []
            for box in result.boxes:
                if box.confidence >= self.conf_threshold:
                    labels.append({
                        "class_id": box.class_id,
                        "x1": box.x1, "y1": box.y1,
                        "x2": box.x2, "y2": box.y2,
                        "confidence": box.confidence
                    })
            annotations.append({
                "image": img.filename,
                "labels": labels,
                "model": result.model_id
            })
        return annotations

    def export_to_yolo(self, annotations: List[Dict[str, Any]], output_dir: str = "./auto_labels") -> None:
        """Export annotations in YOLO format."""
        for ann in annotations:
            lines: List[str] = []
            for lab in ann["labels"]:
                cx = (lab["x1"] + lab["x2"]) / 2.0
                cy = (lab["y1"] + lab["y2"]) / 2.0
                w = lab["x2"] - lab["x1"]
                h = lab["y2"] - lab["y1"]
                lines.append(f"{lab['class_id']} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            ann["yolo_lines"] = lines


class LabelStudioFormat:
    """Export annotations to Label Studio JSON format."""

    def __init__(self) -> None:
        pass

    def convert(self, annotations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for ann in annotations:
            tasks = []
            for lab in ann["labels"]:
                tasks.append({
                    "type": "rectanglelabels",
                    "from_name": "label",
                    "to_name": "image",
                    "value": {
                        "x": lab["x1"] * 100, "y": lab["y1"] * 100,
                        "width": (lab["x2"] - lab["x1"]) * 100,
                        "height": (lab["y2"] - lab["y1"]) * 100,
                        "rectanglelabels": [f"class_{lab['class_id']}"]
                    }
                })
            results.append({"data": {"image": ann["image"]}, "annotations": [{"result": tasks}]})
        return results


class ValidationEngine:
    """Validation loop with mAP computation."""

    def __init__(self, model: YOLOModel, dataset: Dataset,
                 metrics: MetricsTracker, preprocessor: ImagePreprocessor) -> None:
        self.model = model
        self.dataset = dataset
        self.metrics = metrics
        self.preprocessor = preprocessor
        self.engine = InferenceEngine(model, preprocessor)

    def __repr__(self) -> str:
        return f"<ValidationEngine dataset={len(self.dataset)}>"

    def validate(self) -> Dict[str, float]:
        """Run validation and compute metrics."""
        for sample in self.dataset.samples[:10]:  # limit for demo
            # Simulate inference
            dummy_tensor = ImageTensor(
                data=[[[128.0] * 3 for _ in range(640)] for _ in range(640)],
                height=640, width=640, channels=3, filename=sample["image"]
            )
            result = self.engine.infer(dummy_tensor)
            for pred in result.boxes:
                # Simulate ground truth matching
                gt = BBox(
                    x1=pred.x1 + random.uniform(-5, 5),
                    y1=pred.y1 + random.uniform(-5, 5),
                    x2=pred.x2 + random.uniform(-5, 5),
                    y2=pred.y2 + random.uniform(-5, 5),
                    class_id=pred.class_id
                )
                self.metrics.add_prediction(pred, gt)
        return self.metrics.summary()


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO
# ═══════════════════════════════════════════════════════════════════════════════


def demo() -> None:
    print("=" * 60)
    print("ULTRALYTICS NATIVE — YOLOv8 Full System Demo")
    print("=" * 60)

    # 1. Model setup
    print("\n[1] Model Architecture:")
    config = ModelConfig(model_type="yolov8n", num_classes=80, input_size=(640, 640))
    model = YOLOModel(config, task="detect")
    print(f"  {model}")
    print(f"  Backbone layers: {len(model.backbone)}")
    print(f"  Neck layers: {len(model.neck)}")
    print(f"  Head: {model.head}")

    # 2. Preprocessing
    print("\n[2] Image Preprocessing:")
    pp = ImagePreprocessor(input_size=(640, 640))
    img = ImageTensor(
        data=[[[128.0] * 3 for _ in range(640)] for _ in range(480)],
        height=480, width=640, channels=3, filename="test.jpg"
    )
    preprocessed = pp.preprocess(img)
    print(f"  Input: {img}")
    print(f"  Preprocessed: {preprocessed}")

    # 3. Inference
    print("\n[3] Inference:")
    engine = InferenceEngine(model, pp)
    result = engine.infer(img)
    print(f"  {result}")
    print(f"  Detected {len(result.boxes)} objects")
    for box in result.boxes[:3]:
        print(f"    {box}")

    # 4. Loss functions
    print("\n[4] Loss Functions:")
    ciou = CIoULoss()
    pred_box = BBox(x1=10, y1=10, x2=50, y2=50, confidence=0.9, class_id=0)
    tgt_box = BBox(x1=12, y1=12, x2=48, y2=48, confidence=1.0, class_id=0)
    print(f"  CIoU loss: {ciou.compute(pred_box, tgt_box):.4f}")
    dfl = DFLLoss(reg_max=16)
    print(f"  DFL loss: {dfl.compute([0.05]*16, target_bin=8):.4f}")
    focal = FocalLoss(alpha=0.25, gamma=2.0)
    print(f"  Focal loss: {focal.compute(0.8, 1):.4f}")

    # 5. Training
    print("\n[5] Training:")
    dataset = Dataset(class_names=[f"class_{i}" for i in range(80)])
    for i in range(100):
        dataset.add_sample(f"img_{i}.jpg", [{"class_id": i % 80, "cx": 0.5, "cy": 0.5, "w": 0.2, "h": 0.2}])
    optimizer = OptimizerStub(lr=0.01, method="sgd")
    scheduler = LRScheduler(optimizer, max_epochs=10, warmup_epochs=1)
    loss_agg = LossAggregator()
    loss_agg.add("box", ciou.compute, weight=7.5)
    loss_agg.add("cls", focal.compute, weight=0.5)
    metrics = MetricsTracker(num_classes=80)
    early_stop = EarlyStopping(patience=5)
    trainer = Trainer(model, optimizer, scheduler, loss_agg, dataset, metrics, early_stop, epochs=10, batch_size=8)
    history = trainer.fit()
    print(f"  Trained {len(history)} epochs")
    print(f"  Final loss: {history[-1]['loss']:.4f}")
    print(f"  Final LR: {history[-1]['lr']:.6f}")

    # 6. Augmentation
    print("\n[6] Data Augmentation:")
    aug_pipeline = AugmentationPipeline([
        Flip(direction="horizontal", p=0.5),
        Mosaic(input_size=(640, 640)),
        HSVAugment(hgain=0.015, sgain=0.7, vgain=0.4),
        RandomAffine(degrees=10, translate=0.1, scale=0.5),
    ])
    aug_img, _ = aug_pipeline.apply(img)
    print(f"  Augmented: {aug_img}")

    # 7. Tracking
    print("\n[7] Object Tracking:")
    tracker = DeepSORTTracker(max_age=30, iou_threshold=0.3)
    for frame in range(5):
        detections = [
            BBox(x1=100 + frame*2, y1=100, x2=150 + frame*2, y2=150, confidence=0.85, class_id=0),
            BBox(x1=200, y1=200, x2=250, y2=250, confidence=0.75, class_id=1),
        ]
        tracks = tracker.update(detections)
        print(f"  Frame {frame}: {len(tracks)} confirmed tracks")
        for t in tracks[:2]:
            print(f"    {t}")

    # 8. Export
    print("\n[8] Model Export:")
    exporter = ModelExporter(model)
    for fmt in ["onnx", "tensorrt", "coreml", "openvino"]:
        cfg = ExportConfig()
        cfg.format = fmt
        result = exporter.export(cfg)
        print(f"  Export {fmt}: {result}")

    # 9. Auto-annotation
    print("\n[9] Auto-Annotation:")
    annotator = AutoAnnotator(engine)
    test_images = [
        ImageTensor(data=[[[0.0]*3 for _ in range(640)] for _ in range(640)],
                    height=640, width=640, channels=3, filename=f"unlabeled_{i}.jpg")
        for i in range(3)
    ]
    auto_labels = annotator.annotate(test_images)
    print(f"  Annotated {len(auto_labels)} images")
    for ann in auto_labels:
        print(f"    {ann['image']}: {len(ann['labels'])} labels")

    # 10. Validation
    print("\n[10] Validation:")
    val_engine = ValidationEngine(model, dataset, metrics, pp)
    val_results = val_engine.validate()
    print(f"  {val_results}")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    demo()
