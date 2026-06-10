from typing import Any

import httpx

from app.config import Settings
from app.models.auth import CurrentUser


class SupabaseAuthError(Exception):
    """Raised when Supabase cannot validate the presented user token."""


class SupabaseApprovalError(Exception):
    """Raised when BriefWorks cannot complete the approval lookup."""


class SupabaseRequestError(Exception):
    """Raised when Supabase cannot be reached."""


class SupabaseUserNotApprovedError(Exception):
    """Raised when a valid Supabase user is not approved for BriefWorks."""


class SupabaseService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def get_current_user(self, access_token: str) -> CurrentUser:
        user = await self._get_supabase_user(access_token)
        user_id = user.get("id")
        email = user.get("email")

        if not isinstance(user_id, str) or not isinstance(email, str):
            raise SupabaseAuthError("Supabase user payload is missing required claims.")

        approved_user = await self._get_approved_user(email)

        return CurrentUser(
            id=user_id,
            email=email,
            role=str(approved_user.get("role") or "viewer"),
        )

    async def _get_supabase_user(self, access_token: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.settings.supabase_url}/auth/v1/user",
                    headers={
                        "apikey": self.settings.supabase_publishable_key,
                        "Authorization": f"Bearer {access_token}",
                    },
                )
        except httpx.HTTPError as exc:
            raise SupabaseRequestError("Supabase Auth could not be reached.") from exc

        if response.status_code != 200:
            raise SupabaseAuthError("Invalid or expired Supabase session.")

        return response.json()

    async def _get_approved_user(self, email: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.settings.supabase_url}/rest/v1/approved_users",
                    headers={
                        "apikey": self.settings.supabase_service_role_key,
                        "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
                        "Accept": "application/json",
                    },
                    params={
                        "select": "email,role,is_active",
                        "email": f"eq.{email}",
                        "is_active": "eq.true",
                        "limit": "1",
                    },
                )
        except httpx.HTTPError as exc:
            raise SupabaseRequestError("Supabase REST could not be reached.") from exc

        if response.status_code != 200:
            raise SupabaseApprovalError("Approval lookup failed.")

        approved_users = response.json()

        if not approved_users:
            raise SupabaseUserNotApprovedError(
                "This account is not approved for BriefWorks access.",
            )

        approved_user = approved_users[0]

        if not approved_user.get("is_active"):
            raise SupabaseUserNotApprovedError(
                "This account is not approved for BriefWorks access.",
            )

        return approved_user
