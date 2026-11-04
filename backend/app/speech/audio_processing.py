"""Runs only inside a killable inference process with a bounded input buffer."""

from io import BytesIO
import time


def decode_audio(data, max_seconds=30, *, include_metadata=False):
    import av
    import numpy as np

    started = time.monotonic()
    chunks = []
    count = 0
    with av.open(
        BytesIO(data),
        mode="r",
        options={"probesize": "1000000", "analyzeduration": "2000000"},
    ) as container:
        streams = list(container.streams.audio)
        if len(streams) != 1 or container.streams.video:
            raise ValueError("Audio-only recording required")
        stream = streams[0]
        metadata={'codec':stream.codec_context.name,'container':container.format.name}
        if stream.codec_context.name not in {
            "opus",
            "vorbis",
            "pcm_s16le",
            "pcm_s24le",
            "pcm_f32le",
            "aac",
            "flac",
        }:
            raise ValueError("Unsupported codec")
        if (
            stream.codec_context.channels > 2
            or stream.codec_context.sample_rate > 96000
        ):
            raise ValueError("Unsupported channel count or sample rate")
        stream.codec_context.thread_count = 1
        resampler = av.AudioResampler(format="fltp", layout="mono", rate=16000)
        for frame in container.decode(stream):
            if frame.samples > 192000 or time.monotonic() - started > 8:
                raise ValueError("Decode resource limit")
            for converted in resampler.resample(frame):
                samples = converted.to_ndarray().reshape(-1)
                count += samples.size
                if count > max_seconds * 16000:
                    raise ValueError("Recording exceeds duration limit")
                if not np.isfinite(samples).all():
                    raise ValueError("Invalid audio samples")
                chunks.append(samples.copy())
        for converted in resampler.resample(None):
            samples = converted.to_ndarray().reshape(-1)
            count += samples.size
            chunks.append(samples.copy())
    if not chunks or count < 1600 or count > max_seconds * 16000:
        raise ValueError("Recording is empty, too short or too long")
    audio = np.concatenate(chunks).astype("float32")
    if not np.isfinite(audio).all():
        raise ValueError("Invalid audio samples")
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(audio**2)))
    quality = []
    if peak < 0.008 or rms < 0.002:
        quality.append("silence_or_very_quiet")
    if float(np.mean(np.abs(audio) >= 0.99)) > 0.02:
        quality.append("clipping")
    result=(audio, round(len(audio) / 16), quality)
    return (*result,metadata) if include_metadata else result
