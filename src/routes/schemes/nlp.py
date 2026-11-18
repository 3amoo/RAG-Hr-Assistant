# ======================================================
# Import Libs
# ======================================================

from pydantic import BaseModel
from typing import Optional


# ======================================================
# Func.
# ======================================================
# - PushRequest — request schema for queue-and-process jobs
# - SearchRequest — request schema for search and answer calls
# ======================================================

class PushRequest(BaseModel):
    do_reset: Optional[int] = 0

class SearchRequest(BaseModel):
    text: str
    limit: Optional[int] = 5
