"""Process entry point for `uvicorn streaks.main:app`: wires real adapters from the environment."""

from streaks.api import create_app
from streaks.settings import load_settings
from streaks.storage import open_storage_when_ready
from streaks.store import open_store

_settings = load_settings()
app = create_app(
    open_store(_settings.database_url),
    open_storage_when_ready(_settings.s3_endpoint_url, _settings.s3_bucket),
    _settings.default_as_of,
)
