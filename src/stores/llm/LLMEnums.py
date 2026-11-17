from enum import Enum

class LLMEnums(Enum):
    OPENAI = "OPENAI"
    COHERE = "COHERE"
    GEMINI = "GEMINI"

class OpenAIEnums(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class CoHereEnums(Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "CHATBOT"

    DOCUMENT = "search_document"
    QUERY = "search_query"


class GeminiEnums(Enum):
    # Only "user" and "model" are valid Content roles in the Gemini API.
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "model"



class DocumentTypeEnum(Enum):
    DOCUMENT = "document"
    QUERY = "query"