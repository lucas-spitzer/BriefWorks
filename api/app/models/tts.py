from pydantic import BaseModel, ConfigDict


class TtsVoiceResponse(BaseModel):
    id: str
    display_name: str


class TtsCatalogModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    model: str
    provider: str
    display_name: str
    default_voice_id: str
    voices: list[TtsVoiceResponse]
    price_per_million: float | None = None
    capability_tier: int


class TtsCatalogResponse(BaseModel):
    models: list[TtsCatalogModelResponse]
