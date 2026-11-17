from typing import List, Optional

from pydantic import BaseModel


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
