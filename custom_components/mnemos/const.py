from __future__ import annotations

from typing import Final

DOMAIN: Final = "mnemos"

CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_API_KEY: Final = "api_key"
CONF_USE_SSL: Final = "use_ssl"
CONF_SCAN_INTERVAL: Final = "scan_interval"

DEFAULT_HOST: Final = "mnemos-backend"
DEFAULT_PORT: Final = 8000
DEFAULT_USE_SSL: Final = False
DEFAULT_SCAN_INTERVAL: Final = 30  # seconds
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 600
DEFAULT_TIMEOUT: Final = 30  # seconds for identify upload

SERVICE_IDENTIFY: Final = "identify"
SERVICE_REFRESH: Final = "refresh"

SERVICE_FIELD_ENTITY_ID: Final = "entity_id"
SERVICE_FIELD_FILE_PATH: Final = "file_path"
SERVICE_FIELD_TIMEOUT: Final = "timeout"

ATTR_PERSONS: Final = "persons"
ATTR_UNKNOWN: Final = "unknown"
ATTR_TOOK_MS: Final = "took_ms"
ATTR_NAME: Final = "name"
ATTR_CONFIDENCE: Final = "confidence"

DATA_HEALTH: Final = "health"
DATA_MODEL: Final = "model"
DATA_LAST_IDENTIFY: Final = "last_identify"

HEALTH_KEY_STATUS: Final = "status"
HEALTH_KEY_VERSION: Final = "version"
HEALTH_KEY_MODEL: Final = "model"
HEALTH_KEY_DB: Final = "db"
HEALTH_KEY_VECTOR_DB: Final = "vector_db"
HEALTH_KEY_REINDEX_IN_PROGRESS: Final = "reindex_in_progress"
HEALTH_KEY_REINDEX_DONE: Final = "reindex_done"
HEALTH_KEY_REINDEX_TOTAL: Final = "reindex_total"
HEALTH_KEY_MODEL_LOADED: Final = "model_loaded"

MODEL_KEY_NAME: Final = "name"
MODEL_KEY_EMBEDDING_DIM: Final = "embedding_dim"
MODEL_KEY_DET_SIZE: Final = "det_size"

MANUFACTURER: Final = "Mnemos"
MODEL_NAME: Final = "Mnemos Face Recognition Backend"
