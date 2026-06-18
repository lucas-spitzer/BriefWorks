import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

API_DIR = Path(__file__).resolve().parents[1]

load_dotenv(API_DIR / ".env")


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


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_publishable_key: str
    supabase_service_role_key: str
    frontend_origins: list[str]
    redis_url: str
    sources_bucket: str
    rq_queue_name: str
    openai_api_key: str | None
    openai_model: str
    tavily_api_key: str | None
    source_research_max_chars: int
    artifacts_bucket: str
    signed_url_expires_seconds: int
    max_source_upload_bytes: int
    elevenlabs_api_key: str | None
    elevenlabs_voice_id: str
    elevenlabs_model_id: str
    elevenlabs_max_chars: int
    elevenlabs_request_timeout_seconds: int
    elevenlabs_max_retries: int
    elevenlabs_chunk_chars: int
    production_run_job_timeout: str
    speechify_api_key: str | None
    speechify_voice_id: str
    speechify_model: str
    speechify_max_chars: int
    llama_cloud_api_key: str | None
    llamaparse_tier: str
    prepare_batch_pages: int
    qngen_model: str
    qngen_concept_batch_size: int


@lru_cache
def get_settings() -> Settings:
    return Settings(
        supabase_url=get_required_env("SUPABASE_URL").rstrip("/"),
        supabase_publishable_key=get_first_env("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_ANON_KEY"),
        supabase_service_role_key=get_required_env("SUPABASE_SERVICE_ROLE_KEY"),
        frontend_origins=parse_csv_env("FRONTEND_ORIGINS", "http://localhost:5173"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        sources_bucket=os.getenv("SOURCES_BUCKET", "sources"),
        rq_queue_name=os.getenv("RQ_QUEUE_NAME", "briefworks"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        tavily_api_key=os.getenv("TAVILY_API_KEY"),
        source_research_max_chars=int(os.getenv("SOURCE_RESEARCH_MAX_CHARS", "12000")),
        artifacts_bucket=os.getenv("ARTIFACTS_BUCKET", "artifacts"),
        signed_url_expires_seconds=int(os.getenv("SIGNED_URL_EXPIRES_SECONDS", "3600")),
        max_source_upload_bytes=int(
            os.getenv("MAX_SOURCE_UPLOAD_BYTES", str(100 * 1024 * 1024)),
        ),
        elevenlabs_api_key=os.getenv("ELEVENLABS_API_KEY"),
        elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
        elevenlabs_model_id=os.getenv("ELEVENLABS_MODEL_ID", "eleven_v3"),
        elevenlabs_max_chars=int(os.getenv("ELEVENLABS_MAX_CHARS", "200000")),
        elevenlabs_request_timeout_seconds=int(
            os.getenv("ELEVENLABS_REQUEST_TIMEOUT_SECONDS", "600"),
        ),
        elevenlabs_max_retries=int(os.getenv("ELEVENLABS_MAX_RETRIES", "3")),
        elevenlabs_chunk_chars=int(os.getenv("ELEVENLABS_CHUNK_CHARS", "2500")),
        production_run_job_timeout=os.getenv("PRODUCTION_RUN_JOB_TIMEOUT", "2h"),
        speechify_api_key=os.getenv("SPEECHIFY_API_KEY"),
        speechify_voice_id=os.getenv("SPEECHIFY_VOICE_ID", "george"),
        speechify_model=os.getenv("SPEECHIFY_MODEL", "simba-english"),
        speechify_max_chars=int(os.getenv("SPEECHIFY_MAX_CHARS", "200000")),
        llama_cloud_api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
        llamaparse_tier=os.getenv("LLAMAPARSE_TIER", "agentic"),
        prepare_batch_pages=int(os.getenv("PREPARE_BATCH_PAGES", "15")),
        qngen_model=os.getenv("QNGEN_MODEL", "gpt-4o"),
        qngen_concept_batch_size=int(os.getenv("QNGEN_CONCEPT_BATCH_SIZE", "8")),
    )
