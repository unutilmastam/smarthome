import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    Principal, client_ip, get_contracts, get_db, get_principal, get_realtime,
    membership_or_404,
)
from app.core.config import Settings, get_settings
from app.core.contracts import Contracts
from app.core.errors import ApiError, not_found
from app.core.responses import ok
from app.models import Command, Device
from app.schemas.commands import CommandIn
from app.schemas.common import Page
from app.services.commands import command_view, create_command, expire_due

router = APIRouter(tags=["commands"])


@router.post("/commands", status_code=201)
def post_command(body: CommandIn, request: Request, p: Principal = Depends(get_principal),
                 db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
                 contracts: Contracts = Depends(get_contracts),
                 realtime=Depends(get_realtime)):
    cmd, created = create_command(db, settings, contracts, p.user, body, client_ip(request),
                                  realtime)
    if not created:
        return JSONResponse(ok(command_view(cmd), {"idempotent_replay": True}), status_code=200)
    return ok(command_view(cmd))


@router.get("/commands/{command_id}")
def get_command(command_id: uuid.UUID, p: Principal = Depends(get_principal),
                db: Session = Depends(get_db), settings: Settings = Depends(get_settings),
                contracts: Contracts = Depends(get_contracts)):
    c = db.get(Command, command_id)
    if c is None:
        raise not_found("Command")
    try:
        membership_or_404(db, c.home_id, p.user)
    except ApiError:
        raise not_found("Command")
    expire_due(db, settings, contracts, home_id=c.home_id)
    db.refresh(c)
    return ok(command_view(c))


@router.get("/devices/{device_id}/commands")
def device_commands(device_id: uuid.UUID, page: Page = Depends(),
                    p: Principal = Depends(get_principal), db: Session = Depends(get_db),
                    settings: Settings = Depends(get_settings),
                    contracts: Contracts = Depends(get_contracts)):
    d = db.get(Device, device_id)
    if d is None:
        raise not_found("Device")
    try:
        membership_or_404(db, d.home_id, p.user)
    except ApiError:
        raise not_found("Device")
    expire_due(db, settings, contracts, home_id=d.home_id)
    base = select(Command).where(Command.device_id == device_id)
    total = db.scalar(select(func.count()).select_from(base.subquery()))
    rows = db.scalars(base.order_by(Command.created_at.desc()).limit(page.limit)
                      .offset(page.offset)).all()
    return ok([command_view(c, with_events=False) for c in rows], page.meta(total))
