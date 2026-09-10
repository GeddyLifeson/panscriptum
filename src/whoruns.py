#!/usr/bin/env python3
"""Who is actually RUNNING a given script? -- asked without the probe matching itself.

WHY THIS IS A MODULE IN src/ AND NOT A ONE-LINER EACH TIME. Four times in two days a maintenance
run has written `if "mutate.py" in cmdline` and had it match THE PROBE'S OWN COMMAND LINE, because
the string being searched for is inside the `-c` source that was passed to look for it. The answer
comes back as "yes, something is running" every single time, including when nothing is, and it
comes back in the confident direction -- so the run stands down, or double-launches, or reports a
job alive that died hours ago. It is `codewatch.twins()`'s founding bug and order d9328fe1ee38's
bug, and it has now been committed by the runs that filed both of them.

The one-liner keeps being rewritten because the correct version is not a one-liner. It has to:

  * EXCLUDE ITS OWN PID. A probe is never an answer about the thing it is probing.
  * MATCH THE SCRIPT TOKEN, not a substring of the line. `--task-file .../task_mutate.txt`
    contains "mutate" and is not running mutate.py.
  * REFUSE `-m` AND `-c` OUTRIGHT. `python -c "...mutate.py..."` is not running mutate.py, and
    `python -m pyflakes src/mutate.py` is linting it. This is the arm that the hand-written
    versions always leave out, and it is the arm that produces the false positive.
  * TOKENISE THE WINDOWS WAY. `overnight._cmd_tokens` shlex-splits on slash-normalised text, so
    a quoted path with a space stays one token. Splitting on whitespace makes
    `"C:\\Program Files\\Python\\python.exe" src/mutate.py` look like it runs `Files\\Python...`.

TRI-STATE, BECAUSE AN UNREADABLE PROCESS TABLE IS NOT AN EMPTY ONE. `running()` returns None when
the enumeration itself failed, and the CLI prints UNKNOWN rather than NONE. Rendering "nobody
knows" as the confident negative an operator acts on is the fail-closed property inverted -- the
same fault `binding_health --status` was fixed for (order f1901d2178ba), and the same one
`allsweep` was fixed for earlier the same day.

    python3 src/whoruns.py mutate.py
    python3 src/whoruns.py local_agent.py --quiet   # exit 0 if any, 1 if none, 2 if unknown
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overnight as ON                                                  # noqa: E402


def script_of(tokens):
    """-> the .py this command line actually RUNS, or None.

    None for `-m` and `-c`, which is the whole point: those are the two forms whose ARGUMENTS
    routinely contain the name of the script somebody is asking about.
    """
    if not tokens:
        return None
    if "python" not in os.path.basename(tokens[0]).lower():
        return None
    for tok in tokens[1:]:
        if tok in ("-m", "-c"):
            return None
        if tok.startswith("-"):
            continue                   # -u, -O, -X... an interpreter flag, keep looking
        if tok.endswith(".py"):
            return tok
        return None                    # a bare non-flag that is not a .py: not a script run
    return None


def running(want, exclude_self=True):
    """-> [(pid, command line)] running `want`, or None if the process table was unreadable.

    `want` is compared on BASENAME, so "mutate.py", "src/mutate.py" and an absolute path all
    match the same processes.
    """
    listing = ON._proc_lines()
    if listing is None:
        return None                    # UNMEASURABLE. Not "none running".
    # `_proc_lines` HANDS BACK THE RAW STDOUT STRING, not a list of lines -- read its return
    # statement, not its name. The first draft of this function iterated it directly, which
    # iterates CHARACTERS, so every row failed the int() and the answer was a confident empty
    # list: the exact false negative this whole module exists to stop, one layer further in.
    want = os.path.basename(want)
    me = os.getpid()
    out = []
    for ln in listing.splitlines():
        pid, _, cmd = ln.partition("|")
        try:
            pid = int(pid.strip())
        except ValueError:
            continue
        if exclude_self and pid == me:
            continue                   # never count the asker
        script = script_of(ON._cmd_tokens(cmd))
        if script and os.path.basename(script) == want:
            out.append((pid, cmd.strip()))
    return out


def main():
    ap = argparse.ArgumentParser(description="who is RUNNING this script (not merely naming it)")
    ap.add_argument("script", help="e.g. mutate.py, local_agent.py, src/read.py")
    ap.add_argument("--quiet", action="store_true",
                    help="exit status only: 0 some, 1 none, 2 unreadable process table")
    a = ap.parse_args()
    hits = running(a.script)
    if hits is None:
        if not a.quiet:
            print("UNKNOWN: the process table could not be read. This is not 'none running' -- "
                  "treat it as unmeasured and do not stand down on it.")
        return 2
    if not a.quiet:
        if not hits:
            print("NONE running %s" % os.path.basename(a.script))
        else:
            print("%d process(es) RUNNING %s:" % (len(hits), os.path.basename(a.script)))
            for pid, cmd in hits:
                print("   %-7d %s" % (pid, cmd[:150]))
    return 0 if hits else 1


if __name__ == "__main__":
    sys.exit(main())
