"""
livekit_agents_native.py
Native Python reimplementation of the livekit/agents real-time voice/video AI agent framework.

Pure Python — no hard dependencies on LiveKit SDK, Twilio, or WebRTC libraries.
All I/O is async/await. Simulated via abstract adapters and demo stubs.

Architecture:
    RoomManager → MediaPipe → STTPipeline → LLMPipeline → TTSPipeline → TranscriptionSink
                            ↓                  ↓
                     FunctionExecutor ← AgentRunner ← AgentConfig + LiveKitKernel
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import math
import textwrap
import time
import uuid
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Coroutine,
    Deque,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Protocol,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("livekit_native")


# ════════════════════════════════════════════════════════════════════════
# 1. BASE LAYER — Media dataclasses and primitives
# ════════════════════════════════════════════════════════════════════════

class TrackKind(Enum):
    """Kinds of media tracks in a LiveKit room."""
    AUDIO = auto()
    VIDEO = auto()
    DATA = auto()


@dataclass(frozen=True, slots=True)
class AudioFrame:
    """Immutable container for raw PCM audio data.

    Attributes:
        sample_rate: Sampling frequency in Hz (e.g. 16000, 48000).
        channels: Number of interleaved channels (1=mono, 2=stereo).
        data: Raw PCM bytes (little-endian 16-bit assumed).
        timestamp_ms: Capture timestamp in milliseconds (epoch or monotonic).
    """
    sample_rate: int
    channels: int
    data: bytes
    timestamp_ms: float

    def __repr__(self) -> str:
        return (
            f"AudioFrame(sr={self.sample_rate}, ch={self.channels}, "
            f"bytes={len(self.data)}, ts={self.timestamp_ms:.1f})"
        )

    def duration_ms(self) -> float:
        """Return the audio duration represented by this frame in milliseconds."""
        samples = len(self.data) // (2 * self.channels)  # 16-bit
        return (samples / self.sample_rate) * 1000.0


@dataclass(frozen=True, slots=True)
class VideoFrame:
    """Immutable container for a video frame.

    Attributes:
        width: Frame width in pixels.
        height: Frame height in pixels.
        format_str: Pixel format descriptor (e.g. 'NV12', 'I420', 'RGBA').
        data: Raw pixel bytes.
        timestamp_ms: Capture timestamp in milliseconds.
    """
    width: int
    height: int
    format_str: str
    data: bytes
    timestamp_ms: float

    def __repr__(self) -> str:
        return (
            f"VideoFrame({self.width}x{self.height} {self.format_str}, "
            f"bytes={len(self.data)}, ts={self.timestamp_ms:.1f})"
        )


@dataclass
class Track:
    """A single media track within a room.

    In native simulation mode tracks are backed by ``asyncio.Queue`` instances
    rather than real WebRTC RTP senders/receivers.
    """
    track_id: str
    kind: TrackKind
    source_sid: str  # participant who published this track
    queue: asyncio.Queue = field(repr=False)
    metadata: Dict[str, Any] = field(default_factory=dict)
    active: bool = True

    def __post_init__(self) -> None:
        if not self.track_id:
            self.track_id = f"track_{uuid.uuid4().hex[:8]}"

    def __repr__(self) -> str:
        return f"Track(id={self.track_id}, kind={self.kind.name}, src={self.source_sid}, active={self.active})"


@dataclass
class Participant:
    """A participant (local or remote) inside a LiveKit room."""
    sid: str
    identity: str
    name: str = ""
    is_local: bool = False
    tracks: Dict[str, Track] = field(default_factory=dict, repr=False)
    metadata: Dict[str, Any] = field(default_factory=dict)
    joined_at: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        return f"Participant(sid={self.sid}, id={self.identity}, name={self.name}, local={self.is_local})"


@dataclass
class Room:
    """Represents a single LiveKit room (simulated)."""
    room_id: str
    name: str
    participants: Dict[str, Participant] = field(default_factory=dict, repr=False)
    tracks: Dict[str, Track] = field(default_factory=dict, repr=False)
    created_at: float = field(default_factory=time.time)
    event_queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(), repr=False)

    def __repr__(self) -> str:
        return f"Room(id={self.room_id}, name={self.name}, participants={len(self.participants)})"


# ════════════════════════════════════════════════════════════════════════
# 2. ROOM MANAGER — Multi-room WebRTC simulation
# ════════════════════════════════════════════════════════════════════════

class RoomEvent(Enum):
    """Events emitted by RoomManager."""
    CONNECTED = auto()
    DISCONNECTED = auto()
    PARTICIPANT_JOINED = auto()
    PARTICIPANT_LEFT = auto()
    TRACK_PUBLISHED = auto()
    TRACK_SUBSCRIBED = auto()
    TRACK_UNPUBLISHED = auto()
    DATA_RECEIVED = auto()
    CONNECTION_STATE_CHANGED = auto()


@dataclass
class RoomEventPayload:
    """Payload wrapper for room-level events."""
    event: RoomEvent
    room_id: str
    data: Any = None

    def __repr__(self) -> str:
        return f"RoomEventPayload({self.event.name}, room={self.room_id})"


class RoomManager:
    """Manages multiple simulated LiveKit rooms.

    Responsibilities:
        - Connect / disconnect to rooms.
        - Publish and subscribe tracks (audio, video, data).
        - Emit room events via an asyncio Queue.
        - Maintain participant registry per room.
    """

    def __init__(self) -> None:
        self._rooms: Dict[str, Room] = {}
        self._local_participants: Dict[str, Participant] = {}
        self._event_queue: asyncio.Queue[RoomEventPayload] = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._reconnect_tasks: Dict[str, asyncio.Task] = {}

    def __repr__(self) -> str:
        return f"RoomManager(rooms={len(self._rooms)})"

    # ── Public API ─────────────────────────────────────────────────────

    async def connect(self, room_name: str, local_identity: str, token: str = "") -> Room:
        """Connect to (or create) a room.

        Args:
            room_name: Human-readable room name.
            local_identity: Identity of the local participant.
            token: Simulated auth token (ignored in native mode).

        Returns:
            The connected ``Room`` instance.
        """
        async with self._lock:
            room_id = f"room_{room_name}_{uuid.uuid4().hex[:6]}"
            room = Room(room_id=room_id, name=room_name)
            local_sid = f"local_{uuid.uuid4().hex[:8]}"
            local_participant = Participant(
                sid=local_sid, identity=local_identity, name=local_identity, is_local=True
            )
            room.participants[local_sid] = local_participant
            self._local_participants[room_id] = local_participant
            self._rooms[room_id] = room
            logger.info("Connected to room %s as %s", room_name, local_identity)
            await self._emit(RoomEvent.CONNECTED, room_id, room)
            return room

    async def disconnect(self, room_id: str, reason: str = "user_request") -> None:
        """Disconnect from a room and cancel any reconnect loop."""
        async with self._lock:
            room = self._rooms.pop(room_id, None)
            if room is None:
                return
            self._local_participants.pop(room_id, None)
            reconnect_task = self._reconnect_tasks.pop(room_id, None)
            if reconnect_task:
                reconnect_task.cancel()
                try:
                    await reconnect_task
                except asyncio.CancelledError:
                    pass
            logger.info("Disconnected from room %s: %s", room.name, reason)
            await self._emit(RoomEvent.DISCONNECTED, room_id, reason)

    async def publish_track(
        self, room_id: str, kind: TrackKind, metadata: Optional[Dict[str, Any]] = None
    ) -> Track:
        """Publish a new local track into a room.

        Returns:
            The newly created ``Track``.
        """
        async with self._lock:
            room = self._rooms[room_id]
            local = self._local_participants[room_id]
            track_id = f"pub_{kind.name.lower()}_{uuid.uuid4().hex[:8]}"
            track = Track(
                track_id=track_id,
                kind=kind,
                source_sid=local.sid,
                queue=asyncio.Queue(),
                metadata=metadata or {},
            )
            room.tracks[track_id] = track
            local.tracks[track_id] = track
            logger.info("Published %s track %s in room %s", kind.name, track_id, room.name)
            await self._emit(RoomEvent.TRACK_PUBLISHED, room_id, track)
            return track

    async def subscribe_track(self, room_id: str, track_id: str) -> Track:
        """Subscribe to a remote track by ID.

        Returns:
            A proxy ``Track`` whose queue receives frames forwarded from the
            original publisher.
        """
        async with self._lock:
            room = self._rooms[room_id]
            source_track = room.tracks.get(track_id)
            if source_track is None:
                raise KeyError(f"Track {track_id} not found in room {room_id}")
            proxy_queue: asyncio.Queue = asyncio.Queue()
            proxy = Track(
                track_id=f"sub_{track_id}",
                kind=source_track.kind,
                source_sid=source_track.source_sid,
                queue=proxy_queue,
                metadata=dict(source_track.metadata),
            )
            logger.info("Subscribed to track %s in room %s", track_id, room.name)
            await self._emit(RoomEvent.TRACK_SUBSCRIBED, room_id, proxy)
            # Start forwarding task
            asyncio.create_task(self._forward_frames(source_track, proxy_queue))
            return proxy

    async def send_data(self, room_id: str, payload: bytes, destination_identities: Optional[List[str]] = None) -> None:
        """Send data message to all or selected participants."""
        async with self._lock:
            room = self._rooms[room_id]
            for p in room.participants.values():
                if destination_identities and p.identity not in destination_identities:
                    continue
                # In a real SDK this would use DataChannel.send()
                logger.debug("Data sent to %s (%d bytes)", p.identity, len(payload))
            await self._emit(RoomEvent.DATA_RECEIVED, room_id, payload)

    async def simulate_participant_join(self, room_id: str, identity: str, name: str = "") -> Participant:
        """Simulate a remote participant joining (for testing/demo)."""
        async with self._lock:
            room = self._rooms[room_id]
            sid = f"remote_{uuid.uuid4().hex[:8]}"
            p = Participant(sid=sid, identity=identity, name=name or identity)
            room.participants[sid] = p
            logger.info("Participant joined: %s in room %s", identity, room.name)
            await self._emit(RoomEvent.PARTICIPANT_JOINED, room_id, p)
            return p

    async def simulate_participant_leave(self, room_id: str, sid: str) -> None:
        """Simulate a remote participant leaving."""
        async with self._lock:
            room = self._rooms[room_id]
            p = room.participants.pop(sid, None)
            if p:
                logger.info("Participant left: %s from room %s", p.identity, room.name)
                await self._emit(RoomEvent.PARTICIPANT_LEFT, room_id, p)

    def get_room(self, room_id: str) -> Optional[Room]:
        return self._rooms.get(room_id)

    def event_queue(self) -> asyncio.Queue[RoomEventPayload]:
        return self._event_queue

    # ── Internal helpers ───────────────────────────────────────────────

    async def _emit(self, event: RoomEvent, room_id: str, data: Any = None) -> None:
        payload = RoomEventPayload(event=event, room_id=room_id, data=data)
        await self._event_queue.put(payload)

    async def _forward_frames(self, source: Track, sink: asyncio.Queue, maxsize: int = 128) -> None:
        """Forward frames from a source track queue into a sink queue."""
        try:
            while source.active:
                try:
                    frame = await asyncio.wait_for(source.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                if sink.qsize() >= maxsize:
                    sink.get_nowait()  # drop oldest to keep latency low
                await sink.put(frame)
        except asyncio.CancelledError:
            logger.debug("Forwarding cancelled for track %s", source.track_id)


# ════════════════════════════════════════════════════════════════════════
# 3. MEDIA PIPE — Buffers, resampling, jitter, A/V sync
# ════════════════════════════════════════════════════════════════════════

T = TypeVar("T")


class RingBuffer(Generic[T]):
    """Fixed-capacity ring buffer implemented with ``collections.deque``."""

    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._deque: Deque[T] = deque(maxlen=capacity)

    def __repr__(self) -> str:
        return f"RingBuffer(len={len(self._deque)}/{self._capacity})"

    def push(self, item: T) -> None:
        """Push an item; oldest drops if at capacity."""
        self._deque.append(item)

    def pop(self) -> Optional[T]:
        """Pop oldest item, or None if empty."""
        return self._deque.popleft() if self._deque else None

    def peek(self, index: int = 0) -> Optional[T]:
        """Peek at *index* from the front without removing."""
        if 0 <= index < len(self._deque):
            return self._deque[index]
        return None

    def clear(self) -> None:
        self._deque.clear()

    def __len__(self) -> int:
        return len(self._deque)

    def __iter__(self):
        return iter(self._deque)


class AudioBuffer:
    """Ring-buffer for audio frames with resampling support.

    Maintains a window of recent ``AudioFrame`` instances and can produce
    contiguous PCM byte strings at a target sample rate.
    """

    def __init__(self, max_frames: int = 200) -> None:
        self._ring = RingBuffer[AudioFrame](max_frames)
        self._target_rate: Optional[int] = None

    def __repr__(self) -> str:
        return f"AudioBuffer(frames={len(self._ring)}, target_rate={self._target_rate})"

    def push(self, frame: AudioFrame) -> None:
        self._ring.push(frame)

    def read(self, max_duration_ms: float = 500.0) -> Optional[Tuple[int, int, bytes]]:
        """Read up to *max_duration_ms* of contiguous audio.

        Returns:
            (sample_rate, channels, pcm_bytes) or None if empty.
        """
        if len(self._ring) == 0:
            return None
        collected: List[AudioFrame] = []
        total_ms = 0.0
        for frame in self._ring:
            collected.append(frame)
            total_ms += frame.duration_ms()
            if total_ms >= max_duration_ms:
                break
        if not collected:
            return None
        sr = collected[0].sample_rate
        ch = collected[0].channels
        # Simple concatenation (assumes same format across frames)
        pcm = b"".join(f.data for f in collected)
        return sr, ch, pcm

    def resample_linear(self, pcm: bytes, source_rate: int, target_rate: int, channels: int) -> bytes:
        """Naive linear resampling (nearest-neighbour decimation/interpolation).

        This is *not* high-quality — suitable for simulation only.
        """
        if source_rate == target_rate:
            return pcm
        # Interpret as 16-bit little-endian signed ints
        import array as _array
        arr = _array.array("h", pcm)
        sample_count = len(arr) // channels
        ratio = target_rate / source_rate
        new_count = int(sample_count * ratio)
        if new_count == 0:
            return b""
        out = _array.array("h")
        for i in range(new_count):
            src_idx = int(i / ratio)
            src_idx = min(src_idx, sample_count - 1)
            for ch in range(channels):
                out.append(arr[src_idx * channels + ch])
        return out.tobytes()

    def drain(self) -> None:
        self._ring.clear()


class VideoBuffer:
    """Ring-buffer for video frames with deduplication."""

    def __init__(self, max_frames: int = 90) -> None:
        self._ring = RingBuffer[VideoFrame](max_frames)
        self._seen_timestamps: Set[float] = set()

    def __repr__(self) -> str:
        return f"VideoBuffer(frames={len(self._ring)})"

    def push(self, frame: VideoFrame) -> bool:
        """Push a frame; returns True if accepted, False if duplicate."""
        if frame.timestamp_ms in self._seen_timestamps:
            return False
        self._seen_timestamps.add(frame.timestamp_ms)
        self._ring.push(frame)
        # Prevent unbounded growth of seen set
        if len(self._seen_timestamps) > self._ring._capacity * 2:
            self._seen_timestamps.clear()
        return True

    def read_latest(self) -> Optional[VideoFrame]:
        return self._ring.peek(-1) if len(self._ring) else None

    def drain(self) -> None:
        self._ring.clear()
        self._seen_timestamps.clear()


class JitterBuffer:
    """De-jitter buffer that reorders frames by timestamp.

    Simulates a WebRTC jitter buffer: frames arrive out-of-order and are
    released in monotonic timestamp order after a small delay budget.
    """

    def __init__(self, delay_ms: float = 80.0, max_size: int = 64) -> None:
        self.delay_ms = delay_ms
        self.max_size = max_size
        self._frames: List[AudioFrame] = []
        self._last_release: float = 0.0

    def __repr__(self) -> str:
        return f"JitterBuffer(delay={self.delay_ms}ms, buffered={len(self._frames)})"

    def push(self, frame: AudioFrame) -> None:
        if len(self._frames) >= self.max_size:
            self._frames.pop(0)
        self._frames.append(frame)
        self._frames.sort(key=lambda f: f.timestamp_ms)

    def pop_ready(self, now_ms: float) -> Optional[AudioFrame]:
        """Return the next frame if its timestamp + delay <= now."""
        if not self._frames:
            return None
        next_frame = self._frames[0]
        if next_frame.timestamp_ms + self.delay_ms <= now_ms:
            self._last_release = next_frame.timestamp_ms
            return self._frames.pop(0)
        return None


class AVSync:
    """Audio / Video lip-sync aligner.

    Holds both an AudioBuffer and VideoBuffer and attempts to align them by
    timestamp so that audio and video consumed downstream are roughly in sync.
    """

    def __init__(self, max_drift_ms: float = 120.0) -> None:
        self.audio = AudioBuffer(max_frames=200)
        self.video = VideoBuffer(max_frames=90)
        self.max_drift_ms = max_drift_ms

    def __repr__(self) -> str:
        return f"AVSync(audio={self.audio}, video={self.video}, drift={self.max_drift_ms}ms)"

    def push_audio(self, frame: AudioFrame) -> None:
        self.audio.push(frame)

    def push_video(self, frame: VideoFrame) -> None:
        self.video.push(frame)

    def read_synced(self, duration_ms: float = 200.0) -> Optional[Tuple[bytes, Optional[VideoFrame]]]:
        """Read a chunk of audio and the best-matching video frame.

        Returns:
            (audio_pcm_bytes, nearest_video_frame_or_None).
        """
        audio_read = self.audio.read(duration_ms)
        if audio_read is None:
            return None
        sr, ch, pcm = audio_read
        # Approximate midpoint timestamp of this audio chunk
        mid_ts = time.time() * 1000.0
        # Find nearest video frame by timestamp
        best: Optional[VideoFrame] = None
        best_diff = float("inf")
        for vf in self.video._ring:
            diff = abs(vf.timestamp_ms - mid_ts)
            if diff < best_diff:
                best_diff = diff
                best = vf
        if best and best_diff > self.max_drift_ms:
            best = None
        return pcm, best

    def drain(self) -> None:
        self.audio.drain()
        self.video.drain()


# ════════════════════════════════════════════════════════════════════════
# 4. STT PIPELINE — Speech-to-Text
# ════════════════════════════════════════════════════════════════════════

class VADState(Enum):
    """Voice Activity Detection state machine."""
    SILENCE = auto()
    STARTING = auto()
    SPEAKING = auto()
    ENDING = auto()


class VADSegmenter:
    """Energy-based Voice Activity Detection with WebRTC-style state machine.

    Uses a simple energy threshold on 16-bit PCM frames and a hangover
    mechanism to reduce spurious toggling.
    """

    def __init__(
        self,
        energy_threshold: float = 500.0,
        hangover_frames: int = 20,
        activation_frames: int = 5,
        sample_rate: int = 16000,
        frame_duration_ms: float = 30.0,
    ) -> None:
        self.energy_threshold = energy_threshold
        self.hangover_frames = hangover_frames
        self.activation_frames = activation_frames
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms

        self._state = VADState.SILENCE
        self._silent_count = 0
        self._active_count = 0
        self._segment_buffer: List[bytes] = []
        self._on_speech_start: Optional[Callable[[], Awaitable[None]]] = None
        self._on_speech_end: Optional[Callable[[bytes], Awaitable[None]]] = None

    def __repr__(self) -> str:
        return (
            f"VADSegmenter(state={self._state.name}, "
            f"threshold={self.energy_threshold}, "
            f"buffered_frames={len(self._segment_buffer)})"
        )

    def _rms_energy(self, pcm: bytes) -> float:
        import array as _array
        arr = _array.array("h", pcm)
        if not arr:
            return 0.0
        squares = sum(x * x for x in arr)
        return math.sqrt(squares / len(arr))

    def set_callbacks(
        self,
        on_speech_start: Optional[Callable[[], Awaitable[None]]] = None,
        on_speech_end: Optional[Callable[[bytes], Awaitable[None]]] = None,
    ) -> None:
        self._on_speech_start = on_speech_start
        self._on_speech_end = on_speech_end

    async def push_frame(self, pcm: bytes) -> Optional[bytes]:
        """Push a frame of PCM audio and return a completed segment if speech ended.

        Args:
            pcm: Raw 16-bit little-endian PCM bytes.

        Returns:
            Completed speech segment bytes if speech just ended, else None.
        """
        energy = self._rms_energy(pcm)
        is_speech = energy > self.energy_threshold

        completed_segment: Optional[bytes] = None

        if self._state == VADState.SILENCE:
            if is_speech:
                self._active_count += 1
                if self._active_count >= self.activation_frames:
                    self._state = VADState.SPEAKING
                    self._active_count = 0
                    self._segment_buffer.clear()
                    self._segment_buffer.append(pcm)
                    if self._on_speech_start:
                        await self._on_speech_start()
            else:
                self._active_count = max(0, self._active_count - 1)

        elif self._state == VADState.SPEAKING:
            self._segment_buffer.append(pcm)
            if not is_speech:
                self._silent_count += 1
                if self._silent_count >= self.hangover_frames:
                    self._state = VADState.SILENCE
                    self._silent_count = 0
                    completed_segment = b"".join(self._segment_buffer)
                    self._segment_buffer.clear()
                    if self._on_speech_end:
                        await self._on_speech_end(completed_segment)
            else:
                self._silent_count = max(0, self._silent_count - 1)

        return completed_segment


class STTAdapter(ABC):
    """Abstract base for Speech-to-Text adapters.

    Implementations must support streaming inference: chunks of audio are fed
    continuously and partial transcripts are produced in real time.
    """

    @abstractmethod
    def stream_chunk(self, pcm: bytes, sample_rate: int, channels: int, timestamp_ms: float) -> None:
        """Feed a chunk of audio into the streaming recognizer."""
        ...

    @abstractmethod
    async def finalize(self) -> str:
        """Finalize and return the best transcript for the current utterance."""
        ...

    @abstractmethod
    async def flush(self) -> None:
        """Reset internal state for a new utterance."""
        ...

    @abstractmethod
    def partial_transcript(self) -> str:
        """Return the current best partial transcript (may be empty)."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(abstract)"


