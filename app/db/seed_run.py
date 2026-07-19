"""One-shot catalog seeding, run from entrypoint.sh before workers start.

Running here (once) avoids the race where every gunicorn worker would seed
concurrently and collide on unique slugs.
"""
from app.db.session import SessionLocal
from app.db.seed_catalog import seed_catalog


def main() -> None:
    db = SessionLocal()
    try:
        n = seed_catalog(db)
        print(f"[seed] catalog: {n} new roles inserted")
    finally:
        db.close()


if __name__ == "__main__":
    main()
