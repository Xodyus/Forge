# Appendix E - Framed Control Protocol Skeleton

## 371. Frame Header

The control protocol should remain small. Dataset and artifact bytes normally move through immutable files or an explicitly studied data path; control messages carry identifiers, descriptors, leases, status, and acknowledgements. The following 32-byte header is illustrative and should be finalized through golden fixtures before implementation.

**Table 135 --- Illustrative 32-byte control-frame header.**

  -----------------------------------------------------------------------------------------------------
  Offset          Bytes           Field            Rule
  --------------- --------------- ---------------- ----------------------------------------------------
  0               4               magic            fixed ASCII or binary constant, e.g. `FRGE`

  4               1               major_version    incompatible changes require explicit rejection

  5               1               minor_version    negotiated capabilities within major version

  6               2               message_type     unsigned registered type code

  8               2               flags            known bits only; unknown required bits rejected

  10              2               header_bytes     must equal supported value in v1

  12              4               payload_bytes    validated against per-type and global maximum

  16              8               request_id       correlates request/response and duplicate handling

  24              4               payload_crc32c   optional corruption detection, not authentication

  28              4               reserved         zero in v1
  -----------------------------------------------------------------------------------------------------

## 372. Message Registry

**Table 136 --- Control-protocol message registry.**

  -----------------------------------------------------------------------------------------------------
  Code            Message           Sender          Core fields
  --------------- ----------------- --------------- ---------------------------------------------------
  1               HELLO             both            supported versions, instance ID, nonce, features

  2               HELLO_ACK         coordinator     selected version, limits, session ID

  3               REGISTER_WORKER   worker          worker ID, host, process, slots, capabilities

  4               REGISTER_ACK      coordinator     accepted state, heartbeat interval, policy

  5               POLL_WORK         worker          session ID, free slots, request identity

  6               TASK_ASSIGNMENT   coordinator     run/task/attempt/epoch, descriptors, deadline

  7               NO_WORK           coordinator     retry delay, coordinator state

  8               ATTEMPT_STARTED   worker          attempt and epoch, process metadata

  9               HEARTBEAT         worker          attempt epochs, progress, resources, queue state

  10              HEARTBEAT_ACK     coordinator     renewed deadlines and cancellation commands

  11              ATTEMPT_STAGED    worker          artifact descriptor, metrics, result schema

  12              COMMIT_ACK        coordinator     committed or already committed result identity

  13              COMMIT_REJECT     coordinator     stale, cancelled, invalid, or conflicting reason

  14              ATTEMPT_FAILED    worker          typed error, exit status, retry hint, metrics

  15              CANCEL_ATTEMPT    coordinator     attempt, epoch, reason, grace deadline

  16              DRAIN_WORKER      coordinator     stop admission and optionally cancel active work

  17              STATUS_REQUEST    either          bounded query and pagination token

  18              STATUS_RESPONSE   either          bounded status payload and continuation

  19              ERROR             either          stable error code, request ID, bounded diagnostic

  20              GOODBYE           either          reason and last known sequence
  -----------------------------------------------------------------------------------------------------

## 373. Protocol Limits

**Table 137 --- Starting protocol resource limits.**

  ----------------------------------------------------------------------------------------------------------------------------------------
  Limit                     Starting value                                 Behavior at limit
  ------------------------- ---------------------------------------------- ---------------------------------------------------------------
  Global frame payload      1 MiB                                          Reject header before allocation; close on repeated violation.

  Normal control payload    64 KiB                                         Per-type maximum usually much smaller than global maximum.

  Connection input buffer   2 MiB                                          Pause reads or close if decoder cannot make bounded progress.

  Connection output queue   4 MiB and 1,024 frames                         Apply backpressure; disconnect persistently slow peer.

  In-flight requests        256 per connection                             Reject or await capacity.

  Status page               1,000 rows or bounded bytes                    Return continuation token.

  String field              4 KiB unless narrower                          Validation error.

  Diagnostic message        1 KiB public; larger details in local bundle   Truncate with marker and byte count.

  Connection count          configured local bound                         Reject new connections and emit metric.
  ----------------------------------------------------------------------------------------------------------------------------------------

