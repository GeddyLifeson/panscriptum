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
        cctx = zstd.ZstdCompressor(level=10)
        blob = cctx.compress(raw_bytes)
        path = os.path.join(compressed_dir, f"{h}.zst")
    else:
        codec = "gzip"
        blob = gzip.compress(raw_bytes, compresslevel=9)
        path = os.path.join(compressed_dir, f"{h}.gz")

    # LANDED, not written in place. A bare `open(path, "wb")` at the FINAL content-addressed
    # path leaves a torn blob sitting there permanently if the process dies mid-write -- and
    # because the store is keyed by content, nothing ever comes back to overwrite it unless the
    # identical text happens to be stored again. Temp-then-replace_retry is what every other
    # shared-state writer in this project already does (m55, run #19).
    #
    # THE TEMP NAME CARRIES PID AND THREAD, as `silence.write_json`'s does: two processes
    # storing the same text compute the same `h`, so a plain `path + ".tmp"` would put them on
    # the same temp file and let the loser replace the winner's target with a partial one.
    import threading
    tmp = "%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())
    with open(tmp, "wb") as f:
        f.write(blob)
    landed = silence.replace_retry(tmp, path)
    if not landed:
        # replace_retry() FAILS CLOSED by design (see silence.py) -- it records
        # "replace-denied:<file>" and returns False rather than raising, so the temp copy is
        # still sitting on disk and `path` does not exist yet. The old code returned the same
        # success dict either way, so a blob that never landed was reported as stored, and
        # generate.py wrote that path straight into the catalogue as `compressed_path`
        # (generate.py:468) for catalog.py:97 to open later and fail on. Raising here instead
        # of returning gives the caller (generate.py) something to catch and retry, rather than
        # a poisoned catalogue entry.
        raise RuntimeError(
            "compress_store.store(): %s could not be renamed into place after retries -- "
            "nothing landed at the content-addressed path; the temp file %s is still on disk"
            % (path, tmp))

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
