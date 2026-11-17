import logging
from typing import List, Union

from google import genai
from google.genai import types

from ..LLMInterface import LLMInterface
from ..LLMEnums import DocumentTypeEnum, GeminiEnums


class GeminiProvider(LLMInterface):

    def __init__(self, api_key: str,
                 default_input_max_characters: int = 1000,
                 default_generation_max_output_tokens: int = 1000,
                 default_generation_temperature: float = 0.1,
                 request_timeout_ms: int = 30000):

        self.api_key = api_key

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature
        self.request_timeout_ms = request_timeout_ms

        self.generation_model_id = None

        self.embedding_model_id = None
        self.embedding_size = None

        self.client = genai.Client(api_key=self.api_key)

        self.enums = GeminiEnums
        self.logger = logging.getLogger(__name__)

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()

    @staticmethod
    def _message_text(message: dict) -> str:
        """Read text from this project's prompt dicts or OpenAI-style dicts."""
        parts = message.get("parts")
        if parts:
            first = parts[0]
            if isinstance(first, dict):
                return first.get("text", "")
            return getattr(first, "text", str(first))

        content = message.get("content") or message.get("text") or ""
        if isinstance(content, list):
            if content and isinstance(content[0], dict):
                return content[0].get("text", "")
            return str(content)
        return str(content)

    def generate_text(self, prompt: str, chat_history: list = None,
                      max_output_tokens: int = None,
                      temperature: float = None):

        if not self.client:
            self.logger.error("Gemini client wasn't set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for Gemini wasn't set")
            return None

        max_output_tokens = (
            self.default_generation_max_output_tokens
            if max_output_tokens is None else max_output_tokens
        )
        temperature = (
            self.default_generation_temperature
            if temperature is None else temperature
        )

        # Gemini accepts only "user" and "model" content roles. A system
        # prompt becomes a native system_instruction instead of a fake user
        # turn, so it keeps its role in the request.
        system_instruction = None
        contents = []
        for message in list(chat_history or []):
            role = str(message.get("role", GeminiEnums.USER.value)).lower()
            text = self._message_text(message)
            if role in ("system", GeminiEnums.SYSTEM.value.lower()):
                system_instruction = (
                    f"{system_instruction}\n{text}" if system_instruction else text
                )
                continue
            if role in ("assistant", "chatbot", "model",
                        GeminiEnums.ASSISTANT.value.lower()):
                role = GeminiEnums.ASSISTANT.value
            else:
                role = GeminiEnums.USER.value
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=text)])
            )

        contents.append(
            types.Content(
                role=GeminiEnums.USER.value,
                parts=[types.Part.from_text(text=prompt)],
            )
        )

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            http_options=types.HttpOptions(timeout=self.request_timeout_ms),
        )
        if system_instruction:
            config.system_instruction = system_instruction

        try:
            response = self.client.models.generate_content(
                model=self.generation_model_id,
                contents=contents,
                config=config,
            )
        except Exception as e:
            self.logger.error("Error while generating text with Gemini: %s", e)
            return None

        text = getattr(response, "text", None)
        if not text:
            self.logger.error("Error while generating text with Gemini")
            return None

        return text

    def embed_text(self, text: Union[str, List[str]],
                   document_type: str = None):

        if not self.client:
            self.logger.error("Gemini client wasn't set")
            return None

        if isinstance(text, str):
            text = [text]

        if not self.embedding_model_id:
            self.logger.error("Embedding model for Gemini wasn't set")
            return None

        task_type = (
            "RETRIEVAL_QUERY"
            if document_type == DocumentTypeEnum.QUERY.value
            else "RETRIEVAL_DOCUMENT"
        )
        config_kwargs = {
            "task_type": task_type,
            "http_options": types.HttpOptions(timeout=self.request_timeout_ms),
        }
        if self.embedding_size:
            config_kwargs["output_dimensionality"] = self.embedding_size

        try:
            response = self.client.models.embed_content(
                model=self.embedding_model_id,
                contents=[self.process_text(t) for t in text],
                config=types.EmbedContentConfig(**config_kwargs),
            )
        except Exception as e:
            self.logger.error("Error while embedding text with Gemini: %s", e)
            return None

        embeddings = getattr(response, "embeddings", None)
        if not embeddings:
            self.logger.error("Error while embedding text with Gemini")
            return None

        values = [getattr(rec, "values", None) for rec in embeddings]
        if any(not value for value in values):
            self.logger.error("Error while embedding text with Gemini")
            return None

        return values

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "parts": [{"text": prompt}],
        }
