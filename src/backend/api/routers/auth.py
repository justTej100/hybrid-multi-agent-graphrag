from __future__ import annotations

"""Session-cookie auth helpers + Google OAuth routes + /me + /logout.

Google OAuth accepts any signed-in Google account. ADMIN_EMAIL (comma-separated)
marks admin users who get unlimited chat and mutation/admin routes.
"""

import os
from time import time

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, SignatureExpired, TimestampSigner

from router.rate_limit import get_chat_usage, usage_status

COOKIE_NAME = 'argus_session'
MAX_AGE_SECONDS = 60 * 60 * 24 * 30


# ---------------------------------------------------------------------------
# Session-cookie helpers (used as FastAPI dependencies by other routers)
# ---------------------------------------------------------------------------
def _signer() -> TimestampSigner:
    """Return the signer used for the session cookie."""
    secret = os.environ.get('SECRET_KEY') or 'dev-argus-secret'
    return TimestampSigner(secret)


def _secure_cookie() -> bool:
    """Return True when cookies should be marked secure in production."""
    return os.environ.get('ENVIRONMENT', '').lower() in {'prod', 'production'}


def _session_payload(email: str) -> str:
    return f'argus:{email}:{int(time())}'


def issue_session_token(email: str) -> str:
    """Return a signed session token for the given email (tests only)."""
    return _signer().sign(_session_payload(email).encode()).decode()


def set_session_cookie(response: Response, email: str) -> None:
    """Set the signed session cookie for an authenticated user."""
    token = issue_session_token(email)
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        secure=_secure_cookie(),
        samesite='lax',
        max_age=MAX_AGE_SECONDS,
        path='/',
    )


def clear_session_cookie(response: Response) -> None:
    """Remove the session cookie."""
    response.delete_cookie(
        COOKIE_NAME,
        httponly=True,
        secure=_secure_cookie(),
        samesite='lax',
        path='/',
    )


def allowed_emails() -> set[str]:
    """Return admin emails from comma-separated ADMIN_EMAIL."""
    raw = os.environ.get('ADMIN_EMAIL', '')
    emails = {part.strip().lower() for part in raw.split(',') if part.strip()}
    if not emails:
        raise HTTPException(status_code=500, detail='ADMIN_EMAIL is not configured.')
    return emails


def is_admin_email(email: str | None) -> bool:
    """Return True when email is in the ADMIN_EMAIL allowlist."""
    if not email:
        return False
    try:
        return email.strip().lower() in allowed_emails()
    except HTTPException:
        return False


def normalize_login_email(email: str | None) -> str:
    """Accept any non-empty Google email for session creation."""
    if not email or not str(email).strip():
        raise HTTPException(status_code=400, detail='Google account did not provide an email.')
    return str(email).strip()


def verify_admin_email(email: str | None) -> str:
    """Return the email when it is an admin; otherwise raise 403.

    Kept for tests and explicit admin checks; login no longer uses this gate.
    """
    if not email or email.strip().lower() not in allowed_emails():
        raise HTTPException(status_code=403, detail='Email is not authorized.')
    return email.strip()


def session_is_valid(request: Request) -> bool:
    """Check whether the request carries a valid login cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return False
    try:
        value = _signer().unsign(token, max_age=MAX_AGE_SECONDS).decode()
    except (BadSignature, SignatureExpired):
        return False
    parts = value.split(':', 2)
    return len(parts) == 3 and parts[0] == 'argus' and bool(parts[1])


def get_session_email(request: Request) -> str | None:
    """Return the authenticated email from the session cookie, if any."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        value = _signer().unsign(token, max_age=MAX_AGE_SECONDS).decode()
    except (BadSignature, SignatureExpired):
        return None
    parts = value.split(':', 2)
    if len(parts) != 3 or parts[0] != 'argus' or not parts[1]:
        return None
    return parts[1]


def require_session(request: Request) -> None:
    """Raise HTTP 401 when the request is not authenticated."""
    if not session_is_valid(request):
        raise HTTPException(status_code=401, detail='Login required.')


def require_admin(request: Request) -> None:
    """Raise 401 if logged out, 403 if logged in but not an admin."""
    require_session(request)
    email = get_session_email(request)
    if not is_admin_email(email):
        raise HTTPException(status_code=403, detail='Admin access required.')


# ---------------------------------------------------------------------------
# OAuth client + routes
# ---------------------------------------------------------------------------
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

router = APIRouter(tags=['Auth'])


@router.get('/auth/google')
async def auth_google(request: Request):
    redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI')
    if not redirect_uri:
        raise HTTPException(status_code=500, detail='GOOGLE_REDIRECT_URI is not configured.')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get('/auth/google/callback')
async def auth_google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get('userinfo')
        if not userinfo:
            userinfo = await oauth.google.parse_id_token(request, token)
        email = normalize_login_email(userinfo.get('email') if userinfo else None)
        response = RedirectResponse(url='/', status_code=302)
        set_session_cookie(response, email)
        return response
    except HTTPException as exc:
        if exc.status_code == 400:
            return RedirectResponse(url='/login?error=oauth_failed', status_code=302)
        raise
    except Exception:
        return RedirectResponse(url='/login?error=oauth_failed', status_code=302)


@router.get('/logout')
def logout() -> RedirectResponse:
    response = RedirectResponse(url='/login', status_code=302)
    clear_session_cookie(response)
    return response


@router.get('/me', dependencies=[Depends(require_session)])
async def me(request: Request) -> dict:
    email = get_session_email(request) or ''
    admin = is_admin_email(email)
    usage = await get_chat_usage(email) if email else {}
    return {
        'email': email,
        'is_admin': admin,
        'chat': usage_status(usage, is_admin=admin),
    }