## 374. Incremental Decoder Skeleton

    from __future__ import annotations

    from dataclasses import dataclass
    import struct
    from typing import Final

    MAGIC: Final[bytes] = b"FRGE"
    HEADER = struct.Struct("<4sBBHHHIQII")
    HEADER_BYTES: Final[int] = HEADER.size
    MAX_PAYLOAD_BYTES: Final[int] = 1024 * 1024


    class ProtocolError(Exception):
        def __init__(self, code: str, message: str) -> None:
            super().__init__(message)
            self.code = code


    @dataclass(frozen=True, slots=True)
    class Frame:
        major: int
        minor: int
        message_type: int
        flags: int
        request_id: int
        payload_crc32c: int
        payload: bytes


    class FrameDecoder:
        def __init__(
            self,
            *,
            supported_major: int,
            max_payload_bytes: int = MAX_PAYLOAD_BYTES,
        ) -> None:
            if max_payload_bytes <= 0:
                raise ValueError("max payload must be positive")
            self._supported_major = supported_major
            self._max_payload = max_payload_bytes
            self._buffer = bytearray()
            self._expected_payload: int | None = None
            self._pending_header: tuple[int, ...] | None = None

        @property
        def buffered_bytes(self) -> int:
            return len(self._buffer)

        def feed(self, chunk: bytes | bytearray | memoryview) -> list[Frame]:
            if chunk:
                self._buffer.extend(chunk)
            frames: list[Frame] = []

            while True:
                if self._pending_header is None:
                    if len(self._buffer) < HEADER_BYTES:
                        break
                    header_bytes = bytes(self._buffer[:HEADER_BYTES])
                    del self._buffer[:HEADER_BYTES]
                    unpacked = HEADER.unpack(header_bytes)
                    (
                        magic,
                        major,
                        minor,
                        message_type,
                        flags,
                        header_bytes_value,
                        payload_bytes,
                        request_id,
                        payload_crc32c,
                        reserved,
                    ) = unpacked

                    if magic != MAGIC:
                        raise ProtocolError("BAD_MAGIC", "invalid frame magic")
                    if major != self._supported_major:
                        raise ProtocolError(
                            "UNSUPPORTED_MAJOR",
                            f"unsupported major protocol version: {major}",
                        )
                    if header_bytes_value != HEADER_BYTES:
                        raise ProtocolError(
                            "BAD_HEADER_SIZE",
                            f"unsupported header size: {header_bytes_value}",
                        )
                    if reserved != 0:
                        raise ProtocolError("RESERVED_NONZERO", "reserved field is nonzero")
                    if payload_bytes > self._max_payload:
                        raise ProtocolError(
                            "FRAME_TOO_LARGE",
                            f"payload {payload_bytes} exceeds {self._max_payload}",
                        )

                    self._pending_header = (
                        major,
                        minor,
                        message_type,
                        flags,
                        request_id,
                        payload_crc32c,
                    )
                    self._expected_payload = payload_bytes

                assert self._expected_payload is not None
                if len(self._buffer) < self._expected_payload:
                    break

                payload = bytes(self._buffer[: self._expected_payload])
                del self._buffer[: self._expected_payload]
                (
                    major,
                    minor,
                    message_type,
                    flags,
                    request_id,
                    payload_crc32c,
                ) = self._pending_header

                # Validate CRC here when enabled by negotiated flags.
                frames.append(
                    Frame(
                        major=major,
                        minor=minor,
                        message_type=message_type,
                        flags=flags,
                        request_id=request_id,
                        payload_crc32c=payload_crc32c,
                        payload=payload,
                    )
                )
                self._pending_header = None
                self._expected_payload = None

            return frames

