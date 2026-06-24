from pydantic import BaseModel, ConfigDict

from app.services.llm.model_catalog import MODEL_CATALOG


class CatalogModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    model: str
    provider: str
    display_name: str
    capability_tier: int
    supports_reasoning: bool
    reasoning_modes: list[str]
    context_window: int | None
    input_per_million: float | None
    output_per_million: float | None


class ModelCatalogResponse(BaseModel):
    models: list[CatalogModelResponse]


def build_model_catalog_response() -> ModelCatalogResponse:
    return ModelCatalogResponse(
        models=[CatalogModelResponse.model_validate(entry) for entry in MODEL_CATALOG],
    )
