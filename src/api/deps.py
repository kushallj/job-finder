"""Shared FastAPI dependencies, defined once (DRY) instead of in every handler.

    from src.api.deps import CURRENT_USER, DB_SESSION

    @router.get("/things")
    def list_things(user: User = CURRENT_USER, db: Session = DB_SESSION) -> ...: ...

Why constants, not ``Annotated[User, Depends(...)]`` aliases: FastAPI 0.104 (pinned) only
handles ``Annotated`` metadata with the pinned pydantic 2.5; newer pydantic installs drop it
(``FieldInfo has no attribute in_``). Switch to ``Annotated`` aliases after upgrading FastAPI.
"""

from __future__ import annotations

from fastapi import Depends

from src.auth.dependencies import get_current_user
from src.database import get_db

CURRENT_USER = Depends(get_current_user)
DB_SESSION = Depends(get_db)
