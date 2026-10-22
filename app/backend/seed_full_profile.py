#!/usr/bin/env python3
"""Programmatically fill a profile with realistic data across EVERY feature.

A reusable dev/robustness tool: it drives the real HTTP API (same paths the UI
uses), so it also exercises auth, validation, and storage end-to-end. Uploads
real image/PDF artifacts from a folder so attachments and avatars are populated.

Usage:
    python seed_full_profile.py \
        --base-url http://127.0.0.1:8011 \
        --admin-user admin --admin-pass changeme \
        --name "Test Child" --dob 2015-06-01 \
        --artifacts ~/Downloads --max-files 3

Requires `requests` (dev-only; in requirements-test.txt). Run it from the test
virtualenv, e.g.:
    .venv-test/bin/python seed_full_profile.py --admin-user admin --admin-pass ...
"""

from __future__ import annotations

import argparse
import mimetypes
import sys
from pathlib import Path

try:
    import requests  # type: ignore[import-untyped]
except ImportError:
    sys.exit("This tool needs `requests`: pip install requests")

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
DOC_EXTS = {".pdf", ".mp4"}


def _login(base: str, user: str, pw: str) -> str:
    r = requests.post(f"{base}/api/auth/login", json={"username": user, "password": pw}, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]


def _pick_files(folder: Path, exts: set[str], n: int) -> list[Path]:
    found = [p for p in sorted(folder.iterdir()) if p.is_file() and p.suffix.lower() in exts]
    return found[:n]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="http://127.0.0.1:8011")
    ap.add_argument("--admin-user", required=True)
    ap.add_argument("--admin-pass", required=True)
    ap.add_argument("--name", default="Seed Child")
    ap.add_argument("--dob", default="2015-06-01")
    ap.add_argument("--artifacts", default=None, help="folder of images/PDFs to upload")
    ap.add_argument("--max-files", type=int, default=3)
    args = ap.parse_args()

    base = args.base_url.rstrip("/")
    tok = _login(base, args.admin_user, args.admin_pass)
    h = {"Authorization": f"Bearer {tok}"}
    s = requests.Session()
    s.headers.update(h)

    # 1) Profile (auto-seeds milestones + bounties).
    p = s.post(
        f"{base}/api/profiles/", json={"name": args.name, "date_of_birth": args.dob}, timeout=30
    )
    p.raise_for_status()
    pid = p.json()["id"]
    print(f"created profile {pid} ({args.name})")

    art = Path(args.artifacts).expanduser() if args.artifacts else None
    images = _pick_files(art, IMAGE_EXTS, args.max_files) if art and art.is_dir() else []
    docs = _pick_files(art, DOC_EXTS, args.max_files) if art and art.is_dir() else []

    # 2) Avatar upload (first image).
    if images:
        img = images[0]
        ct = mimetypes.guess_type(img.name)[0] or "image/jpeg"
        with img.open("rb") as fh:
            r = s.post(
                f"{base}/api/profiles/{pid}/avatar", files={"file": (img.name, fh, ct)}, timeout=60
            )
        print(f"  avatar: {img.name} -> {r.status_code}")

    # 3) A custom milestone/entry, then attach files to it (events).
    e = s.post(
        f"{base}/api/profiles/{pid}/entries/",
        json={
            "pillar": "heritage",
            "title": "Seed: documented a family story",
            "content": "With photos/scans.",
            "age_band": "6-12",
            "is_milestone": True,
        },
        timeout=30,
    )
    if e.status_code in (200, 201):
        eid = e.json()["id"]
        files = [
            (
                "files",
                (
                    f.name,
                    f.open("rb"),
                    mimetypes.guess_type(f.name)[0] or "application/octet-stream",
                ),
            )
            for f in (images[1:] + docs)[: args.max_files]
        ]
        if files:
            r = s.post(
                f"{base}/api/profiles/{pid}/entries/{eid}/attachments/", files=files, timeout=120
            )
            print(f"  attachments on entry {eid}: {len(files)} -> {r.status_code}")
            for _, (_, fh, _) in files:
                fh.close()

    # 4) Behavior incident + score.
    s.post(
        f"{base}/api/profiles/{pid}/incidents",
        json={
            "trait": "honesty",
            "positive": 1,
            "description": "Seed: told the truth",
            "date": args.dob,
        },
        timeout=30,
    )
    s.post(
        f"{base}/api/profiles/{pid}/behavior",
        json={
            "week_of": args.dob,
            "integrity": 4,
            "honesty": 5,
            "responsibility": 4,
            "respect": 4,
            "school_effort": 3,
            "citizenship": 4,
            "notes": "Seed week",
        },
        timeout=30,
    )

    # 5) Bounty + log.
    b = s.post(
        f"{base}/api/profiles/{pid}/bounties",
        json={
            "tier": "bronze",
            "title": "Seed: tidy the bookshelf",
            "reward_amount": 200,
            "age_band": "6-12",
        },
        timeout=30,
    )
    if b.status_code in (200, 201):
        bid = b.json()["id"]
        s.post(
            f"{base}/api/profiles/{pid}/bounties/{bid}/logs",
            json={"author": "parent", "entry_type": "note", "content": "Seed log entry"},
            timeout=30,
        )

    # 6) Wishlist.
    s.post(
        f"{base}/api/profiles/{pid}/wishlist",
        json={"title": "Seed: new bike", "cost_cents": 12000, "priority": 2},
        timeout=30,
    )

    # 7) Fund + transaction.
    f = s.post(
        f"{base}/api/profiles/{pid}/funds/",
        json={"name": "Seed: car fund", "starting_balance": 1000000},
        timeout=30,
    )
    if f.status_code in (200, 201):
        fid = f.json()["id"]
        s.post(
            f"{base}/api/profiles/{pid}/funds/{fid}/transactions",
            json={"amount": 25000, "description": "Seed: insurance", "date": args.dob},
            timeout=30,
        )

    # 8) Discernment journal (child-private) + a parent note.
    s.post(
        f"{base}/api/profiles/{pid}/discernment/",
        json={"category": "faith", "title": "Seed reflection", "reflection": "A seeded thought."},
        timeout=30,
    )

    # 9) Lesson + response.
    les = s.post(
        f"{base}/api/profiles/{pid}/lessons/",
        json={"title": "Seed lesson", "transcript": "Seed transcript body."},
        timeout=30,
    )
    if les.status_code in (200, 201):
        lid = les.json()["id"]
        s.post(
            f"{base}/api/profiles/{pid}/lessons/{lid}/responses",
            json={"response_type": "rebrief", "content": "Seed rebrief."},
            timeout=30,
        )

    print(f"done — profile {pid} populated across all features")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
