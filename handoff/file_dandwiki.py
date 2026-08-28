"""Correct the dandwiki diagnosis: it is not unreachable, it is a login wall.

Two open orders describe www.dandwiki.com as an unreachable host whose API "is not answering",
and one of them notes that its quarantine will never lift on its own while a 24h retry keeps
trying. Both are half right and the wrong half is the one that decides what to do about it.

Measured 2026-08-27 with a plain GET to the site's own api.php, User-Agent set:

    HTTP 403 -- "To reduce server load, we had to restrict this action to logged in users
    only. Please just make an account, log in, and then proceed!"

The API answered. It answered with a deliberate policy refusal that names its own condition, and
that distinction is the whole finding: an unreachable host is a transport problem a retry can
solve, and a login wall is an ACCOUNT DECISION that no amount of retrying will ever satisfy. The
bot rung has been retrying something that cannot succeed, and would have gone on doing so
indefinitely.

Filed at OWNER because every way forward is a person's call -- create an account and hold
credentials for it, drop the source from the roll, or accept the source as permanently
partial. A maintenance run may not decide any of those, and it certainly may not create an
account.
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))
import workorders  # noqa: E402

WHAT = (
    "www.dandwiki.com IS NOT UNREACHABLE -- IT IS A LOGIN WALL, AND THAT CHANGES THE REMEDY "
    "COMPLETELY. Two open orders (2da53c3e192f, 52cd63cee774) describe the host as unreachable "
    "with an API that 'is not answering', and one observes that its quarantine will never lift "
    "on its own while the 24h retry keeps probing. Measured directly 2026-08-27 with a plain "
    "GET to https://www.dandwiki.com/w/api.php (action=query&meta=siteinfo, User-Agent set): "
    "the server answered HTTP 403 with the message 'To reduce server load, we had to restrict "
    "this action to logged in users only. Please just make an account, log in, and then "
    "proceed!'. The API is alive and is refusing anonymous reads by policy. An unreachable host "
    "is a transport fault a retry can eventually clear; a login wall is an account decision no "
    "retry can ever satisfy, so the bot rung has been retrying something that cannot succeed "
    "and will keep doing so forever. THE DECISION IS THE OWNER'S and there are only three: "
    "(1) create a dandwiki account and give the crawler credentials, (2) drop the source from "
    "the Acquisitions Roll, or (3) accept it as permanently partial and stop probing. A "
    "maintenance run may not create accounts and may not drop a source from the roll. "
    "Recommend at minimum that the probe distinguish 403-with-a-login-message from a transport "
    "failure, so a policy refusal stops being retried as if it were a network blip."
)

EVIDENCE = {
    "probe": "GET https://www.dandwiki.com/w/api.php?action=query&meta=siteinfo&format=json",
    "status": 403,
    "server_message": ("To reduce server load, we had to restrict this action to logged in "
                       "users only. Please just make an account, log in, and then proceed!"),
    "misdiagnosis": "recorded as 'host unreachable / siteinfo returned nothing usable'",
    "why_it_matters": "a retry can clear a transport fault; it can never clear a login wall",
    "supersedes_mechanism_in": ["2da53c3e192f", "52cd63cee774"],
    "owner_options": ["create an account and hold credentials",
                      "drop the source from the roll",
                      "accept permanently partial and stop probing"],
}


def main():
    o = workorders.file_order(
        code="DANDWIKI_IS_A_LOGIN_WALL_NOT_AN_OUTAGE",
        what=WHAT, handler="OWNER", severity="MAJOR",
        where="www.dandwiki.com",
        evidence=EVIDENCE,
        found_by="maintenance-2026-08-27 direct 403 probe")
    print("filed:", o["id"], o["code"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
