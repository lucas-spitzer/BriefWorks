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
        bucket_name = bucket or self.sources_bucket
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

    def copy(
        self,
        source_path: str,
        dest_path: str,
        *,
        content_type: str,
        bucket: str | None = None,
    ) -> None:
        content = self.download(source_path, bucket=bucket)
        self.upload(
            dest_path,
            content,
            bucket=bucket,
            content_type=content_type,
            upsert=True,
        )

    def delete(self, path: str, *, bucket: str | None = None) -> None:
        bucket_name = bucket or self.sources_bucket
        with httpx.Client(timeout=60) as client:
            response = client.delete(
                f"{self.base_url}/object/{bucket_name}/{path}",
                headers=self.headers,
            )
        if response.status_code in {404, 400}:
            return
        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise RuntimeError(
                f"Supabase Storage delete failed ({response.status_code}): {detail}",
            )

    def list_paths(self, prefix: str, *, bucket: str | None = None) -> list[str]:
        """Return object keys under prefix. Storage has no folder delete API."""
        bucket_name = bucket or self.sources_bucket
        root = prefix.strip("/")
        with httpx.Client(timeout=120) as client:
            return self._list_paths_at(client, bucket_name, root)

    def delete_prefix(self, prefix: str, *, bucket: str | None = None) -> int:
        """Delete every object under prefix. Returns how many keys were removed."""
        paths = self.list_paths(prefix, bucket=bucket)
        if not paths:
            return 0
        bucket_name = bucket or self.sources_bucket
        removed = 0
        with httpx.Client(timeout=120) as client:
            for start in range(0, len(paths), 1000):
                batch = paths[start : start + 1000]
                response = client.request(
                    "DELETE",
                    f"{self.base_url}/object/{bucket_name}",
                    headers={**self.headers, "Content-Type": "application/json"},
                    json={"prefixes": batch},
                )
                if response.status_code >= 400:
                    detail = response.text.strip() or response.reason_phrase
                    raise RuntimeError(
                        f"Supabase Storage prefix delete failed ({response.status_code}): {detail}",
                    )
                removed += len(batch)
        return removed

    def _list_paths_at(
        self,
        client: httpx.Client,
        bucket_name: str,
        prefix: str,
    ) -> list[str]:
        paths: list[str] = []
        offset = 0
        limit = 1000
        list_prefix = f"{prefix}/" if prefix else ""
        while True:
            response = client.post(
                f"{self.base_url}/object/list/{bucket_name}",
                headers={**self.headers, "Content-Type": "application/json"},
                json={
                    "prefix": list_prefix,
                    "limit": limit,
                    "offset": offset,
                    "sortBy": {"column": "name", "order": "asc"},
                },
            )
            if response.status_code >= 400:
                detail = response.text.strip() or response.reason_phrase
                raise RuntimeError(
                    f"Supabase Storage list failed ({response.status_code}): {detail}",
                )
            items = response.json()
            if not isinstance(items, list) or not items:
                break
            for item in items:
                name = str(item.get("name") or "")
                if not name or name in {".", ".."}:
                    continue
                full = f"{list_prefix}{name}" if list_prefix else name
                if item.get("id") is None:
                    paths.extend(self._list_paths_at(client, bucket_name, full))
                else:
                    paths.append(full)
            if len(items) < limit:
                break
            offset += limit
        return paths

    def empty_bucket(self, bucket: str) -> None:
        """Delete all objects in a bucket via the Storage API."""
        with httpx.Client(timeout=120) as client:
            response = client.post(
                f"{self.base_url}/bucket/{bucket}/empty",
                headers=self.headers,
            )

        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise RuntimeError(
                f"Supabase Storage empty bucket failed ({response.status_code}): {detail}",
            )

    def delete_bucket(self, bucket: str) -> None:
        """Delete an empty bucket via the Storage API."""
        with httpx.Client(timeout=60) as client:
            response = client.delete(
                f"{self.base_url}/bucket/{bucket}",
                headers=self.headers,
            )

        if response.status_code == 404:
            return

        if response.status_code >= 400:
            detail = response.text.strip() or response.reason_phrase
            raise RuntimeError(
                f"Supabase Storage delete bucket failed ({response.status_code}): {detail}",
            )
