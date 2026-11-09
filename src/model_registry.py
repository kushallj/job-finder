"""Import every module that declares tables on `src.models.Base`, in one place.

`Base.metadata` only knows the tables whose modules have been imported. Alembic
(`alembic/env.py`) and `create_all` (`src/database.py`) both call `load_all_models()`,
so autogenerate, `alembic check` and local schema creation always see the same tables.
A new module with `__tablename__` classes must be added here, or Alembic will offer
to drop its tables.
"""

from __future__ import annotations

import importlib

MODEL_MODULES = (
    "src.models",
    "src.answer_bank.models",
    "src.nextraise.models",
    "src.tsenta.models",
    "src.workday.models",
)


def load_all_models() -> None:
    for name in MODEL_MODULES:
        importlib.import_module(name)
