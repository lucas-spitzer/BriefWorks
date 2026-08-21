# Shared LLM defaults — kept outside app.services.llm to avoid import cycles with config.
HAIKU_45_MODEL = "claude-haiku-4-5-20251001"
SONNET_5_MODEL = "claude-sonnet-5"
OPUS_5_MODEL = "claude-opus-5"
GPT_56_SOL_MODEL = "gpt-5.6-sol"
GPT_56_TERRA_MODEL = "gpt-5.6-terra"
GPT_56_LUNA_MODEL = "gpt-5.6-luna"
GEMINI_37_FLASH_MODEL = "gemini-3.7-flash"
# Constructor fallback when an OpenAI client is built without a model.
# Per-action defaults live in env vars (SOURCE_RESEARCH_MODEL, etc.).
DEFAULT_OPENAI_MODEL = GPT_56_LUNA_MODEL
