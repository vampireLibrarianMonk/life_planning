"""Seed LOCAL demo data for the Email Center (v6 Pass 5).

Run:  .venv/bin/python seed_email_demo.py   (from app/backend, dev DB)

Creates (idempotently) on the dev database:
  * a child profile "Robert Demo"
  * a completed child-development objective + a PRIVATE worries note
    (the worries note exists to demonstrate that the composer excludes it)
  * two gallery media items backed by REAL small files in uploads/
    (sample photo + sample video - "slugs" with real bytes so previews work)
  * two contacts with VERIFIED email methods: Grandma (family) + Dr. Sample
    (pediatrician) - verification is set directly (the flow itself is
    already proven live in prod)
"""

import base64
import sys
from datetime import datetime

import database
from models import Contact, ContactMethod, PillarEntry, Profile, ProfileMedia, ProfileContactLink

# A tiny valid 1x1 blue PNG (67 bytes).
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
# A minimal placeholder MP4 container stub (not playable; demo metadata only).
MP4_STUB = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 256


def main() -> None:
    db = database.SessionLocal()
    try:
        profile = db.query(Profile).filter(Profile.name == "Robert Demo").first()
        if not profile:
            profile = Profile(name="Robert Demo", date_of_birth="2024-11-09")
            db.add(profile)
            db.commit()
            db.refresh(profile)
        pid = profile.id
        print(f"profile: Robert Demo (id={pid})")

        def ensure_entry(title, category, status, content, age_band="12mo", age_years=1):
            row = (
                db.query(PillarEntry)
                .filter(PillarEntry.profile_id == pid, PillarEntry.title == title)
                .first()
            )
            if not row:
                row = PillarEntry(
                    profile_id=pid, pillar="education", entry_type="milestone",
                    title=title, category=category, status=status, content=content,
                    age_band=age_band, age_years=age_years, is_milestone=1,
                )
                db.add(row)
                db.commit()
            return row

        obj = ensure_entry(
            "Stacks three blocks",
            "child_development:motor",
            "complete",
            "Stacked three blocks without help and clapped for himself.",
        )
        ensure_entry(
            "Points to two body parts",
            "child_development:language",
            "practicing",
            "Points to nose and belly on request most of the time.",
        )
        ensure_entry(
            "Private worries (12mo)",
            "child_development_private",
            "complete",
            "PRIVATE: we are worried about his picky eating - do not email this.",
        )
        print(f"objectives seeded (incl. 1 PRIVATE worries note, id={obj.id})")

        def ensure_media(name, mime, kind, blob, observation):
            import uuid

            from storage import get_storage

            row = db.query(ProfileMedia).filter(
                ProfileMedia.profile_id == pid, ProfileMedia.original_name == name
            ).first()
            if not row:
                key = f"demo_{uuid.uuid4().hex[:8]}_{name}"
                get_storage().save(key, blob, mime)
                row = ProfileMedia(
                    profile_id=pid, storage_key=key, original_name=name,
                    mime_type=mime, media_type=kind, size_bytes=len(blob),
                    observation=observation, status="ready",
                )
                db.add(row)
                db.commit()
                db.refresh(row)
            return row

        photo = ensure_media(
            "block-tower-accomplishment.jpg", "image/jpeg", "photo", PNG_1PX,
            "Robert's first three-block tower!",
        )
        video = ensure_media(
            "first-steps-video.mp4", "video/mp4", "video", MP4_STUB,
            "First unassisted steps across the living room.",
        )
        print(f"media seeded: photo id={photo.id}, video id={video.id}")

        def ensure_contact(name, roles, addr):
            contact = db.query(Contact).filter(Contact.display_name == name).first()
            if not contact:
                contact = Contact(display_name=name, kind="individual")
                db.add(contact)
                db.flush()
                method = ContactMethod(
                    contact_id=contact.id, channel="email", address=addr,
                    verified_at=datetime.utcnow(), verification_method="code_email",
                )
                db.add(method)
                db.add(
                    ProfileContactLink(
                        profile_id=pid, contact_id=contact.id, roles=roles,
                        approved_by=1,
                    )
                )
                db.commit()
                db.refresh(contact)
            return contact

        grandma = ensure_contact("Grandma Sara (demo)", "family", "grandma@example.com")
        doctor = ensure_contact("Dr. Sample (demo)", "pediatrician", "dr.example@clinic.com")
        gm = db.query(ContactMethod).filter(ContactMethod.contact_id == grandma.id).first()
        dm = db.query(ContactMethod).filter(ContactMethod.contact_id == doctor.id).first()
        print(f"contacts seeded: grandma method={gm.id}, doctor method={dm.id}")
        print("DEMO IDS: profile=%s photo=%s video=%s objective=%s gm_method=%s dr_method=%s"
              % (pid, photo.id, video.id, obj.id, gm.id, dm.id))
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
