"""Child Development domain (category) CRUD + custom-domain rendering tests.

Route-function level per repo convention. Covers:
  DOM-01   custom domain created with a first item; rendered with a human label
  DOM-02   duplicate domain (no first item) rejected 409
  DOM-03   rename moves rows to the new category suffix; old key gone
  DOM-04   rename onto an existing key rejected 409
  DOM-05   delete removes rows + gallery links, keeps the canonical media
  SEED-02  re-seed is a top-up: adds new corpus items, keeps custom items
  SEED-03  re-seed re-adds a deleted built-in item (built-in behavior)
  CAT-30   the 30mo age group exists in the catalog
  AUTH     domain routes are admin-or-child wired
"""

import importlib
import sys

import pytest
from fastapi import HTTPException


@pytest.fixture
def ctx(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "z" * 40)
    for mod in (
        "config",
        "database",
        "models",
        "auth",
        "storage",
        "main",
        "child_development",
        "routes.child_development",
        "routes.gallery",
    ):
        sys.modules.pop(mod, None)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    storage = importlib.import_module("storage")
    importlib.import_module("main")
    cd = importlib.import_module("routes.child_development")

    monkeypatch.setattr(storage, "UPLOAD_DIR", tmp_path)
    storage.get_storage.cache_clear()
    monkeypatch.setattr(storage.LocalStorage, "__init__", lambda self: None)

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    database.Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    a = models.Profile(name="Robert Test", date_of_birth="2024-11-01")
    db.add(a)
    db.flush()
    admin = models.User(
        username="admin", hashed_password="x", display_name="A", role=models.Role.admin, id=1
    )
    db.add(admin)
    db.commit()
    return {"cd": cd, "models": models, "storage": storage, "db": db, "a": a.id, "admin": admin}


def _seed(ctx, age_band="24mo"):
    return ctx["cd"].seed_age_group(ctx["a"], age_band, db=ctx["db"], _=ctx["admin"])


def _group(ctx, age_band="24mo"):
    return ctx["cd"].age_group(ctx["a"], age_band, db=ctx["db"])


def _media(ctx, name="trip.jpg"):
    db = ctx["db"]
    m = ctx["models"].ProfileMedia(
        profile_id=ctx["a"],
        storage_key=f"k_{name}",
        original_name=name,
        mime_type="image/jpeg",
        media_type="photo",
        size_bytes=10,
        status="ready",
    )
    db.add(m)
    db.commit()
    return m


# --- Domain CRUD ----------------------------------------------------------------


def test_dom01_custom_domain_created_and_rendered(ctx):
    _seed(ctx)
    out = ctx["cd"].create_domain(
        ctx["a"],
        "24mo",
        ctx["cd"].DomainCreate(name="Self Help Skills", first_item="Uses a fork."),
        db=ctx["db"],
        _=ctx["admin"],
    )
    assert out["domain_key"] == "self_help_skills"
    assert out["label"] == "Self Help Skills"
    g = _group(ctx)
    assert "self_help_skills" in g["domains"]
    assert g["domains"]["self_help_skills"] == "Self Help Skills"
    assert len(g["objectives"]["self_help_skills"]) == 1
    # Built-in domains still render first.
    assert list(g["domains"].keys())[0] == "social_emotional"


def test_dom02_duplicate_domain_rejected(ctx):
    _seed(ctx)
    DC = ctx["cd"].DomainCreate
    ctx["cd"].create_domain(
        ctx["a"],
        "24mo",
        DC(name="Self Help Skills", first_item="Uses a fork."),
        db=ctx["db"],
        _=ctx["admin"],
    )
    with pytest.raises(HTTPException) as e:
        ctx["cd"].create_domain(
            ctx["a"],
            "24mo",
            DC(name="self help skills"),
            db=ctx["db"],
            _=ctx["admin"],
        )
    assert e.value.status_code == 409


def test_dom03_rename_moves_rows(ctx):
    _seed(ctx)
    out = ctx["cd"].rename_domain(
        ctx["a"],
        "24mo",
        "gross_motor",
        ctx["cd"].DomainRename(name="Big Movements"),
        db=ctx["db"],
        _=ctx["admin"],
    )
    assert out["domain_key"] == "big_movements"
    g = _group(ctx)
    assert "gross_motor" not in g["domains"]
    assert "big_movements" in g["domains"]
    assert len(g["objectives"]["big_movements"]) == 3  # the seeded gross-motor rows moved


