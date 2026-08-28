"""Restart the Ollama server so it picks up OLLAMA_NUM_PARALLEL=1.

Written as a FILE and not a heredoc on purpose: the path to ollama.exe is full of backslashes,
and pushing it through a shell heredoc is how this project's oldest bug arrives. The first
attempt at this did exactly that and died on a SyntaxError before running a line -- which was
lucky, because the half that would have run first was `Stop-Process`.

WHY NUM_PARALLEL=1. Ollama splits a model's context across parallel slots: with the user-scope
OLLAMA_NUM_PARALLEL=3 and config's num_ctx=12288, each slot got 4,096 -- which is exactly the
`context_length: 4096` every diagnosis in this project has been staring at for three runs and
attributing to a client. No client was asking for 4,096. The SERVER was dividing by three.

A request naming 12,288 then wants a slot that size, which is a different runner shape, which is
a rebuild. That is the reload war, and it is why the rung died: a 6 GB model being rebuilt on a
loop cannot also serve. This workload is sequential -- one pipeline, one reader -- so the three
slots bought concurrency nothing used, at the cost of a context a third the size.

The previous value is recorded in state/run36b_env_before.json with its revert command.
"""
import os
import subprocess
import sys
import time

OLLAMA = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe")
_NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def stop():
    for name in ("ollama", "llama-server"):
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        'Stop-Process -Name "%s" -Force -ErrorAction SilentlyContinue' % name],
                       capture_output=True, text=True)
    time.sleep(4)


def start():
    """Detached, so it outlives this process and inherits the new user env var."""
    if not os.path.isfile(OLLAMA):
        raise SystemExit("ollama.exe not found at %s" % OLLAMA)
    subprocess.Popen([OLLAMA, "serve"], creationflags=_NO_WIN | 0x00000008,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(8)


def alive():
    o = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-Process | Where-Object { $_.Name -match 'ollama|llama' } | "
                        "Select-Object Id,Name | Format-Table -AutoSize | Out-String"],
                       capture_output=True, text=True, errors="replace")
    return o.stdout.strip()


def main():
    print("stopping...")
    stop()
    print("starting...")
    start()
    print(alive() or "(nothing running -- start it by hand)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
