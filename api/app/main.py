from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.dependencies.auth import require_approved_user
from app.models.auth import CurrentUser, CurrentUserResponse
from app.routers import artifacts, assessments, production_runs, skills, sources, wiki, workspaces

settings = get_settings()

app = FastAPI(title="BriefWorks API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(workspaces.router)
app.include_router(skills.router)
app.include_router(sources.router)
app.include_router(production_runs.router)
app.include_router(wiki.router)
app.include_router(artifacts.router)
app.include_router(assessments.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/me", response_model=CurrentUserResponse)
async def get_me(
    user: Annotated[CurrentUser, Depends(require_approved_user)],
) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
    )
