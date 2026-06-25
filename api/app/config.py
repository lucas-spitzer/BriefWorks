import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from app.llm_actions import LLM_ACTION_DEFAULTS, LLM_GLOBAL_DEFAULT
from app.llm_defaults import DEFAULT_OPENAI_MODEL

API_DIR = Path(__file__).resolve().parents[1]
_DOTENV_PATH = API_DIR / ".env"
_DOTENV_MTIME: float | None = None

load_dotenv(_DOTENV_PATH)


def _refresh_dotenv_if_changed() -> None:
    """Reload .env when the file changes so dev edits apply without a restart."""
    global _DOTENV_MTIME

    if not _DOTENV_PATH.exists():
        return

    mtime = _DOTENV_PATH.stat().st_mtime
    if _DOTENV_MTIME == mtime:
        return

    load_dotenv(_DOTENV_PATH, override=True)
    _DOTENV_MTIME = mtime
    _get_settings_cached.cache_clear()


def get_required_env(name: str) -> str:
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")

    return value


def get_first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)

        if value:
            return value

    formatted_names = ", ".join(names)
    raise RuntimeError(f"Missing one of required environment variables: {formatted_names}")


def parse_csv_env(name: str, default: str) -> list[str]:
    raw_value = os.getenv(name, default)
    values = [value.strip() for value in raw_value.split(",")]

    return [value for value in values if value]


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)

    if raw is None or not raw.strip():
        return default

    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_llm_action(action: str) -> "LLMActionSettings":
    _refresh_dotenv_if_changed()
    provider_default, model_default = LLM_ACTION_DEFAULTS.get(action, LLM_GLOBAL_DEFAULT)
    key = action.upper()
    provider = os.getenv(f"LLM_{key}_PROVIDER", provider_default).strip().lower()
    model = os.getenv(f"LLM_{key}_MODEL", "").strip()

    if not model:
        # Fall back to the provider's global default model, then the registry default.
        if provider == "openai":
            model = os.getenv("OPENAI_MODEL", model_default).strip()
        else:
            model = model_default

    return LLMActionSettings(provider=provider, model=model)


@dataclass(frozen=True)
class SupabaseSettings:
    url: str
    publishable_key: str
    service_role_key: str


@dataclass(frozen=True)
class InfrastructureSettings:
    frontend_origins: list[str]
    redis_url: str
    sources_bucket: str
    artifacts_bucket: str
    rq_queue_name: str
    production_run_job_timeout: str
    signed_url_expires_seconds: int
    max_source_upload_bytes: int
    log_level: str


@dataclass(frozen=True)
class LLMActionSettings:
    provider: str
    model: str


@dataclass(frozen=True)
class LLMSettings:
    openai_api_key: str | None
    openai_model: str
    anthropic_api_key: str | None
    anthropic_max_tokens: int
    anthropic_json_prefill: str

    def resolve_action(self, action: str) -> LLMActionSettings:
        return _resolve_llm_action(action)


@dataclass(frozen=True)
class IntellexSettings:
    llama_cloud_api_key: str | None
    llamaparse_tier: str
    source_research_max_chars: int
    extract_knowledge_deep_importance: tuple[str, ...]
    extract_chapter_max_chars: int | None
    eleven_reader_max_pages: int
    prepare_batch_pages: int
    # Wiki-entry selection bands/thresholds (extraction redesign). Defaults are
    # permissive (0 = no cap / no gate) so behavior is unchanged until the
    # scored-selection phases consume them.
    extract_max_entries_per_chapter: int
    extract_max_entries_per_document: int
    extract_min_confidence: float
    extract_min_selection_score: float
    # Comparative importance calibration: top fraction → essential, next
    # fraction → supporting, remainder → contextual (document-wide ranking).
    extract_essential_fraction: float
    extract_supporting_fraction: float
    # Embedding-based semantic dedup (off by default — adds per-extraction
    # embedding API cost). Merges candidates whose vectors exceed the threshold.
    extract_embedding_dedup: bool
    extract_embedding_model: str
    extract_embedding_similarity_threshold: float


