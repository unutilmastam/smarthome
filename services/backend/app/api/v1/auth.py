import uuid
from typing import Optional

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import Principal, client_ip, get_db, get_principal
from app.core.config import Settings, get_settings
from app.core.errors import auth_required, not_found
from app.core.responses import ok
from app.core.security import REFRESH_TOKEN_TTL
from app.schemas.auth import LoginIn, PasswordChangeIn, PinSetIn, RefreshIn
from app.services import auth as svc
from app.services.device_view import iso

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE = "sh_refresh"
COOKIE_PATH = "/api/v1/auth"


def is_web(request: Request) -> bool:
    """ADR 0009: browsers send X-Client: web and keep the refresh token in a cookie."""
    return request.headers.get("x-client", "").lower() == "web"


def _token_response(request: Request, settings: Settings, data: dict) -> JSONResponse:
    if not is_web(request):
        return JSONResponse(ok(data))
    refresh = data.pop("refresh_token")
    resp = JSONResponse(ok(data))
    resp.set_cookie(COOKIE, refresh, max_age=int(REFRESH_TOKEN_TTL.total_seconds()),
                    path=COOKIE_PATH, httponly=True, secure=settings.cookie_secure,
                    samesite="strict")
    return resp


def _clear_cookie(resp: JSONResponse, settings: Settings) -> JSONResponse:
    resp.delete_cookie(COOKIE, path=COOKIE_PATH, httponly=True, secure=settings.cookie_secure,
                       samesite="strict")
    return resp


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db),
          settings: Settings = Depends(get_settings)):
    data = svc.login(db, settings, body.email, body.password, client_ip(request),
                     request.headers.get("user-agent"))
    return _token_response(request, settings, data)


@router.post("/refresh")
def refresh(request: Request, body: Optional[RefreshIn] = Body(default=None),
            db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    token = body.refresh_token if body else None
    if token is None and is_web(request):
        token = request.cookies.get(COOKIE)
    if not token:
        raise auth_required("Refresh token required")
    data = svc.refresh(db, settings, token, client_ip(request))
    return _token_response(request, settings, data)


@router.post("/logout")
def logout(request: Request, p: Principal = Depends(get_principal),
           db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    svc.logout(db, p.user, p.session, client_ip(request))
    return _clear_cookie(JSONResponse(ok({"logged_out": True})), settings)


@router.post("/logout-all")
def logout_all(request: Request, p: Principal = Depends(get_principal),
               db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    n = svc.logout_all(db, p.user, client_ip(request))
    return _clear_cookie(JSONResponse(ok({"sessions_revoked": n})), settings)


@router.get("/me")
def me(p: Principal = Depends(get_principal)):
    return ok(svc.user_out(p.user))


@router.post("/password")
def change_password(body: PasswordChangeIn, request: Request,
                    p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    n, _ = svc.change_password(db, p.user, p.session, body.current_password,
                               body.new_password, client_ip(request))
    return ok({"changed": True, "other_sessions_revoked": n})


@router.post("/pin")
def set_pin(body: PinSetIn, request: Request, p: Principal = Depends(get_principal),
            db: Session = Depends(get_db)):
    svc.set_pin(db, p.user, body.password, body.pin, client_ip(request))
    return ok({"pin_set": True})


@router.get("/sessions")
def list_sessions(p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    return ok([
        {"id": str(s.id), "current": s.id == p.session.id, "ip": s.ip,
         "user_agent": s.user_agent, "created_at": iso(s.created_at),
         "last_used_at": iso(s.last_used_at), "expires_at": iso(s.expires_at)}
        for s in svc.active_sessions(db, p.user)
    ])


@router.delete("/sessions/{session_id}")
def revoke_session(session_id: uuid.UUID, request: Request,
                   p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    if not svc.revoke_session(db, p.user, session_id, client_ip(request)):
        raise not_found("Session")
    return ok({"revoked": True, "current": session_id == p.session.id})
