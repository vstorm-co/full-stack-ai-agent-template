"""OAuth2 authentication routes."""

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.api.deps import UserSvc
from app.core.config import settings
from app.core.oauth import oauth
from app.core.security import create_access_token, create_refresh_token

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/google/login")
async def google_login(request: Request):
    """Redirect to Google OAuth2 login page."""
    return await oauth.google.authorize_redirect(request, settings.GOOGLE_REDIRECT_URI)


@router.get("/google/callback")
async def google_callback(request: Request, user_service: UserSvc):
    """Handle Google OAuth2 callback."""
    frontend = settings.FRONTEND_URL.rstrip("/")
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")

        if not user_info:
            params = urlencode({"error": "Failed to get user info from Google"})
            return RedirectResponse(url=f"{frontend}/login?{params}")

        user = await user_service.get_or_create_oauth_user(
            provider="google",
            provider_id=user_info.get("sub"),
            email=user_info.get("email"),
            full_name=user_info.get("name"),
        )

        access_token = create_access_token(subject=str(user.id))
        refresh_token = create_refresh_token(subject=str(user.id))

        params = urlencode(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        )
        return RedirectResponse(url=f"{frontend}/auth/callback?{params}")

    except Exception:
        logger.exception("google_oauth_callback_failed")
        params = urlencode({"error": "Sign-in failed. Please try again."})
        return RedirectResponse(url=f"{frontend}/login?{params}")