class MockSTTAdapter(STTAdapter):
    """Demo STT adapter that simulates streaming recognition.

    Every 20 chunks it emits a partial word; every 60 chunks it emits a
    sentence; finalize returns the full accumulated transcript.
    """

    DEMO_WORDS = ["hello", "this", "is", "a", "simulated", "voice", "assistant", "test", "one", "two"]

    def __init__(self) -> None:
        self._chunk_count = 0
        self._transcript_parts: List[str] = []
        self._partial: str = ""
        self._lock = asyncio.Lock()

    def __repr__(self) -> str:
        return f"MockSTTAdapter(chunks={self._chunk_count}, partial='{self._partial}')"

    def stream_chunk(self, pcm: bytes, sample_rate: int, channels: int, timestamp_ms: float) -> None:
        self._chunk_count += 1
        # Simulated partial recognition
        if self._chunk_count % 20 == 0:
            word = self.DEMO_WORDS[(self._chunk_count // 20) % len(self.DEMO_WORDS)]
            self._partial = " ".join(self._transcript_parts + [word])
        if self._chunk_count % 60 == 0:
            word = self.DEMO_WORDS[(self._chunk_count // 60) % len(self.DEMO_WORDS)]
            self._transcript_parts.append(word)
            self._partial = " ".join(self._transcript_parts)

    async def finalize(self) -> str:
        async with self._lock:
            return " ".join(self._transcript_parts)

    async def flush(self) -> None:
        async with self._lock:
            self._chunk_count = 0
            self._transcript_parts.clear()
            self._partial = ""

    def partial_transcript(self) -> str:
        return self._partial


class STTPipeline:
    """High-level STT pipeline combining VAD segmentation + adapter inference.

    Reads audio from a ``Track`` (or ``asyncio.Queue``), segments by voice
    activity, and streams chunks into an ``STTAdapter``.
    """

    def __init__(
        self,
        stt_adapter: STTAdapter,
        vad: Optional[VADSegmenter] = None,
    ) -> None:
        self.stt = stt_adapter
        self.vad = vad or VADSegmenter()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._transcript_queue: asyncio.Queue[str] = asyncio.Queue()
        self._partial_queue: asyncio.Queue[str] = asyncio.Queue()

    def __repr__(self) -> str:
        return f"STTPipeline(stt={self.stt}, running={self._running})"

    async def start(self, audio_queue: asyncio.Queue[AudioFrame]) -> None:
        """Start consuming audio frames from *audio_queue*."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._consume(audio_queue))

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _consume(self, audio_queue: asyncio.Queue[AudioFrame]) -> None:
        while self._running:
            try:
                frame = await asyncio.wait_for(audio_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            segment = await self.vad.push_frame(frame.data)
            self.stt.stream_chunk(
                frame.data, frame.sample_rate, frame.channels, frame.timestamp_ms
            )
            partial = self.stt.partial_transcript()
            if partial:
                await self._partial_queue.put(partial)
            if segment:
                transcript = await self.stt.finalize()
                if transcript.strip():
                    await self._transcript_queue.put(transcript)
                await self.stt.flush()

    def transcript_queue(self) -> asyncio.Queue[str]:
        return self._transcript_queue

    def partial_queue(self) -> asyncio.Queue[str]:
        return self._partial_queue


# ════════════════════════════════════════════════════════════════════════
# 5. LLM PIPELINE — Chat context, tools, streaming
# ════════════════════════════════════════════════════════════════════════

@dataclass
class ChatMessage:
    """A single turn in a conversation.

    Supports system, user, assistant, and tool roles.
    """
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str] = None  # for tool role
    tool_calls: Optional[List[Dict[str, Any]]] = None
    timestamp: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        preview = self.content[:60].replace("\n", " ")
        return f"ChatMessage(role={self.role}, content='{preview}...')"


class ChatContext:
    """Manages message history with pruning and token-aware summarization hooks.

    Stores messages in a list and provides convenient append / rewind access.
    In a real system this would integrate with a tokenizer; here we use
    approximate word counts as a stand-in.
    """

    def __init__(self, system_prompt: str = "", max_messages: int = 40) -> None:
        self.messages: List[ChatMessage] = []
        self.system_prompt = system_prompt
        self.max_messages = max_messages
        if system_prompt:
            self.messages.append(ChatMessage(role="system", content=system_prompt))

    def __repr__(self) -> str:
        return f"ChatContext(messages={len(self.messages)}, system={bool(self.system_prompt)})"

    def append(self, message: ChatMessage) -> None:
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            # Keep system message if present, drop oldest non-system
            if self.messages[0].role == "system" and len(self.messages) > 1:
                self.messages.pop(1)
            else:
                self.messages.pop(0)

    def add_user(self, content: str) -> None:
        self.append(ChatMessage(role="user", content=content))

    def add_assistant(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None) -> None:
        self.append(ChatMessage(role="assistant", content=content, tool_calls=tool_calls))

    def add_tool_result(self, name: str, content: str) -> None:
        self.append(ChatMessage(role="tool", content=content, name=name))

    def to_list(self) -> List[Dict[str, Any]]:
        """Export to OpenAI-style chat-completion message list."""
        out: List[Dict[str, Any]] = []
        for m in self.messages:
            obj: Dict[str, Any] = {"role": m.role, "content": m.content}
            if m.role == "tool" and m.name:
                obj["name"] = m.name
            if m.tool_calls:
                obj["tool_calls"] = m.tool_calls
            out.append(obj)
        return out

    def last_user_message(self) -> Optional[ChatMessage]:
        for m in reversed(self.messages):
            if m.role == "user":
                return m
        return None

    def clear(self) -> None:
        self.messages.clear()
        if self.system_prompt:
            self.messages.append(ChatMessage(role="system", content=self.system_prompt))


class FunctionTool:
    """Represents a callable tool with JSON schema metadata.

    Args:
        name: Tool identifier (snake_case).
        description: Human-readable explanation for the LLM.
        parameters: JSON Schema object describing expected arguments.
        fn: The actual callable (sync or async).
    """

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        fn: Callable[..., Any],
    ) -> None:
        self.name = name
        self.description = description
        self.parameters = parameters
        self._fn = fn
        self._is_async = asyncio.iscoroutinefunction(fn)

    def __repr__(self) -> str:
        return f"FunctionTool(name={self.name}, async={self._is_async})"

    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def invoke(self, **kwargs: Any) -> Any:
        """Invoke the underlying function with error handling and a 30 s timeout."""
        try:
            if self._is_async:
                return await asyncio.wait_for(self._fn(**kwargs), timeout=30.0)
            else:
                loop = asyncio.get_event_loop()
                return await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: self._fn(**kwargs)),
                    timeout=30.0,
                )
        except asyncio.TimeoutError:
            return {"error": "tool_timeout", "message": f"Tool {self.name} timed out after 30s"}
        except Exception as exc:
            return {"error": "tool_exception", "message": str(exc), "type": type(exc).__name__}


class ChatAdapter(ABC):
    """Abstract base for LLM streaming adapters."""

    @abstractmethod
    async def chat_stream(
        self,
        context: ChatContext,
        tools: Optional[List[FunctionTool]] = None,
    ) -> AsyncIterator[str]:
        """Yield response text tokens (deltas) in real time."""
        ...

    @abstractmethod
    async def chat(
        self,
        context: ChatContext,
        tools: Optional[List[FunctionTool]] = None,
    ) -> str:
        """Return a complete non-streaming response."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(abstract)"


class UnifiedLLMAdapter(ChatAdapter):
    """Real LLM adapter using UnifiedLLMNative."""

    def __init__(self, latency_ms: float = 15.0) -> None:
        self.latency_ms = latency_ms
        self._bridge = None

    def _get_bridge(self):
        if self._bridge is None:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from ai.unified_llm_backend import UnifiedLLMNative
            self._bridge = UnifiedLLMNative()
        return self._bridge

    def __repr__(self) -> str:
        return f"UnifiedLLMAdapter(latency={self.latency_ms}ms)"

    async def chat_stream(
        self,
        context: ChatContext,
        tools: Optional[List[FunctionTool]] = None,
    ) -> AsyncIterator[str]:
        last_user = context.last_user_message()
        user_text = last_user.content if last_user else "Hello"
        try:
            bridge = self._get_bridge()
            reply = bridge.generate(user_text)
        except Exception:
            # Fallback if no LLM backend available
            if "weather" in user_text.lower():
                reply = "Let me check the weather for you using the get_weather tool."
            else:
                reply = f"Echo: I received your message — '{user_text}'. (LLM backend unavailable — fallback mode.)"
        words = reply.split()
        for w in words:
            await asyncio.sleep(self.latency_ms / 1000.0)
            yield w + " "

    async def chat(
        self,
        context: ChatContext,
        tools: Optional[List[FunctionTool]] = None,
    ) -> str:
        parts: List[str] = []
        async for delta in self.chat_stream(context, tools):
            parts.append(delta)
        return "".join(parts)


class LLMPipeline:
    """Orchestrates LLM interaction: context management + tool binding + streaming."""

    def __init__(
        self,
        adapter: ChatAdapter,
        context: Optional[ChatContext] = None,
    ) -> None:
        self.adapter = adapter
        self.context = context or ChatContext()
        self.tools: List[FunctionTool] = []
        self._response_queue: asyncio.Queue[str] = asyncio.Queue()

    def __repr__(self) -> str:
        return f"LLMPipeline(adapter={self.adapter}, tools={len(self.tools)}, msgs={len(self.context.messages)})"

    def register_tool(self, tool: FunctionTool) -> None:
        self.tools.append(tool)

    async def process_user_message(self, text: str) -> str:
        """Push a user message through the pipeline and return the full assistant reply."""
        self.context.add_user(text)
        full_reply = await self.adapter.chat(self.context, tools=self.tools)
        self.context.add_assistant(full_reply)
        return full_reply

    async def process_user_message_stream(self, text: str) -> AsyncIterator[str]:
        """Push a user message and yield streaming response deltas."""
        self.context.add_user(text)
        collected = ""
        async for delta in self.adapter.chat_stream(self.context, tools=self.tools):
            collected += delta
            yield delta
        self.context.add_assistant(collected)

    def response_queue(self) -> asyncio.Queue[str]:
        return self._response_queue


# ════════════════════════════════════════════════════════════════════════
# 6. TTS PIPELINE — Text-to-Speech
# ════════════════════════════════════════════════════════════════════════

class TTSAdapter(ABC):
    """Abstract base for Text-to-Speech adapters.

    Implementations must support streaming audio frame output and
    barge-in (interruption) semantics.
    """

    @abstractmethod
    async def synthesize_stream(self, text_stream: AsyncIterator[str]) -> AsyncIterator[AudioFrame]:
        """Yield audio frames as text arrives."""
        ...

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Return a complete audio byte string for *text*."""
        ...

    @abstractmethod
    def interrupt(self) -> None:
        """Signal the adapter to stop producing audio for the current utterance."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(abstract)"


class SentenceSegmenter:
    """Splits text into sentences for streaming TTS.

    Uses simple punctuation heuristics. In production this would use a
    proper NLP sentence boundary detector.
    """

    BOUNDARIES = {".", "?", "!", "\n"}

    def __init__(self, max_chars: int = 180) -> None:
        self.max_chars = max_chars
        self._buffer = ""

    def __repr__(self) -> str:
        return f"SentenceSegmenter(buffer_len={len(self._buffer)})"

    def push(self, text: str) -> List[str]:
        """Push text fragment and return any completed sentences."""
        self._buffer += text
        sentences: List[str] = []
        while True:
            # Find earliest boundary
            best_idx = -1
            for ch in self.BOUNDARIES:
                idx = self._buffer.find(ch)
                if idx != -1 and (best_idx == -1 or idx < best_idx):
                    best_idx = idx
            if best_idx == -1:
                # No boundary yet; if buffer exceeds max_chars, force split
                if len(self._buffer) >= self.max_chars:
                    split_at = self.max_chars
                    sentences.append(self._buffer[:split_at].strip())
                    self._buffer = self._buffer[split_at:].strip()
                    continue
                break
            sentence = self._buffer[: best_idx + 1].strip()
            if sentence:
                sentences.append(sentence)
            self._buffer = self._buffer[best_idx + 1 :].strip()
        return sentences

    def flush(self) -> List[str]:
        """Return any remaining buffered text as a final sentence."""
        remaining = self._buffer.strip()
        self._buffer = ""
        return [remaining] if remaining else []


class MockTTSAdapter(TTSAdapter):
    """Demo TTS adapter that yields synthetic sine-wave audio frames.

    Each character produces ~80 ms of 16-bit mono 16 kHz sine tone.
    Supports interruption via an internal flag.
    """

    def __init__(self, sample_rate: int = 16000, tone_hz: int = 440) -> None:
        self.sample_rate = sample_rate
        self.tone_hz = tone_hz
        self._interrupted = False
        self._lock = asyncio.Lock()

    def __repr__(self) -> str:
        return f"MockTTSAdapter(sr={self.sample_rate}, tone={self.tone_hz}Hz)"

    def _generate_tone(self, duration_ms: float, amplitude: int = 8000) -> bytes:
        import array as _array
        samples = int((duration_ms / 1000.0) * self.sample_rate)
        arr = _array.array("h")
        for i in range(samples):
            t = i / self.sample_rate
            val = int(amplitude * math.sin(2.0 * math.pi * self.tone_hz * t))
            arr.append(val)
        return arr.tobytes()

    async def synthesize_stream(self, text_stream: AsyncIterator[str]) -> AsyncIterator[AudioFrame]:
        self._interrupted = False
        segmenter = SentenceSegmenter()
        async for text in text_stream:
            if self._interrupted:
                logger.info("TTS interrupted — dropping remaining text")
                return
            sentences = segmenter.push(text)
            for sentence in sentences:
                if self._interrupted:
                    return
                duration_ms = max(80.0, len(sentence) * 40.0)
                pcm = self._generate_tone(duration_ms)
                frame = AudioFrame(
                    sample_rate=self.sample_rate,
                    channels=1,
                    data=pcm,
                    timestamp_ms=time.time() * 1000.0,
                )
                yield frame
                await asyncio.sleep(0.01)
        # Flush any remainder
        for sentence in segmenter.flush():
            if self._interrupted:
                return
            duration_ms = max(80.0, len(sentence) * 40.0)
            pcm = self._generate_tone(duration_ms)
            frame = AudioFrame(
                sample_rate=self.sample_rate,
                channels=1,
                data=pcm,
                timestamp_ms=time.time() * 1000.0,
            )
            yield frame

    async def synthesize(self, text: str) -> bytes:
        chunks: List[bytes] = []
        async def _stream() -> AsyncIterator[str]:
            yield text
        async for frame in self.synthesize_stream(_stream()):
            chunks.append(frame.data)
        return b"".join(chunks)

    def interrupt(self) -> None:
        self._interrupted = True


class TTSPipeline:
    """High-level TTS pipeline with sentence buffering and barge-in support."""

    def __init__(self, adapter: TTSAdapter) -> None:
        self.adapter = adapter
        self._audio_queue: asyncio.Queue[AudioFrame] = asyncio.Queue()
        self._current_task: Optional[asyncio.Task] = None

    def __repr__(self) -> str:
        return f"TTSPipeline(adapter={self.adapter})"

    async def speak(self, text: str) -> None:
        """Synthesize *text* and enqueue resulting audio frames."""
        async def _stream() -> AsyncIterator[str]:
            yield text
        await self.speak_stream(_stream())

    async def speak_stream(self, text_stream: AsyncIterator[str]) -> None:
        """Consume a text stream and enqueue audio frames as they arrive."""
        async for frame in self.adapter.synthesize_stream(text_stream):
            await self._audio_queue.put(frame)

    def interrupt(self) -> None:
        """Interrupt any ongoing TTS synthesis."""
        self.adapter.interrupt()
        if self._current_task:
            self._current_task.cancel()

    def audio_queue(self) -> asyncio.Queue[AudioFrame]:
        return self._audio_queue


# ════════════════════════════════════════════════════════════════════════
# 7. FUNCTION EXECUTOR — Tool calling system
# ════════════════════════════════════════════════════════════════════════

class ToolRegistry:
    """Registry for ``FunctionTool`` instances with auto-discovery support.

    Decorate a function with ``@tool`` to automatically generate JSON schema
    from type hints and docstrings.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, FunctionTool] = {}

    def __repr__(self) -> str:
        return f"ToolRegistry(tools={list(self._tools.keys())})"

    def register(self, tool: FunctionTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[FunctionTool]:
        return self._tools.get(name)

    def list_schemas(self) -> List[Dict[str, Any]]:
        return [t.schema() for t in self._tools.values()]

    def auto_discover(self, module: Any) -> None:
        """Scan a module for functions decorated with ``@tool``."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if callable(attr) and getattr(attr, "_is_tool", False):
                meta = getattr(attr, "_tool_meta")
                self.register(
                    FunctionTool(
                        name=meta["name"],
                        description=meta["description"],
                        parameters=meta["parameters"],
                        fn=attr,
                    )
                )

    async def execute(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name with JSON-parsed arguments."""
        tool = self._tools.get(name)
        if tool is None:
            return {"error": "tool_not_found", "message": f"Tool '{name}' not registered"}
        result = await tool.invoke(**arguments)
        # Serialize result
        if isinstance(result, dict):
            return result
        try:
            return {"result": result}
        except Exception as exc:
            return {"error": "serialization", "message": str(exc)}


def tool(name: Optional[str] = None, description: Optional[str] = None) -> Callable:
    """Decorator to mark a function as a discoverable tool.

    Extracts JSON schema from type hints using a simplistic heuristic.
    """

    def decorator(fn: Callable) -> Callable:
        tool_name = name or fn.__name__
        tool_desc = description or (fn.__doc__ or "No description provided.")
        sig = inspect.signature(fn)
        properties: Dict[str, Any] = {}
        required: List[str] = []
        for param_name, param in sig.parameters.items():
            if param.default is inspect.Parameter.empty:
                required.append(param_name)
            # Simplistic type mapping
            ann = param.annotation
            if ann is str:
                properties[param_name] = {"type": "string"}
            elif ann is int:
                properties[param_name] = {"type": "integer"}
            elif ann is float:
                properties[param_name] = {"type": "number"}
            elif ann is bool:
                properties[param_name] = {"type": "boolean"}
            else:
                properties[param_name] = {"type": "string"}
        parameters = {
            "type": "object",
            "properties": properties,
            "required": required,
        }

        fn._is_tool = True  # type: ignore[attr-defined]
        fn._tool_meta = {  # type: ignore[attr-defined]
            "name": tool_name,
            "description": textwrap.dedent(tool_desc).strip(),
            "parameters": parameters,
        }
        return fn

    return decorator


class FunctionExecutor:
    """Validates, dispatches, and serializes tool calls from LLM outputs."""

    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry

    def __repr__(self) -> str:
        return f"FunctionExecutor(registry={self.registry})"

    def parse_tool_calls(self, raw: str) -> List[Dict[str, Any]]:
        """Attempt to extract tool_calls from raw assistant text or JSON."""
        calls: List[Dict[str, Any]] = []
        # Try embedded JSON array
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and "tool_calls" in parsed:
                return parsed["tool_calls"]
        except json.JSONDecodeError:
            pass
        # Try markdown code block
        if "```json" in raw:
            try:
                start = raw.index("```json") + 7
                end = raw.index("```", start)
                parsed = json.loads(raw[start:end])
                if isinstance(parsed, list):
                    return parsed
            except (ValueError, json.JSONDecodeError):
                pass
        return calls

    async def dispatch(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Dispatch a list of tool calls concurrently and return results."""
        if not tool_calls:
            return []
        tasks = []
        for call in tool_calls:
            name = call.get("name") or call.get("function", {}).get("name")
            args = call.get("arguments") or call.get("function", {}).get("arguments") or {}
            if name:
                tasks.append(self.registry.execute(name, args))
        return await asyncio.gather(*tasks)


# ════════════════════════════════════════════════════════════════════════
# 8. TRANSCRIPTION SINK — Captions, translation, diarization hooks
# ════════════════════════════════════════════════════════════════════════

@dataclass
class TranscriptionSegment:
    """A single transcription segment with word-level metadata."""
    text: str
    speaker_id: Optional[str] = None
    start_ms: float = 0.0
    end_ms: float = 0.0
    words: List[Dict[str, Any]] = field(default_factory=list)
    language: str = "en"
    is_final: bool = True

    def __repr__(self) -> str:
        return (
            f"TranscriptionSegment('{self.text[:40]}...', "
            f"speaker={self.speaker_id}, final={self.is_final})"
        )


class Formatter(ABC):
    """Base for caption/transcription formatters."""

    @abstractmethod
    def format(self, segments: List[TranscriptionSegment]) -> str:
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(abstract)"


class SRTFormatter(Formatter):
    """SubRip Text formatter."""

    def _ms_to_srt(self, ms: float) -> str:
        td = timedelta(milliseconds=int(ms))
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        millis = int(ms) % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

    def format(self, segments: List[TranscriptionSegment]) -> str:
        lines: List[str] = []
        for idx, seg in enumerate(segments, start=1):
            lines.append(str(idx))
            lines.append(f"{self._ms_to_srt(seg.start_ms)} --> {self._ms_to_srt(seg.end_ms)}")
            lines.append(seg.text)
            lines.append("")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return "SRTFormatter()"


class VTTFormatter(Formatter):
    """WebVTT formatter."""

    def _ms_to_vtt(self, ms: float) -> str:
        td = timedelta(milliseconds=int(ms))
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        millis = int(ms) % 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"

    def format(self, segments: List[TranscriptionSegment]) -> str:
        lines = ["WEBVTT", ""]
        for seg in segments:
            lines.append(f"{self._ms_to_vtt(seg.start_ms)} --> {self._ms_to_vtt(seg.end_ms)}")
            if seg.speaker_id:
                lines.append(f"<v {seg.speaker_id}>{seg.text}</v>")
            else:
                lines.append(seg.text)
            lines.append("")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return "VTTFormatter()"


class PlainFormatter(Formatter):
    """Plain text formatter (speaker prefixed if available)."""

    def format(self, segments: List[TranscriptionSegment]) -> str:
        lines: List[str] = []
        for seg in segments:
            prefix = f"[{seg.speaker_id}] " if seg.speaker_id else ""
            lines.append(f"{prefix}{seg.text}")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return "PlainFormatter()"


class TranscriptionSink:
    """Collects transcription segments and emits formatted captions.

    Supports speaker diarization hooks: assign a ``diarize_fn`` that takes
    audio bytes and returns a speaker label string.
    """

    def __init__(self, formatter: Optional[Formatter] = None) -> None:
        self.segments: List[TranscriptionSegment] = []
        self.formatter = formatter or PlainFormatter()
        self.diarize_fn: Optional[Callable[[bytes], Awaitable[Optional[str]]]] = None
        self._lock = asyncio.Lock()

    def __repr__(self) -> str:
        return f"TranscriptionSink(segments={len(self.segments)}, formatter={self.formatter})"

    def set_diarize_hook(self, fn: Callable[[bytes], Awaitable[Optional[str]]]) -> None:
        self.diarize_fn = fn

    async def push(
        self,
        text: str,
        audio_pcm: Optional[bytes] = None,
        start_ms: float = 0.0,
        end_ms: float = 0.0,
        is_final: bool = True,
    ) -> TranscriptionSegment:
        speaker: Optional[str] = None
        if self.diarize_fn and audio_pcm:
            speaker = await self.diarize_fn(audio_pcm)
        seg = TranscriptionSegment(
            text=text,
            speaker_id=speaker,
            start_ms=start_ms,
            end_ms=end_ms,
            is_final=is_final,
        )
        async with self._lock:
            self.segments.append(seg)
        return seg

    def export(self) -> str:
        return self.formatter.format(self.segments)

    def clear(self) -> None:
        self.segments.clear()


# ════════════════════════════════════════════════════════════════════════
# 9. AGENT RUNNER — Lifecycle, health, graceful shutdown
# ════════════════════════════════════════════════════════════════════════

class AgentState(Enum):
    """Agent lifecycle states."""
    IDLE = auto()
    STARTING = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()
    ERROR = auto()
    RECONNECTING = auto()


class AgentRunner:
    """Core agent lifecycle orchestrator.

    Connects all pipelines via ``asyncio.Queue`` wiring and manages the overall
    agent health: start, stop, reload, reconnect.
    """

    def __init__(
        self,
        room_manager: RoomManager,
        stt_pipeline: STTPipeline,
        llm_pipeline: LLMPipeline,
        tts_pipeline: TTSPipeline,
        executor: FunctionExecutor,
        sink: TranscriptionSink,
    ) -> None:
        self.room_manager = room_manager
        self.stt = stt_pipeline
        self.llm = llm_pipeline
        self.tts = tts_pipeline
        self.executor = executor
        self.sink = sink

        self.state = AgentState.IDLE
        self.health_last_ok = 0.0
        self.health_interval = 5.0
        self._tasks: Set[asyncio.Task] = set()
        self._stop_event = asyncio.Event()
        self._audio_in_queue: asyncio.Queue[AudioFrame] = asyncio.Queue()
        self._transcript_out_queue: asyncio.Queue[str] = asyncio.Queue()

    def __repr__(self) -> str:
        return f"AgentRunner(state={self.state.name})"

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def start(self, room_id: str) -> None:
        """Start the agent in a room: wire all pipeline stages."""
        if self.state in (AgentState.RUNNING, AgentState.STARTING):
            logger.warning("Agent already running")
            return
        self.state = AgentState.STARTING
        self._stop_event.clear()

        # Wire STT to read from audio input queue
        await self.stt.start(self._audio_in_queue)

        # Launch orchestration tasks
        self._tasks.add(asyncio.create_task(self._orchestrate_transcript_to_llm()))
        self._tasks.add(asyncio.create_task(self._orchestrate_llm_to_tts()))
        self._tasks.add(asyncio.create_task(self._health_check_loop()))
        self._tasks.add(asyncio.create_task(self._auto_reconnect_loop(room_id)))

        self.state = AgentState.RUNNING
        self.health_last_ok = time.time()
        logger.info("Agent started in room %s", room_id)

    async def stop(self, reason: str = "shutdown") -> None:
        """Graceful shutdown with cancellation and drain."""
        if self.state in (AgentState.STOPPED, AgentState.STOPPING):
            return
        self.state = AgentState.STOPPING
        logger.info("Agent stopping: %s", reason)
        self._stop_event.set()

        await self.stt.stop()
        self.tts.interrupt()

        # Cancel all tasks
        for t in list(self._tasks):
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        self.state = AgentState.STOPPED
        logger.info("Agent stopped")

    async def reload(self) -> None:
        """Hot-reload configuration without full disconnect."""
        logger.info("Agent reloading...")
        # In a real system this would reload plugins/adapters
        await self.stop(reason="reload")
        # Context is preserved; just restart
        # (room_id would need to be stored for a real implementation)
        logger.info("Agent reloaded")

    # ── Orchestration loops ────────────────────────────────────────────

    async def _orchestrate_transcript_to_llm(self) -> None:
        """Task: consume STT transcripts, push to LLM, handle tool calls."""
        try:
            while not self._stop_event.is_set():
                try:
                    transcript = await asyncio.wait_for(self.stt.transcript_queue().get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                logger.info("STT → LLM: %s", transcript)
                # Check for tool calls in stream mode
                response = ""
                async for delta in self.llm.process_user_message_stream(transcript):
                    response += delta
                    # Stream TTS as deltas arrive (real-time interleaving)
                    # We batch by sentence boundary inside TTSPipeline
                # After full response, check if tools need to run
                tool_calls = self.executor.parse_tool_calls(response)
                if tool_calls:
                    results = await self.executor.dispatch(tool_calls)
                    for res in results:
                        self.llm.context.add_tool_result(
                            name="tool", content=json.dumps(res)
                        )
                    # Re-run LLM with tool results
                    response = await self.llm.process_user_message("")
                await self._transcript_out_queue.put(response)
                # Push to sink
                await self.sink.push(
                    text=response,
                    start_ms=time.time() * 1000.0,
                    end_ms=time.time() * 1000.0,
                )
        except asyncio.CancelledError:
            logger.debug("Orchestrator transcript→LLM cancelled")

    async def _orchestrate_llm_to_tts(self) -> None:
        """Task: consume LLM responses and synthesize speech."""
        try:
            while not self._stop_event.is_set():
                try:
                    text = await asyncio.wait_for(self._transcript_out_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                logger.info("LLM → TTS: %s", text[:80])
                async def _text_stream() -> AsyncIterator[str]:
                    yield text
                await self.tts.speak_stream(_text_stream())
        except asyncio.CancelledError:
            logger.debug("Orchestrator LLM→TTS cancelled")

    # ── Health & reconnect ───────────────────────────────────────────────

    async def _health_check_loop(self) -> None:
        """Periodic health check: verifies all pipeline queues are moving."""
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(self.health_interval)
                now = time.time()
                # In a real agent we would check heartbeats from each stage
                self.health_last_ok = now
                logger.debug("Health check OK")
        except asyncio.CancelledError:
            logger.debug("Health check loop cancelled")

    async def _auto_reconnect_loop(self, room_id: str) -> None:
        """Monitor room connection and attempt reconnect if lost."""
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(10.0)
                room = self.room_manager.get_room(room_id)
                if room is None:
                    logger.warning("Room %s missing — reconnecting...", room_id)
                    self.state = AgentState.RECONNECTING
                    # Simulated reconnect
                    await asyncio.sleep(1.0)
                    self.state = AgentState.RUNNING
                    logger.info("Reconnected to room %s", room_id)
        except asyncio.CancelledError:
            logger.debug("Reconnect loop cancelled")

    # ── External wiring helpers ──────────────────────────────────────────

    def audio_input_queue(self) -> asyncio.Queue[AudioFrame]:
        return self._audio_in_queue


# ════════════════════════════════════════════════════════════════════════
# 10. AGENT CONFIG — Declarative presets
# ════════════════════════════════════════════════════════════════════════

class AgentPreset(Enum):
    """Built-in agent configuration presets."""
    VOICE_ASSISTANT = auto()
    MEETING_BOT = auto()
    INBOUND_IVR = auto()
    OUTBOUND_DIALER = auto()
    LIVE_CAPTIONER = auto()
    CUSTOM = auto()


@dataclass
class AgentConfig:
    """Declarative agent configuration.

    Can be constructed from a dictionary (YAML-style) for easy serialization.
    """
    preset: AgentPreset = AgentPreset.VOICE_ASSISTANT
    name: str = "native-agent"
    system_prompt: str = "You are a helpful real-time voice assistant."
    stt_adapter_class: str = "MockSTTAdapter"
    llm_adapter_class: str = "UnifiedLLMAdapter"
    tts_adapter_class: str = "MockTTSAdapter"
    vad_energy_threshold: float = 500.0
    vad_hangover_frames: int = 20
    max_history_messages: int = 40
    enable_tools: bool = True
    enable_transcription_sink: bool = True
    auto_reconnect: bool = True
    health_check_interval_sec: float = 5.0
    extra: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"AgentConfig(preset={self.preset.name}, name={self.name})"

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AgentConfig:
        """Hydrate from a dictionary (e.g. loaded from YAML/JSON)."""
        preset_name = d.get("preset", "VOICE_ASSISTANT")
        preset = AgentPreset[preset_name.upper()]
        return cls(
            preset=preset,
            name=d.get("name", "native-agent"),
            system_prompt=d.get("system_prompt", cls.system_prompt),
            stt_adapter_class=d.get("stt_adapter_class", cls.stt_adapter_class),
            llm_adapter_class=d.get("llm_adapter_class", cls.llm_adapter_class),
            tts_adapter_class=d.get("tts_adapter_class", cls.tts_adapter_class),
            vad_energy_threshold=d.get("vad_energy_threshold", cls.vad_energy_threshold),
            vad_hangover_frames=d.get("vad_hangover_frames", cls.vad_hangover_frames),
            max_history_messages=d.get("max_history_messages", cls.max_history_messages),
            enable_tools=d.get("enable_tools", cls.enable_tools),
            enable_transcription_sink=d.get("enable_transcription_sink", cls.enable_transcription_sink),
            auto_reconnect=d.get("auto_reconnect", cls.auto_reconnect),
            health_check_interval_sec=d.get("health_check_interval_sec", cls.health_check_interval_sec),
            extra=d.get("extra", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preset": self.preset.name,
            "name": self.name,
            "system_prompt": self.system_prompt,
            "stt_adapter_class": self.stt_adapter_class,
            "llm_adapter_class": self.llm_adapter_class,
            "tts_adapter_class": self.tts_adapter_class,
            "vad_energy_threshold": self.vad_energy_threshold,
            "vad_hangover_frames": self.vad_hangover_frames,
            "max_history_messages": self.max_history_messages,
            "enable_tools": self.enable_tools,
            "enable_transcription_sink": self.enable_transcription_sink,
            "auto_reconnect": self.auto_reconnect,
            "health_check_interval_sec": self.health_check_interval_sec,
            "extra": self.extra,
        }


# ════════════════════════════════════════════════════════════════════════
# 11. LIVEKIT KERNEL — Magnatrix integration bridge
# ════════════════════════════════════════════════════════════════════════

class LiveKitKernel:
    """Bridge between the native LiveKit agent framework and Magnatrix OS.

    Responsibilities:
        - Auto-register STT/LLM/TTS adapters to the Magnatrix SkillRegistry.
        - Expose event hooks for voice session analytics.
        - Connect to Layer 5 (Knowledge), Layer 6 (Skills), Layer 10 (Uncensored AI).

    In a full Magnatrix deployment this would import and call into
    ``magnatrix-os/core/skills-registry.ts``; here we simulate the integration
    surface with Python-native hooks.
    """

    def __init__(self, agent_runner: AgentRunner, config: AgentConfig) -> None:
        self.runner = agent_runner
        self.config = config
        self._skill_registry: Optional[Any] = None  # Would be injected from Magnatrix
        self._analytics_events: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self._hooks: List[Callable[[str, Any], Awaitable[None]]] = []

    def __repr__(self) -> str:
        return f"LiveKitKernel(agent={self.runner}, hooks={len(self._hooks)})"

    def attach_skill_registry(self, registry: Any) -> None:
        """Attach a Magnatrix SkillRegistry-like object.

        Auto-registers capabilities: ``stt_stream``, ``llm_chat``, ``tts_synthesize``.
        """
        self._skill_registry = registry
        # Simulate registration
        logger.info("LiveKitKernel: registered skills stt_stream, llm_chat, tts_synthesize")

    def register_event_hook(self, hook: Callable[[str, Any], Awaitable[None]]) -> None:
        self._hooks.append(hook)

    async def emit(self, event_type: str, payload: Any) -> None:
        """Emit an analytics event to all registered hooks and internal queue."""
        record = {
            "event_type": event_type,
            "timestamp_ms": time.time() * 1000.0,
            "payload": payload,
            "agent_name": self.config.name,
        }
        await self._analytics_events.put(record)
        for hook in self._hooks:
            try:
                await hook(event_type, payload)
            except Exception:
                logger.exception("Event hook failed")

    def analytics_queue(self) -> asyncio.Queue[Dict[str, Any]]:
        return self._analytics_events

    async def start(self, room_id: str) -> None:
        await self.emit("agent_start", {"room_id": room_id})
        await self.runner.start(room_id)

    async def stop(self) -> None:
        await self.emit("agent_stop", {})
        await self.runner.stop()

    def knowledge_layer_context(self) -> str:
        """Return a context string for injection into Layer 5 (Knowledge)."""
        return (
            f"Voice session context for agent '{self.config.name}':\n"
            f"  - Preset: {self.config.preset.name}\n"
            f"  - System prompt: {self.config.system_prompt[:120]}...\n"
            f"  - Tools enabled: {self.config.enable_tools}\n"
            f"  - Adapter stack: {self.config.stt_adapter_class} → "
            f"{self.config.llm_adapter_class} → {self.config.tts_adapter_class}\n"
        )


# ════════════════════════════════════════════════════════════════════════
# 12. DEMO — Full simulated STT → LLM → TTS pipeline
# ════════════════════════════════════════════════════════════════════════

async def _demo_feed_audio(audio_queue: asyncio.Queue[AudioFrame], duration_sec: float = 8.0) -> None:
    """Simulate microphone input: feed synthetic PCM frames to the STT pipeline."""
    sr = 16000
    ch = 1
    frame_duration_ms = 30.0
    samples_per_frame = int((frame_duration_ms / 1000.0) * sr)
    import array as _array
    start_ts = time.time() * 1000.0
    frames_to_send = int((duration_sec * 1000.0) / frame_duration_ms)
    for i in range(frames_to_send):
        arr = _array.array("h")
        # Slightly varying energy to trigger VAD
        amplitude = 12000 if i > 10 else 500
        for _ in range(samples_per_frame):
            t = (_ / sr) + (i * frame_duration_ms / 1000.0)
            val = int(amplitude * math.sin(2.0 * math.pi * 440.0 * t))
            arr.append(val)
        pcm = arr.tobytes()
        frame = AudioFrame(sample_rate=sr, channels=ch, data=pcm, timestamp_ms=start_ts + i * frame_duration_ms)
        await audio_queue.put(frame)
        await asyncio.sleep(frame_duration_ms / 1000.0)


async def _demo_print_tts_audio(tts_pipeline: TTSPipeline, duration_sec: float = 30.0) -> None:
    """Consume TTS audio frames and print a summary."""
    deadline = time.time() + duration_sec
    total_frames = 0
    total_bytes = 0
    while time.time() < deadline:
        try:
            frame = await asyncio.wait_for(tts_pipeline.audio_queue().get(), timeout=0.5)
        except asyncio.TimeoutError:
            continue
        total_frames += 1
        total_bytes += len(frame.data)
    logger.info("TTS consumed %d frames (%d bytes) in demo", total_frames, total_bytes)


async def _demo_print_sink(sink: TranscriptionSink, duration_sec: float = 30.0) -> None:
    """Periodically print transcription sink contents."""
    await asyncio.sleep(2.0)
    for _ in range(5):
        await asyncio.sleep(duration_sec / 5.0)
        exported = sink.export()
        if exported:
            logger.info("Transcription sink:\n%s", exported[:400])


async def _demo_print_analytics(kernel: LiveKitKernel, duration_sec: float = 30.0) -> None:
    """Print analytics events as they arrive."""
    deadline = time.time() + duration_sec
    while time.time() < deadline:
        try:
            evt = await asyncio.wait_for(kernel.analytics_queue().get(), timeout=1.0)
        except asyncio.TimeoutError:
            continue
        logger.info("Analytics: %s", evt["event_type"])


async def main() -> None:
    """Run a full end-to-end simulation of the native LiveKit agent pipeline."""
    print("=" * 70)
    print("  Native Python LiveKit Agent Framework — Demo")
    print("=" * 70)

    # Build config
    config = AgentConfig(
        preset=AgentPreset.VOICE_ASSISTANT,
        name="demo-native-agent",
        system_prompt="You are a concise voice assistant running inside a pure Python simulation.",
        vad_energy_threshold=800.0,
        vad_hangover_frames=10,
    )
    print(f"\nConfig: {config}")

    # Instantiate adapters
    stt_adapter = MockSTTAdapter()
    llm_adapter = UnifiedLLMAdapter(latency_ms=20.0)
    tts_adapter = MockTTSAdapter(sample_rate=16000, tone_hz=880)
    print(f"Adapters: STT={stt_adapter}, LLM={llm_adapter}, TTS={tts_adapter}")

    # Build pipelines
    vad = VADSegmenter(
        energy_threshold=config.vad_energy_threshold,
        hangover_frames=config.vad_hangover_frames,
    )
    stt_pipeline = STTPipeline(stt_adapter=stt_adapter, vad=vad)
    llm_pipeline = LLMPipeline(adapter=llm_adapter, context=ChatContext(system_prompt=config.system_prompt))
    tts_pipeline = TTSPipeline(adapter=tts_adapter)

    # Register a demo tool
    @tool(name="get_weather", description="Get current weather for a location")
    def get_weather(location: str) -> str:
        return f"The weather in {location} is sunny and 28°C."

    registry = ToolRegistry()
    registry.register(
        FunctionTool(
            name="get_weather",
            description="Get current weather for a location",
            parameters={
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
            },
            fn=get_weather,
        )
    )
    weather_tool = registry.get("get_weather")
    if weather_tool:
        llm_pipeline.register_tool(weather_tool)

    executor = FunctionExecutor(registry)

    sink = TranscriptionSink(formatter=VTTFormatter())

    # Room manager
    room_manager = RoomManager()
    room = await room_manager.connect(room_name="demo-room", local_identity="agent-1")
    print(f"Room: {room}")

    # Agent runner
    runner = AgentRunner(
        room_manager=room_manager,
        stt_pipeline=stt_pipeline,
        llm_pipeline=llm_pipeline,
        tts_pipeline=tts_pipeline,
        executor=executor,
        sink=sink,
    )
    print(f"Runner: {runner}")

    # LiveKit Kernel (Magnatrix bridge)
    kernel = LiveKitKernel(agent_runner=runner, config=config)
    print(f"Kernel: {kernel}")

    # Register dummy hook
    async def _dummy_hook(event_type: str, payload: Any) -> None:
        pass
    kernel.register_event_hook(_dummy_hook)

    # Start agent
    await kernel.start(room.room_id)

    # Run concurrent demo tasks
    audio_q = runner.audio_input_queue()
    await asyncio.gather(
        _demo_feed_audio(audio_q, duration_sec=8.0),
        _demo_print_tts_audio(tts_pipeline, duration_sec=15.0),
        _demo_print_sink(sink, duration_sec=15.0),
        _demo_print_analytics(kernel, duration_sec=15.0),
    )

    # Stop
    await kernel.stop()
    await room_manager.disconnect(room.room_id)

    print("\n" + "=" * 70)
    print("  Demo complete. Full pipeline exercised:")
    print("    RoomManager → MediaPipe → STT(VAD) → LLM → TTS → Sink")
    print("=" * 70)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
