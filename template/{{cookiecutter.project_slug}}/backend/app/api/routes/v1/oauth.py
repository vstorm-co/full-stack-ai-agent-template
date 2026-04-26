{%- if cookiecutter.enable_oauth %}
"""OAuth2 authentication routes."""

from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.api.deps import UserSvc
from app.core.oauth import oauth
from app.core.security import create_access_token, create_refresh_token

router = APIRouter()

from app.core.config import settings

FRONTEND_URL = settings.FRONTEND_URL

{%- if cookiecutter.enable_oauth_google %}


@router.get("/google/login")
async def google_login(request: Request):
    """Redirect to Google OAuth2 login page."""
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


{%- if cookiecutter.use_postgresql %}


@router.get("/google/callback")
async def google_callback(request: Request, user_service: UserSvc):
    """Handle Google OAuth2 callback."""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")

        if not user_info:
            params = urlencode({"error": "Failed to get user info from Google"})
            return RedirectResponse(url=f"{FRONTEND_URL}/login?{params}")

        user = await user_service.get_or_create_oauth_user(
            provider="google",
            provider_id=user_info.get("sub"),
            email=user_info.get("email"),
            full_name=user_info.get("name"),
        )

        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))

        params = urlencode({
            "access_token": access_token,
            "refresh_token": refresh_token,
        })
        return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?{params}")

    except Exception as e:
        params = urlencode({"error": str(e)})
        return RedirectResponse(url=f"{FRONTEND_URL}/login?{params}")


{%- elif cookiecutter.use_mongodb %}


@router.get("/google/callback")
async def google_callback(request: Request, user_service: UserSvc):
    """Handle Google OAuth2 callback."""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")

        if not user_info:
            params = urlencode({"error": "Failed to get user info from Google"})
            return RedirectResponse(url=f"{FRONTEND_URL}/login?{params}")

        user = await user_service.get_or_create_oauth_user(
            provider="google",
            provider_id=user_info.get("sub"),
            email=user_info.get("email"),
            full_name=user_info.get("name"),
        )

        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))

        params = urlencode({
            "access_token": access_token,
            "refresh_token": refresh_token,
        })
        return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?{params}")

    except Exception as e:
        params = urlencode({"error": str(e)})
        return RedirectResponse(url=f"{FRONTEND_URL}/login?{params}")


{%- elif cookiecutter.use_sqlite %}


@router.get("/google/callback")
async def google_callback(request: Request, user_service: UserSvc):
    """Handle Google OAuth2 callback."""
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")

        if not user_info:
            params = urlencode({"error": "Failed to get user info from Google"})
            return RedirectResponse(url=f"{FRONTEND_URL}/login?{params}")

        user = user_service.get_or_create_oauth_user(
            provider="google",
            provider_id=user_info.get("sub"),
            email=user_info.get("email"),
            full_name=user_info.get("name"),
        )

        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)

        params = urlencode({
            "access_token": access_token,
            "refresh_token": refresh_token,
        })
        return RedirectResponse(url=f"{FRONTEND_URL}/auth/callback?{params}")

    except Exception as e:
        params = urlencode({"error": str(e)})
        return RedirectResponse(url=f"{FRONTEND_URL}/login?{params}")


{%- endif %}
{%- endif %}
{%- else %}
"""OAuth routes - not configured."""
{%- endif %}
