"""Runtime configuration from the environment. Read once, at the edge (cli and api)."""

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    database_url: str
    s3_endpoint_url: str
    s3_bucket: str
    default_as_of: datetime  # the brief fixes "now"; the real clock would break every user
    data_dir: Path
    affected_uids_path: Path


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ.get("DATABASE_URL", "postgresql://streaks:streaks@localhost:5432/streaks"),
        s3_endpoint_url=os.environ.get("S3_ENDPOINT_URL", "http://localhost:4566"),
        s3_bucket=os.environ.get("S3_BUCKET", "jumpp-streaks"),
        default_as_of=datetime.fromisoformat(os.environ.get("STREAKS_DEFAULT_AS_OF", "2026-11-15T10:00:00+05:30")),
        data_dir=_ROOT / "data",
        affected_uids_path=_ROOT / "config" / "affected_uids.csv",
    )
