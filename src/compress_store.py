"""
Compression + content-addressed storage for generated chapters.

Tries zstandard first (better ratio, faster); falls back to gzip if the zstandard package
isn't installed so this doesn't hard-block a run over a missing optional dependency.
"""
import gzip
import hashlib
import os
import silence

try:
    import zstandard as zstd
    _HAVE_ZSTD = True
except ImportError:
    silence.note("compress_store.py:14")
    _HAVE_ZSTD = False


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def store(text: str, compressed_dir: str) -> dict:
    """
    Compress `text`, write it to compressed_dir keyed by content hash, and return
    {"hash":..., "path":..., "codec":..., "raw_bytes":..., "compressed_bytes":...}
    """
    os.makedirs(compressed_dir, exist_ok=True)
    h = content_hash(text)
    raw_bytes = text.encode("utf-8")

    if _HAVE_ZSTD:
        codec = "zstd"
        cctx = zstd.ZstdCompressor(level=19)
        blob = cctx.compress(raw_bytes)
        path = os.path.join(compressed_dir, f"{h}.zst")
    else:
        codec = "gzip"
        blob = gzip.compress(raw_bytes, compresslevel=9)
        path = os.path.join(compressed_dir, f"{h}.gz")

    with open(path, "wb") as f:
        f.write(blob)

    return {
        "hash": h,
        "path": path,
        "codec": codec,
        "raw_bytes": len(raw_bytes),
        "compressed_bytes": len(blob),
    }


def load(path: str, codec: str) -> str:
    with open(path, "rb") as f:
        blob = f.read()
    if codec == "zstd":
        if not _HAVE_ZSTD:
            raise RuntimeError("zstandard package not installed; cannot decompress .zst file")
        dctx = zstd.ZstdDecompressor()
        return dctx.decompress(blob).decode("utf-8")
    elif codec == "gzip":
        return gzip.decompress(blob).decode("utf-8")
    raise ValueError(f"unknown codec: {codec}")
