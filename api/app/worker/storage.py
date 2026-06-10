import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

API_DIR = Path(__file__).resolve().parents[2]
load_dotenv(API_DIR / ".env")


class WorkerStorage:
    def __init__(self) -> None:
        supabase_url = os.environ["SUPABASE_URL"].rstrip("/")
        service_role_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        self.base_url = f"{supabase_url}/storage/v1"
        self.headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
        }
        self.sources_bucket = os.getenv("SOURCES_BUCKET", "workspace-sources")
        self.artifacts_bucket = os.getenv("ARTIFACTS_BUCKET", "workspace-artifacts")

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
