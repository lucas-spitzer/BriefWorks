from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.repositories.artifacts import ArtifactRepository
from app.repositories.assessments import AssessmentRepository
from app.repositories.ndr_segments import NdrSegmentRepository
from app.repositories.wiki_entries import WikiEntryRepository
from app.repositories.production_runs import ProductionRunRepository
from app.repositories.stage_runs import StageRunRepository
from app.repositories.stages import StageRepository
from app.repositories.sources import SourceRepository
from app.repositories.stage_settings import StageSettingsRepository
from app.repositories.workspaces import WorkspaceRepository
from app.services.supabase_rest import SupabaseRestClient
from app.services.supabase_storage import SupabaseStorageClient


def get_supabase_rest_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SupabaseRestClient:
    return SupabaseRestClient(settings)


def get_supabase_storage_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> SupabaseStorageClient:
    return SupabaseStorageClient(settings)


def get_workspace_repository(
    db: Annotated[SupabaseRestClient, Depends(get_supabase_rest_client)],
) -> WorkspaceRepository:
    return WorkspaceRepository(db)


def get_stage_repository(
    db: Annotated[SupabaseRestClient, Depends(get_supabase_rest_client)],
) -> StageRepository:
    return StageRepository(db)


def get_stage_settings_repository(
    db: Annotated[SupabaseRestClient, Depends(get_supabase_rest_client)],
) -> StageSettingsRepository:
    return StageSettingsRepository(db)


def get_source_repository(
    db: Annotated[SupabaseRestClient, Depends(get_supabase_rest_client)],
) -> SourceRepository:
    return SourceRepository(db)


def get_production_run_repository(
    db: Annotated[SupabaseRestClient, Depends(get_supabase_rest_client)],
) -> ProductionRunRepository:
    return ProductionRunRepository(db)


def get_stage_run_repository(
    db: Annotated[SupabaseRestClient, Depends(get_supabase_rest_client)],
) -> StageRunRepository:
    return StageRunRepository(db)


def get_ndr_segment_repository(
    db: Annotated[SupabaseRestClient, Depends(get_supabase_rest_client)],
) -> NdrSegmentRepository:
    return NdrSegmentRepository(db)


def get_wiki_entry_repository(
    db: Annotated[SupabaseRestClient, Depends(get_supabase_rest_client)],
) -> WikiEntryRepository:
    return WikiEntryRepository(db)


def get_artifact_repository(
    db: Annotated[SupabaseRestClient, Depends(get_supabase_rest_client)],
) -> ArtifactRepository:
    return ArtifactRepository(db)


def get_assessment_repository(
    db: Annotated[SupabaseRestClient, Depends(get_supabase_rest_client)],
) -> AssessmentRepository:
    return AssessmentRepository(db)