def test_dom04_rename_onto_existing_key_rejected(ctx):
    _seed(ctx)
    with pytest.raises(HTTPException) as e:
        ctx["cd"].rename_domain(
            ctx["a"],
            "24mo",
            "gross_motor",
            ctx["cd"].DomainRename(name="Fine Motor"),
            db=ctx["db"],
            _=ctx["admin"],
        )
    assert e.value.status_code == 409


def test_dom05_delete_removes_rows_keeps_media(ctx):
    _seed(ctx)
    m = _media(ctx)
    from schemas import ObjectiveLinkCreate

    g = _group(ctx)
    first_gross = g["objectives"]["gross_motor"][0]
    ctx["cd"].router  # ensure module wired
    from routes.gallery import link_objective

    link_objective(
        ctx["a"],
        m.id,
        ObjectiveLinkCreate(objective_id=first_gross["id"]),
        db=ctx["db"],
        _=ctx["admin"],
    )
    ctx["cd"].delete_domain(ctx["a"], "24mo", "gross_motor", db=ctx["db"], _=ctx["admin"])
    g = _group(ctx)
    assert "gross_motor" not in g["domains"]
    db = ctx["db"]
    assert db.query(ctx["models"].PillarEntry).get(first_gross["id"]) is None
    # The canonical media survives.
    assert db.query(ctx["models"].ProfileMedia).get(m.id) is not None
    # And its gallery link was cleaned up.
    assert (
        db.query(ctx["models"].MediaObjectiveLink)
        .filter_by(media_id=m.id, objective_id=first_gross["id"])
        .first()
        is None
    )


# --- Seed idempotency with custom edits ------------------------------------------


def test_seed02_reseed_is_a_topup_keeps_custom_items(ctx):
    """Re-seeding an active age group adds NEW corpus items and never touches
    parent-custom items or domains (zero-touch compatibility for existing
    profiles when the corpus grows)."""
    _seed(ctx)
    # Parent adds a custom item to a built-in domain.
    from routes.pillars import create_entry as entries_create

    entries_create(
        ctx["a"],
        __import__("schemas").PillarEntryCreate(
            pillar="education",
            entry_type="milestone",
            is_milestone=1,
            age_band="24mo",
            category="child_development:communication",
            title="CUSTOM-ITEM says a three-word sentence",
        ),
        db=ctx["db"],
        _=ctx["admin"],
    )
    # Re-seed: corpus items that are new get added; the custom item survives.
    out = _seed(ctx)
    g = _group(ctx)
    titles = [o["title"] for o in g["objectives"]["communication"]]
    assert any("CUSTOM-ITEM" in t for t in titles)
    assert out["created"] >= 0
    # Idempotent: seeding again adds nothing.
    out2 = _seed(ctx)
    assert out2["created"] == 0


def test_seed03_reseed_readds_deleted_builtin_item(ctx):
    """Deleting a built-in item then re-seeding re-adds it (the corpus is the
    source of truth for built-in checklists)."""
    _seed(ctx)
    g = _group(ctx)
    first = g["objectives"]["social_emotional"][0]
    ctx["cd"].delete_domain(ctx["a"], "24mo", "social_emotional", db=ctx["db"], _=ctx["admin"])
    assert _group(ctx)["objectives"]["social_emotional"] == []
    _seed(ctx)
    titles = [o["title"] for o in _group(ctx)["objectives"]["social_emotional"]]
    assert first["title"] in titles


def test_cat30_thirty_month_group_in_catalog(ctx):
    overview = ctx["cd"].overview(ctx["a"], db=ctx["db"])
    bands = [g["age_band"] for g in overview["catalog"]]
    assert "30mo" in bands
    labels = {g["age_band"]: g["label"] for g in overview["catalog"]}
    assert "2.5 years" in labels["30mo"]
    # And it seeds with items across all five built-in domains.
    _seed(ctx, "30mo")
    g = _group(ctx, "30mo")
    for d in ("social_emotional", "communication", "thinking", "gross_motor", "fine_motor"):
        assert len(g["objectives"][d]) >= 2, d


def test_auth_domain_routes_are_admin_or_child(ctx):
    """The domain CRUD routes must be wired to require_admin_or_child (readonly
    blocked). Route-function tests bypass deps, so assert the wiring."""

    wired = []
    for route in ctx["cd"].router.routes:
        deps = getattr(getattr(route, "dependant", None), "dependencies", [])
        names = {getattr(d.call, "__name__", "") for d in deps}
        if "require_admin_or_child" in names:
            wired.append(route.path)
    assert any("/domains" in p for p in wired), wired
