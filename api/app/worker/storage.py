import httpx

from app.config import get_settings


class WorkerStorage:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = f"{settings.supabase.url}/storage/v1"
        self.headers = {
            "apikey": settings.supabase.service_role_key,
            "Authorization": f"Bearer {settings.supabase.service_role_key}",
        }
        self.sources_bucket = settings.infra.sources_bucket
        self.artifacts_bucket = settings.infra.artifacts_bucket

    def download(self, path: str, *, bucket: str | None = None) -> bytes:
        bucket_name = bucket or self.sources_bucket

        with httpx.Client(timeout=120) as client:
            response = client.get(
                f"{self.base_url}/object/{bucket_name}/{path}",
                headers=self.headers,
            )

        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise RuntimeError(
                f"Supabase Storage download failed ({response.status_code}): {detail}",
            )

        return response.content

    def upload(
        self,
        path: str,
        content: bytes,
        *,
        bucket: str | None = None,
        content_type: str = "application/octet-stream",
        upsert: bool = True,
    ) -> None:
        bucket_name = bucket or self.artifacts_bucket
        headers = {
            **self.headers,
            "Content-Type": content_type,
        }

        if upsert:
            headers["x-upsert"] = "true"

        with httpx.Client(timeout=120) as client:
            response = client.post(
                f"{self.base_url}/object/{bucket_name}/{path}",
                headers=headers,
                content=content,
            )

        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise RuntimeError(
                f"Supabase Storage upload failed ({response.status_code}): {detail}",
            )
