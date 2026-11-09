"""Shared FastAPI dependencies, defined once (DRY) instead of in every handler.

    from src.api.deps import CURRENT_USER, DB_SESSION

    @router.get("/things")
    def list_things(user: User = CURRENT_USER, db: Session = DB_SESSION) -> ...: ...

Constants rather than ``Annotated[User, Depends(...)]`` aliases date from FastAPI 0.104, whose
``Annotated`` handling broke under newer pydantic. FastAPI is now 0.146, so ``Annotated``
aliases would work; migrating is optional style work, not a fix.
"""

from __future__ import annotations

from fastapi import Depends

from src.auth.dependencies import get_current_user
from src.database import get_db

CURRENT_USER = Depends(get_current_user)
DB_SESSION = Depends(get_db)
