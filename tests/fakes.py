from models.db_schemes import RetrievedDocument


class FakeEnums:
    SYSTEM = type("SystemRole", (), {"value": "system"})()


class FakeGeneration:
    enums = FakeEnums()

    def __init__(self, answer="Here is the answer."):
        self.answer = answer

    def process_text(self, text):
        return text

    def construct_prompt(self, prompt, role):
        return {"role": role, "content": prompt}

    def generate_text(self, prompt, chat_history=None):
        return self.answer


class FakeEmbedding:
    embedding_size = 1024

    def embed_text(self, text, document_type=None):
        return [[0.1] * self.embedding_size]


class FakeVectorDB:
    default_vector_size = 1024

    def __init__(self, documents):
        self.documents = documents

    async def search_by_vector(self, collection_name, vector, limit):
        return self.documents[:limit]


class FakeProject:
    project_id = 1


def document(text, score, chunk_id=1, metadata=None):
    return RetrievedDocument(
        text=text,
        score=score,
        chunk_id=chunk_id,
        metadata=metadata or {},
    )
