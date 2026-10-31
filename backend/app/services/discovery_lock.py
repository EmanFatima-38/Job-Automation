from contextlib import contextmanager
import hashlib

from sqlalchemy import text
from app.database import engine


@contextmanager
def discovery_lock(key):
    """Session advisory lock held on a dedicated connection across ORM commits."""
    value = int.from_bytes(hashlib.sha256(str(key).encode()).digest()[:8], 'big', signed=True)
    with engine.connect() as conn:
        acquired = bool(conn.scalar(text('SELECT pg_try_advisory_lock(:key)'), {'key': value}))
        try:
            yield acquired
        finally:
            if acquired:
                conn.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': value})

