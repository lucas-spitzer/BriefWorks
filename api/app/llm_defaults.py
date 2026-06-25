# Shared LLM defaults — kept outside app.services.llm to avoid import cycles with config.
HAIKU_45_MODEL = "claude-haiku-4-5-20251001"
GPT_54_MODEL = "gpt-5.4"
GPT_54_MINI_MODEL = "gpt-5.4-mini"
# Default OpenAI model (also the OPENAI_MODEL env fallback). gpt-4o / gpt-4o-mini
# were retired as selectable options.
DEFAULT_OPENAI_MODEL = GPT_54_MINI_MODEL
