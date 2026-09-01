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
    silence.note("compress_store.py:zstd-unavailable")
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
        # SWEEP THE TEMP BEFORE RAISING. The message below names the leftover, which was honest
        # but not sufficient: the temp name carries pid and thread (deliberately, see above), so
        # repeated denials on a hot path accumulate UNIQUELY-NAMED files instead of overwriting
        # one, and nothing else in the kit ever comes back for them. Removing it loses nothing --
        # the blob is reproducible from `text`, which the caller still holds and
        # which it re-derives on retry -- `generate.py`'s `compress_store.store(text,
        # compressed_dir)` call, named rather than numbered: this said `generate.py:554`, which
        # had drifted onto generate.py's own comment about not putting line numbers in strings,
        # the joke writing itself. Order bf22c557852e.
        # Same shape as the silence.write_json leak (b464a0311775).
        # The unlink is itself guarded: failing to clean up must not replace the real error
        # (a denied replace) with a confusing one from the cleanup path.
        try:
            os.unlink(tmp)
            tmp_state = "the temp file %s was removed" % tmp
        except OSError:
            silence.note("compress_store.py:temp-unlink-denied")
            tmp_state = "the temp file %s is still on disk" % tmp
        # replace_retry() FAILS CLOSED by design (see silence.py) -- it records
        # "replace-denied:<file>" and returns False rather than raising, so nothing landed and
        # `path` does not exist yet (the temp is swept just above). The old code returned the same
        # success dict either way, so a blob that never landed was reported as stored, and
        # generate.py wrote that path straight into the catalogue as `compressed_path`
        # (the catalog[job["address"]] assignment in its generation loop -- this cited
        # generate.py:468, drifted; order bf22c557852e) for `catalog.cmd_read` to open later
        # and fail on. Raising here instead
        # of returning gives the caller (generate.py) something to catch and retry, rather than
        # a poisoned catalogue entry.
        raise RuntimeError(
            "compress_store.store(): %s could not be renamed into place after retries -- "
            "nothing landed at the content-addressed path; %s"
            % (path, tmp_state))

    return {
        "hash": h,
        "path": path,
        "codec": codec,
        "raw_bytes": len(raw_bytes),
        "compressed_bytes": len(blob),
    }


def _address_in(path: str) -> str:
    """The content hash a store path CLAIMS, or "" if the name is not a content address.

    store() names every blob `<content_hash(text)>.zst` / `.gz`, and content_hash is
    sha256(...)[:32] -- so a store path's stem is exactly 32 lowercase hex characters. Anything
    else (a hand-copied file, a path from some future naming scheme) has no address to check
    against, and load() must not invent a failure for it.
    """
    stem = os.path.splitext(os.path.basename(path))[0]
    if len(stem) == 32 and all(c in "0123456789abcdef" for c in stem):
        return stem
    return ""


def load(path: str, codec: str) -> str:
    """Read a stored blob back, VERIFYING it against the address it is filed under.

    THE FILENAME IS A CHECKSUM AND THIS FUNCTION USED NOT TO READ IT. store() computes
    content_hash(text), writes it into the name, and the loader returned the decompressed bytes
    without ever hashing them back -- declining the one property content-addressing gives away
    for free. It matters concretely: the temp-then-replace repair in store() stops NEW torn
    blobs and can do nothing about any already on disk from before it, because store() never
    revisits a path that exists. A verifying load() is the only thing that will ever find one,
    and it finds it at the moment the damage matters -- when catalog.cmd_read serves the chapter to
    a reader. Refusing loudly beats returning text that is not what was stored, which is the
    quietest corpus corruption available to this project.
    """
    with open(path, "rb") as f:
        blob = f.read()
    if codec == "zstd":
        if not _HAVE_ZSTD:
            raise RuntimeError("zstandard package not installed; cannot decompress .zst file")
        dctx = zstd.ZstdDecompressor()
        text = dctx.decompress(blob).decode("utf-8")
    elif codec == "gzip":
        text = gzip.decompress(blob).decode("utf-8")
    else:
        raise ValueError(f"unknown codec: {codec}")

    claimed = _address_in(path)
    if claimed:
        got = content_hash(text)
        if got != claimed:
            silence.note("compress_store.py:address-mismatch")
            raise RuntimeError(
                "compress_store.load(): %s decompressed to text whose content hash is %s, not "
                "the %s its own filename claims -- the blob on disk is not what was stored "
                "(a torn write, or the file was replaced). Refusing to return it."
                % (path, got, claimed))
    return text