@dataclass(frozen=True)
class QnGenSettings:
    concept_batch_size: int
    critique_supporting: bool
    max_repair_turns: int
    flashcards_per_chapter_min: int
    flashcards_per_chapter_max: int
    scenarios_per_chapter_min: int
    scenarios_per_chapter_max: int


@dataclass(frozen=True)
class ElevenLabsSettings:
    api_key: str | None
    voice_id: str
    model_id: str
    max_chars: int
    chunk_chars: int
    request_timeout_seconds: int
    max_retries: int
    price_per_token: float


@dataclass(frozen=True)
class SpeechifySettings:
    api_key: str | None
    voice_id: str
    model: str
    max_chars: int


@dataclass(frozen=True)
class Settings:
    supabase: SupabaseSettings
    infra: InfrastructureSettings
    llm: LLMSettings
    intellex: IntellexSettings
    qngen: QnGenSettings
    elevenlabs: ElevenLabsSettings
    speechify: SpeechifySettings

    # Backward-compatible flat accessors for existing call sites.
    @property
    def supabase_url(self) -> str:
        return self.supabase.url

    @property
    def supabase_publishable_key(self) -> str:
        return self.supabase.publishable_key

    @property
    def supabase_service_role_key(self) -> str:
        return self.supabase.service_role_key

    @property
    def frontend_origins(self) -> list[str]:
        return self.infra.frontend_origins

    @property
    def redis_url(self) -> str:
        return self.infra.redis_url

    @property
    def sources_bucket(self) -> str:
        return self.infra.sources_bucket

    @property
    def artifacts_bucket(self) -> str:
        return self.infra.artifacts_bucket

    @property
    def rq_queue_name(self) -> str:
        return self.infra.rq_queue_name

    @property
    def production_run_job_timeout(self) -> str:
        return self.infra.production_run_job_timeout

    @property
    def signed_url_expires_seconds(self) -> int:
        return self.infra.signed_url_expires_seconds

    @property
    def max_source_upload_bytes(self) -> int:
        return self.infra.max_source_upload_bytes

    @property
    def qngen_concept_batch_size(self) -> int:
        return self.qngen.concept_batch_size


