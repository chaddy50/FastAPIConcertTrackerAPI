from typing import Annotated, Optional
from uuid import UUID

from pydantic import AfterValidator


def _validate_uuid(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    UUID(value)  # raises ValueError -> 422 for malformed ids
    return value  # preserve the exact string for verbatim echo


# Optional client-supplied primary key; None means "server generates it".
ClientSuppliedId = Annotated[Optional[str], AfterValidator(_validate_uuid)]
