# ======================================================
# Import Libs
# ======================================================

import os
from dataclasses import dataclass, field
from typing import List

from models import ProcessingEnum

from .BaseController import BaseController
from .ProjectController import ProjectController


# ======================================================
# Func.
# ======================================================
# - Document — in-memory representation of a processed document
# - ProcessController — convert uploaded files into clean text chunks
#   - __init__ — initialize instance state and dependencies
#   - get_file_extension — normalize the file extension
#   - get_file_content — read text from PDF or TXT files
#   - process_file_content — split raw text into overlapping chunks
#   - process_simpler_splitter — fallback character-based text splitter
# ======================================================

try:  # PyMuPDF >= 1.24 exposes the `pymupdf` module name
    import pymupdf
except ImportError:  # pragma: no cover - fallback for older PyMuPDF
    import fitz as pymupdf


@dataclass
class Document:
    page_content: str
    metadata: dict = field(default_factory=dict)


class ProcessController(BaseController):

    def __init__(self, project_id: str):
        super().__init__()

        self.project_id = project_id
        self.project_path = ProjectController().get_project_path(project_id=project_id)

    def get_file_extension(self, file_id: str):
        return os.path.splitext(file_id)[-1].lower()

    def get_file_content(self, file_id: str):
        file_ext = self.get_file_extension(file_id=file_id)
        file_path = os.path.join(self.project_path, file_id)

        if not os.path.exists(file_path):
            return None

        if file_ext == ProcessingEnum.TXT.value:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return [Document(page_content=f.read(), metadata={"source": file_id})]

        if file_ext == ProcessingEnum.PDF.value:
            documents = []
            with pymupdf.open(file_path) as pdf:
                for page in pdf:
                    documents.append(
                        Document(
                            page_content=page.get_text("text"),
                            metadata={
                                "source": file_id,
                                "page": page.number + 1,
                            },
                        )
                    )
            return documents

        return None

    def process_file_content(self, file_content: list, file_id: str,
                             chunk_size: int = 100, overlap_size: int = 20):
        chunks = []

        for record in file_content:
            metadata = dict(record.metadata or {})
            metadata.setdefault("source", file_id)
            chunks.extend(
                self.process_simpler_splitter(
                    text=record.page_content,
                    metadata=metadata,
                    chunk_size=chunk_size,
                    overlap_size=overlap_size,
                )
            )

        return chunks

    def process_simpler_splitter(self, text: str, metadata: dict,
                                 chunk_size: int, overlap_size: int = 20):
        text = (text or "").strip()
        if not text:
            return []

        chunk_size = max(int(chunk_size or 100), 1)
        overlap_size = max(int(overlap_size or 0), 0)
        overlap_size = min(overlap_size, chunk_size - 1)

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + chunk_size, text_length)

            # Prefer a natural boundary when one is close to the limit.
            if end < text_length:
                newline = text.rfind("\n", start, end)
                if newline > start + chunk_size // 2:
                    end = newline
                else:
                    space = text.rfind(" ", start, end)
                    if space > start + chunk_size // 2:
                        end = space

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    Document(page_content=chunk_text, metadata=dict(metadata))
                )

            if end >= text_length:
                break

            start = max(end - overlap_size, start + 1)

        return chunks
