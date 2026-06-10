"""Carga y validación de configuración (Pydantic Settings)."""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de entorno con validación al instanciar."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    environment: Literal["local", "test", "staging", "production"] = Field(
        default="local",
        description="Entorno de ejecución; `test` relaja validaciones de secretos.",
    )

    log_level: str = Field(default="INFO")

    cors_allow_origins: str = Field(
        default=(
            "http://localhost:3000,http://localhost,http://127.0.0.1:3000," "http://127.0.0.1"
        ),
    )

    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000)

    jwt_secret: str = Field(default="", repr=False)
    jwt_alg: str = Field(default="HS256")
    jwt_access_token_expires_seconds: int = Field(default=900, ge=1)
    jwt_refresh_token_expires_seconds: int = Field(default=2_592_000, ge=60)

    password_pepper: str = Field(default="", repr=False)

    auth_login_max_attempts_per_ip_per_minute: int = Field(default=30, ge=1)
    auth_login_max_attempts_per_email_per_minute: int = Field(default=15, ge=1)
    auth_failed_password_threshold: int = Field(default=5, ge=1)
    auth_lockout_base_seconds: int = Field(default=60, ge=1)
    auth_lockout_max_seconds: int = Field(default=3600, ge=1)

    app_rate_limit_enabled: bool = Field(
        default=True,
        description="Rate limit global por usuario autenticado (Redis).",
    )
    app_rate_limit_per_minute: int = Field(default=120, ge=1)
    ingest_upload_max_per_user_per_minute: int = Field(
        default=10,
        ge=1,
        description="Máximo de subidas de documentos por usuario por minuto.",
    )
    ingest_upload_max_per_kb_per_minute: int = Field(
        default=20,
        ge=1,
        description="Máximo de subidas por KB por minuto (todos los usuarios).",
    )
    rate_limit_audit_enabled: bool = Field(
        default=True,
        description="Persistir filas en rate_limit_events al devolver 429.",
    )

    fail2ban_security_log_enabled: bool = Field(
        default=True,
        description="Middleware SECURITY_ACCESS en respuestas 401/403/429 de /api.",
    )
    fail2ban_security_log_path: str = Field(
        default="",
        description="Ruta opcional a archivo (p. ej. /var/log/rag/security-access.log en Docker).",
    )

    prompt_guard_enabled: bool = Field(
        default=True,
        description="Sanitización de chunks y heurísticas anti prompt injection.",
    )
    prompt_guard_block_user_exfil: bool = Field(
        default=True,
        description="Rechazar consultas que piden secretos o el system prompt.",
    )
    prompt_guard_max_chunk_chars: int = Field(
        default=4000,
        ge=200,
        le=20_000,
        description="Tope de caracteres por snippet tras sanitizar.",
    )

    database_url: str = Field(
        default="postgresql+psycopg://rag:rag_password_local@postgres:5432/rag",
        repr=False,
    )

    redis_host: str = Field(default="redis")
    redis_port: int = Field(default=6379)

    qdrant_host: str = Field(default="qdrant")
    qdrant_port: int = Field(default=6333)
    qdrant_collection: str = Field(
        default="rag_chunks_v1",
        description="Colección global de chunks vectoriales en Qdrant.",
    )
    qdrant_enabled: bool = Field(
        default=True,
        description="Si false, se omiten upsert/delete en Qdrant (solo depuración).",
    )
    qdrant_upsert_batch_size: int = Field(default=64, ge=1, le=512)
    qdrant_timeout_seconds: float = Field(default=30.0, ge=1.0)
    qdrant_snippet_max_chars: int = Field(
        default=500,
        ge=0,
        le=4000,
        description="Máximo de caracteres del chunk en payload.text (snippet).",
    )

    ollama_host: str = Field(default="ollama")
    ollama_port: int = Field(default=11434)
    ollama_timeout_seconds: float = Field(
        default=120.0,
        ge=5.0,
        description="Timeout HTTP por petición a Ollama (chat/generate).",
    )
    ollama_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Reintentos ante errores transitorios de red/5xx.",
    )

    llm_model: str = Field(
        default="qwen2.5:7b-instruct",
        description="Modelo Ollama (tag en `ollama pull`).",
    )
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=800, ge=64, le=8192)
    llm_streaming: bool = Field(
        default=True,
        description="Preferencia global; POST /messages con stream=false ignora esto.",
    )
    llm_force_spanish: bool = Field(
        default=True,
        description="System prompt exige respuestas en español.",
    )
    chat_llm_backend: Literal["auto", "fake", "ollama"] = Field(
        default="auto",
        description="`auto`: fake en test, ollama en otros entornos.",
    )
    chat_default_top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="top_k RAG por defecto si el cliente no envía rag.top_k.",
    )
    chat_context_max_chars: int = Field(
        default=12_000,
        ge=500,
        le=100_000,
        description="Tope de caracteres del bloque de contexto en el prompt.",
    )

    socketio_enabled: bool = Field(
        default=True,
        description="Montar servidor Socket.IO junto a FastAPI.",
    )
    socketio_path: str = Field(
        default="/socket.io",
        description="Path HTTP del engine.io (Traefik debe enrutarlo al backend).",
    )
    socketio_cors_origins: str = Field(
        default="",
        description="Orígenes CORS Socket.IO (vacío = usar CORS_ALLOW_ORIGINS).",
    )

    health_http_timeout_seconds: float = Field(default=3.0)

    upload_storage_dir: str = Field(
        default="",
        description="Directorio absoluto o vacío (<raíz repo>/uploads).",
    )
    max_upload_mb: int = Field(default=50, ge=1, le=512)
    allowed_mime_types: str = Field(
        default=(
            "application/pdf,"
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
            "text/plain"
        ),
    )

    celery_broker_url: str = Field(default="", repr=False)
    celery_result_backend: str = Field(default="", repr=False)
    celery_task_always_eager: bool = Field(default=False)

    parse_timeout_seconds: float = Field(
        default=120.0,
        ge=1.0,
        description="Tiempo máximo por documento en la etapa parse (segundos).",
    )
    ocr_min_chars_per_page: int = Field(
        default=40,
        ge=0,
        description="Si el PDF tiene menos caracteres promedio por página, se marca needs_ocr.",
    )
    parser_save_artifacts: bool = Field(
        default=True,
        description="Guardar extracted/normalized en disco bajo uploads/artifacts.",
    )
    unstructured_enabled: bool = Field(
        default=False,
        description="Usar Unstructured como fallback si está instalado (pip extra).",
    )

    ocr_enabled: bool = Field(default=True, description="Habilitar OCR Tesseract en ingesta PDF.")
    ocr_max_pages: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Máximo de páginas a procesar con OCR por documento.",
    )
    ocr_tesseract_lang: str = Field(
        default="spa",
        description="Idioma Tesseract (paquete del sistema, p. ej. tesseract-ocr-spa).",
    )
    ocr_tesseract_cmd: str = Field(
        default="",
        description="Ruta al binario tesseract si no está en PATH.",
    )
    ocr_cache_enabled: bool = Field(
        default=True,
        description="Cachear texto OCR por página en uploads/.ocr_cache.",
    )
    ocr_dpi: int = Field(default=200, ge=72, le=400, description="DPI al rasterizar páginas PDF.")
    ocr_max_workers: int = Field(
        default=2,
        ge=1,
        le=8,
        description="Hilos paralelos para OCR por página.",
    )

    chunk_size_tokens: int = Field(
        default=500,
        ge=50,
        le=4000,
        description="Tamaño objetivo de cada chunk (tokens aproximados).",
    )
    chunk_overlap_tokens: int = Field(
        default=100,
        ge=0,
        le=500,
        description="Solapamiento entre chunks consecutivos (ventana deslizante).",
    )
    max_chunk_size_tokens: int = Field(
        default=800,
        ge=100,
        le=8000,
        description="Tope duro por chunk; se parte si se supera.",
    )
    chunk_min_merge_tokens: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Chunks por debajo de este umbral se fusionan con el vecino.",
    )
    embedding_enabled: bool = Field(
        default=True,
        description="Si false, la etapa embed se omite (solo para depuración).",
    )
    embedding_backend: Literal["auto", "fake", "sentence_transformers"] = Field(
        default="auto",
        description="`auto`: fake en test, sentence_transformers en otros entornos.",
    )
    embedding_model_name: str = Field(
        default="BAAI/bge-m3",
        description="Nombre HuggingFace / SentenceTransformers.",
    )
    embedding_model_label: str = Field(
        default="bge-m3",
        description="Etiqueta corta persistida en chunks.embedding_model.",
    )
    embedding_batch_size: int = Field(default=32, ge=1, le=256)
    embedding_batch_size_min: int = Field(
        default=1,
        ge=1,
        description="Tamaño mínimo de batch tras backoff por OOM.",
    )
    embedding_normalize: bool = Field(
        default=True,
        description="Normalizar L2 los vectores (recomendado para cosine).",
    )
    embedding_timeout_seconds: float = Field(default=300.0, ge=5.0)
    embedding_fake_dimension: int = Field(
        default=64,
        ge=8,
        le=1024,
        description="Dimensión del vector fake (solo backend fake / tests).",
    )

    rag_hybrid_enabled: bool = Field(
        default=True,
        description="Si true, combina búsqueda vectorial y BM25 con RRF.",
    )
    rag_vector_top_k: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Candidatos vectoriales antes de fusión.",
    )
    rag_bm25_top_k: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Candidatos BM25 antes de fusión.",
    )
    rag_rrf_k: int = Field(
        default=60,
        ge=1,
        le=500,
        description="Constante k de Reciprocal Rank Fusion.",
    )
    rag_search_max_top_k: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Tope de resultados devueltos por POST /search.",
    )
    rag_rerank_enabled: bool = Field(
        default=True,
        description="Si true, reordena candidatos híbridos con FlashRank (o fake en test).",
    )
    rag_rerank_candidate_top_k: int = Field(
        default=30,
        ge=1,
        le=100,
        description="Candidatos tras fusión híbrida que entran al reranker (top-N).",
    )
    rag_rerank_top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Resultados finales tras rerank (top-M).",
    )
    rag_rerank_backend: Literal["auto", "fake", "flashrank"] = Field(
        default="auto",
        description="`auto`: fake en test, flashrank en otros entornos.",
    )
    rag_rerank_model_name: str = Field(
        default="ms-marco-TinyBERT-L-2-v2",
        description="Modelo FlashRank (cross-encoder).",
    )
    rag_rerank_max_length: int = Field(
        default=256,
        ge=64,
        le=512,
        description="max_length del cross-encoder FlashRank.",
    )
    rag_rerank_max_passage_chars: int = Field(
        default=2000,
        ge=100,
        le=8000,
        description="Recorte de texto del chunk antes de rerank.",
    )
    rag_rerank_cache_dir: str = Field(
        default="",
        description="Directorio cache de modelos FlashRank (vacío = default de la lib).",
    )

    clamav_enabled: bool = Field(
        default=True,
        description="Escaneo antivirus en la etapa ingest antes de parse.",
    )
    clamav_host: str = Field(default="clamav")
    clamav_port: int = Field(default=3310, ge=1, le=65535)
    clamav_timeout_seconds: float = Field(
        default=120.0,
        ge=5.0,
        description="Timeout por conexión INSTREAM a clamd.",
    )
    clamav_fail_open: bool = Field(
        default=False,
        description="Si clamd no responde, omitir escaneo (solo dev/local).",
    )
    clamav_allow_eicar_test: bool = Field(
        default=False,
        description="Backend fake en test: detectar cadena EICAR estándar.",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def socketio_cors_origin_list(self) -> list[str]:
        raw = self.socketio_cors_origins.strip()
        if raw:
            return [o.strip() for o in raw.split(",") if o.strip()]
        return self.cors_origins

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def qdrant_http_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def ollama_http_url(self) -> str:
        return f"http://{self.ollama_host}:{self.ollama_port}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_mime_type_list(self) -> list[str]:
        return [m.strip() for m in self.allowed_mime_types.split(",") if m.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_celery_broker_url(self) -> str:
        if self.celery_broker_url.strip():
            return self.celery_broker_url.strip()
        return self.redis_url

    @computed_field  # type: ignore[prop-decorator]
    @property
    def resolved_celery_result_backend(self) -> str | None:
        s = self.celery_result_backend.strip()
        return s if s else None

    @model_validator(mode="after")
    def validate_boot(self) -> Settings:
        if self.environment == "test" and not self.jwt_secret.strip():
            self.jwt_secret = "test_jwt_secret_" + "x" * 32
        elif self.environment in ("staging", "production") and len(self.jwt_secret) < 32:
            msg = "JWT_SECRET debe tener al menos 32 caracteres en staging/production."
            raise ValueError(msg)
        elif self.environment == "local" and len(self.jwt_secret) < 16:
            msg = "JWT_SECRET debe tener al menos 16 caracteres en local (fail-fast)."
            raise ValueError(msg)

        if self.environment == "test" and not self.password_pepper.strip():
            self.password_pepper = "test_password_pepper_" + "x" * 32
        elif self.environment in ("staging", "production") and len(self.password_pepper) < 32:
            msg = "PASSWORD_PEPPER debe tener al menos 32 caracteres en staging/production."
            raise ValueError(msg)
        elif self.environment == "local" and len(self.password_pepper) < 16:
            msg = "PASSWORD_PEPPER debe tener al menos 16 caracteres en local (fail-fast)."
            raise ValueError(msg)

        if not _looks_like_sqlalchemy_postgres(self.database_url):
            msg = "DATABASE_URL debe ser un DSN PostgreSQL (postgresql+psycopg o postgresql)."
            raise ValueError(msg)

        if self.environment == "test":
            self.celery_task_always_eager = True
            env_clamav = os.environ.get("CLAMAV_ENABLED", "").strip().lower()
            if env_clamav not in ("1", "true", "yes", "on"):
                self.clamav_enabled = False

        if self.chunk_overlap_tokens >= self.chunk_size_tokens:
            msg = "CHUNK_OVERLAP_TOKENS debe ser menor que CHUNK_SIZE_TOKENS."
            raise ValueError(msg)
        if self.max_chunk_size_tokens < self.chunk_size_tokens:
            msg = "MAX_CHUNK_SIZE_TOKENS debe ser >= CHUNK_SIZE_TOKENS."
            raise ValueError(msg)

        if self.embedding_batch_size_min > self.embedding_batch_size:
            msg = "EMBEDDING_BATCH_SIZE_MIN no puede ser mayor que EMBEDDING_BATCH_SIZE."
            raise ValueError(msg)

        if self.embedding_backend == "auto":
            self.embedding_backend = (
                "fake" if self.environment == "test" else "sentence_transformers"
            )

        if self.rag_rerank_backend == "auto":
            self.rag_rerank_backend = "fake" if self.environment == "test" else "flashrank"

        if self.chat_llm_backend == "auto":
            self.chat_llm_backend = "fake" if self.environment == "test" else "ollama"

        if self.rag_rerank_candidate_top_k < self.rag_rerank_top_k:
            msg = "RAG_RERANK_CANDIDATE_TOP_K debe ser >= RAG_RERANK_TOP_K."
            raise ValueError(msg)

        return self

    def resolved_rerank_backend(self) -> Literal["fake", "flashrank"]:
        if self.rag_rerank_backend == "fake":
            return "fake"
        return "flashrank"

    def resolved_embedding_backend(self) -> Literal["fake", "sentence_transformers"]:
        if self.embedding_backend == "fake":
            return "fake"
        return "sentence_transformers"

    def resolved_chat_llm_backend(self) -> Literal["fake", "ollama"]:
        if self.chat_llm_backend == "fake":
            return "fake"
        return "ollama"


def _looks_like_sqlalchemy_postgres(url: str) -> bool:
    return bool(re.match(r"^postgresql(\+[\w]+)?://", url.strip()))


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