## 375. Encoder Skeleton

    import zlib


    def encode_frame(
        *,
        major: int,
        minor: int,
        message_type: int,
        flags: int,
        request_id: int,
        payload: bytes,
        max_payload_bytes: int = MAX_PAYLOAD_BYTES,
    ) -> bytes:
        if not 0 <= message_type <= 0xFFFF:
            raise ValueError("message type out of range")
        if not 0 <= flags <= 0xFFFF:
            raise ValueError("flags out of range")
        if not 0 <= request_id <= 0xFFFFFFFFFFFFFFFF:
            raise ValueError("request ID out of range")
        if len(payload) > max_payload_bytes:
            raise ValueError("payload exceeds configured maximum")

        checksum = zlib.crc32(payload) & 0xFFFFFFFF
        header = HEADER.pack(
            MAGIC,
            major,
            minor,
            message_type,
            flags,
            HEADER_BYTES,
            len(payload),
            request_id,
            checksum,
            0,
        )
        return header + payload

## 376. Bounded Async Writer

    import asyncio
    from collections.abc import Awaitable, Callable


    class ConnectionClosed(RuntimeError):
        pass


    class BoundedFrameWriter:
        def __init__(
            self,
            send_bytes: Callable[[bytes], Awaitable[None]],
            *,
            max_frames: int,
            max_bytes: int,
        ) -> None:
            self._send_bytes = send_bytes
            self._queue: asyncio.Queue[bytes | None] = asyncio.Queue(max_frames)
            self._max_bytes = max_bytes
            self._queued_bytes = 0
            self._closed = False
            self._condition = asyncio.Condition()

        async def put(self, frame: bytes) -> None:
            if len(frame) > self._max_bytes:
                raise ValueError("single frame exceeds writer byte bound")
            async with self._condition:
                await self._condition.wait_for(
                    lambda: self._closed
                    or self._queued_bytes + len(frame) <= self._max_bytes
                )
                if self._closed:
                    raise ConnectionClosed("writer is closed")
                self._queued_bytes += len(frame)
            try:
                await self._queue.put(frame)
            except BaseException:
                async with self._condition:
                    self._queued_bytes -= len(frame)
                    self._condition.notify_all()
                raise

        async def run(self) -> None:
            try:
                while True:
                    frame = await self._queue.get()
                    if frame is None:
                        return
                    try:
                        await self._send_bytes(frame)
                    finally:
                        async with self._condition:
                            self._queued_bytes -= len(frame)
                            self._condition.notify_all()
            finally:
                async with self._condition:
                    self._closed = True
                    self._condition.notify_all()

        async def close(self) -> None:
            async with self._condition:
                if self._closed:
                    return
                self._closed = True
                self._condition.notify_all()
            await self._queue.put(None)

## 377. Protocol Decoder Property Tests

    from hypothesis import given, strategies as st


    @given(
        payload=st.binary(max_size=4096),
        split_points=st.lists(
            st.integers(min_value=0, max_value=8192),
            max_size=50,
        ),
    )
    def test_decoder_is_invariant_to_chunking(
        payload: bytes,
        split_points: list[int],
    ) -> None:
        encoded = encode_frame(
            major=1,
            minor=0,
            message_type=5,
            flags=0,
            request_id=17,
            payload=payload,
        )
        points = sorted({0, len(encoded), *split_points})
        points = [p for p in points if 0 <= p <= len(encoded)]
        decoder = FrameDecoder(supported_major=1)
        frames: list[Frame] = []
        for start, end in zip(points, points[1:], strict=True):
            frames.extend(decoder.feed(encoded[start:end]))
        assert len(frames) == 1
        assert frames[0].payload == payload
        assert decoder.buffered_bytes == 0

## 378. Handshake and Compatibility Procedure

1.  Both sides begin with a short handshake timeout and a strict maximum pre-handshake buffer.
2.  The connector sends HELLO with supported major/minor ranges, instance identity, nonce, and feature set.
3.  The coordinator selects one compatible major/minor combination and returns server limits and a new session ID.
4.  If no compatible major exists, the receiver sends a bounded error when safe and closes.
5.  The worker registers durable worker identity and ephemeral process/session metadata.
6.  The coordinator validates duplicate identity policy and returns heartbeat interval, lease policy, and accepted capabilities.
7.  Only then may the worker poll for work. Messages received in the wrong session phase are rejected.
8.  Reconnect creates a new session. It does not automatically transfer authority for an old attempt; durable attempt identity and fencing epoch remain authoritative.
