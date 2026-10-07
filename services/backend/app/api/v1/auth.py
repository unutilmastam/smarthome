from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import Principal, client_ip, get_db, get_principal
from app.core.config import Settings, get_settings
from app.core.responses import ok
from app.schemas.auth import LoginIn, PasswordChangeIn, PinSetIn, RefreshIn
from app.services import auth as svc

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db),
          settings: Settings = Depends(get_settings)):
    data = svc.login(db, settings, body.email, body.password, client_ip(request),
                     request.headers.get("user-agent"))
    return ok(data)


@router.post("/refresh")
def refresh(body: RefreshIn, request: Request, db: Session = Depends(get_db),
            settings: Settings = Depends(get_settings)):
    return ok(svc.refresh(db, settings, body.refresh_token, client_ip(request)))


@router.post("/logout")
def logout(request: Request, p: Principal = Depends(get_principal),
           db: Session = Depends(get_db)):
    svc.logout(db, p.user, p.session, client_ip(request))
    return ok({"logged_out": True})


@router.post("/logout-all")
def logout_all(request: Request, p: Principal = Depends(get_principal),
               db: Session = Depends(get_db)):
    n = svc.logout_all(db, p.user, client_ip(request))
    return ok({"sessions_revoked": n})


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
