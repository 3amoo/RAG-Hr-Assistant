# ======================================================
# Import Libs
# ======================================================

from typing import List, Optional

from pydantic import BaseModel


# ======================================================
# Func.
# ======================================================
# - Citation — citation envelope returned with an answer
# - RagAnswer — answer payload with citations and confidence flag
# ======================================================

class Citation(BaseModel):
    chunk_id: Optional[int] = None
    asset_name: Optional[str] = None
    doc_type: Optional[str] = None
    page: Optional[int] = None
    section: Optional[str] = None
    score: float
    quote: str


class RagAnswer(BaseModel):
    answer: str
    citations: List[Citation] = []
    low_confidence: bool = False