@lru_cache
def _get_settings_cached() -> Settings:
    deep_importance = tuple(
        value.strip()
        for value in parse_csv_env("EXTRACT_KNOWLEDGE_DEEP_IMPORTANCE", "essential,supporting")
    )
    extract_chapter_raw = os.getenv("EXTRACT_CHAPTER_MAX_CHARS")
    extract_chapter_max_chars = (
        int(extract_chapter_raw) if extract_chapter_raw and extract_chapter_raw.strip() else None
    )

    return Settings(
        supabase=SupabaseSettings(
            url=get_required_env("SUPABASE_URL").rstrip("/"),
            publishable_key=get_first_env("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_ANON_KEY"),
            service_role_key=get_required_env("SUPABASE_SERVICE_ROLE_KEY"),
        ),
        infra=InfrastructureSettings(
            frontend_origins=parse_csv_env("FRONTEND_ORIGINS", "http://localhost:5173"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            sources_bucket=os.getenv("SOURCES_BUCKET", "sources"),
            artifacts_bucket=os.getenv("ARTIFACTS_BUCKET", "artifacts"),
            rq_queue_name=os.getenv("RQ_QUEUE_NAME", "briefworks"),
            production_run_job_timeout=os.getenv("PRODUCTION_RUN_JOB_TIMEOUT", "2h"),
            signed_url_expires_seconds=int(os.getenv("SIGNED_URL_EXPIRES_SECONDS", "3600")),
            max_source_upload_bytes=int(
                os.getenv("MAX_SOURCE_UPLOAD_BYTES", str(100 * 1024 * 1024)),
            ),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        ),
        llm=LLMSettings(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            anthropic_max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", "16384")),
            anthropic_json_prefill=os.getenv("ANTHROPIC_JSON_PREFILL", "auto").strip().lower(),
        ),
        intellex=IntellexSettings(
            llama_cloud_api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
            llamaparse_tier=os.getenv("LLAMAPARSE_TIER", "agentic"),
            source_research_max_chars=int(os.getenv("SOURCE_RESEARCH_MAX_CHARS", "16000")),
            extract_knowledge_deep_importance=deep_importance,
            extract_chapter_max_chars=extract_chapter_max_chars,
            eleven_reader_max_pages=int(os.getenv("ELEVEN_READER_MAX_PAGES", "500")),
            prepare_batch_pages=int(os.getenv("PREPARE_BATCH_PAGES", "15")),
            extract_max_entries_per_chapter=int(os.getenv("EXTRACT_MAX_ENTRIES_PER_CHAPTER", "0")),
            extract_max_entries_per_document=int(os.getenv("EXTRACT_MAX_ENTRIES_PER_DOCUMENT", "0")),
            extract_min_confidence=float(os.getenv("EXTRACT_MIN_CONFIDENCE", "0.0")),
            extract_min_selection_score=float(os.getenv("EXTRACT_MIN_SELECTION_SCORE", "0.0")),
            extract_essential_fraction=float(os.getenv("EXTRACT_ESSENTIAL_FRACTION", "0.2")),
            extract_supporting_fraction=float(os.getenv("EXTRACT_SUPPORTING_FRACTION", "0.4")),
            extract_embedding_dedup=_bool_env("EXTRACT_EMBEDDING_DEDUP", False),
            extract_embedding_model=os.getenv("EXTRACT_EMBEDDING_MODEL", "text-embedding-3-small"),
            extract_embedding_similarity_threshold=float(
                os.getenv("EXTRACT_EMBEDDING_SIMILARITY_THRESHOLD", "0.86"),
            ),
        ),
        qngen=QnGenSettings(
            concept_batch_size=int(os.getenv("QNGEN_CONCEPT_BATCH_SIZE", "8")),
            critique_supporting=_bool_env("QNGEN_CRITIQUE_SUPPORTING", False),
            max_repair_turns=int(os.getenv("QNGEN_MAX_REPAIR_TURNS", "2")),
            flashcards_per_chapter_min=int(os.getenv("QNGEN_FLASHCARDS_PER_CHAPTER_MIN", "3")),
            flashcards_per_chapter_max=int(os.getenv("QNGEN_FLASHCARDS_PER_CHAPTER_MAX", "8")),
            scenarios_per_chapter_min=int(os.getenv("QNGEN_SCENARIOS_PER_CHAPTER_MIN", "1")),
            scenarios_per_chapter_max=int(os.getenv("QNGEN_SCENARIOS_PER_CHAPTER_MAX", "3")),
        ),
        elevenlabs=ElevenLabsSettings(
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
            model_id=os.getenv("ELEVENLABS_MODEL_ID", "eleven_v3"),
            max_chars=int(os.getenv("ELEVENLABS_MAX_CHARS", "200000")),
            chunk_chars=int(os.getenv("ELEVENLABS_CHUNK_CHARS", "2500")),
            request_timeout_seconds=int(os.getenv("ELEVENLABS_REQUEST_TIMEOUT_SECONDS", "600")),
            max_retries=int(os.getenv("ELEVENLABS_MAX_RETRIES", "3")),
            price_per_token=float(os.getenv("ELEVENLABS_PRICE_PER_TOKEN", "0.00018333")),
        ),
        speechify=SpeechifySettings(
            api_key=os.getenv("SPEECHIFY_API_KEY"),
            voice_id=os.getenv("SPEECHIFY_VOICE_ID", "george"),
            model=os.getenv("SPEECHIFY_MODEL", "simba-english"),
            max_chars=int(os.getenv("SPEECHIFY_MAX_CHARS", "200000")),
        ),
    )


def get_settings() -> Settings:
    _refresh_dotenv_if_changed()
    return _get_settings_cached()


get_settings.cache_clear = _get_settings_cached.cache_clear  # type: ignore[attr-defined]
