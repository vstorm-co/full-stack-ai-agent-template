"""OAuth2 client configuration."""

from authlib.integrations.starlette_client import OAuth

from app.core.config import settings

oauth = OAuth()

# Configure Google OAuth2
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
