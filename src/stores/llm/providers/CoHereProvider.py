# ======================================================
# Import Libs
# ======================================================

import logging
from typing import List, Union

import cohere
from cohere.types.message import ChatbotMessage, SystemMessage, UserMessage

from ..LLMEnums import CoHereEnums, DocumentTypeEnum
from ..LLMInterface import LLMInterface


# ======================================================
# Func.
# ======================================================
# - CoHereProvider — Cohere implementation of LLMInterface
#   - __init__ — initialize instance state and dependencies
#   - set_generation_model — select the generation model id
#   - set_embedding_model — select the embedding model and size
#   - process_text — truncate and trim text to configured limit
#   - generate_text — generate a grounded text response
#   - embed_text — embed one or more text inputs
#   - construct_prompt — build a provider-specific message dict
# ======================================================

logger = logging.getLogger(__name__)


class CoHereProvider(LLMInterface):

    def __init__(self, api_key: str,
                 default_input_max_characters: int = 1000,
                 default_generation_max_output_tokens: int = 1000,
                 default_generation_temperature: float = 0.1):

        self.api_key = api_key

        self.default_input_max_characters = default_input_max_characters
        self.default_generation_max_output_tokens = default_generation_max_output_tokens
        self.default_generation_temperature = default_generation_temperature

        self.generation_model_id = None

        self.embedding_model_id = None
        self.embedding_size = None

        self.client = cohere.Client(api_key=self.api_key)

        self.enums = CoHereEnums
        self.logger = logger

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def process_text(self, text: str):
        return text[:self.default_input_max_characters].strip()

    def generate_text(self, prompt: str, chat_history: list = None,
                      max_output_tokens: int = None, temperature: float = None):

        if not self.client:
            self.logger.error("CoHere client was not set")
            return None

        if not self.generation_model_id:
            self.logger.error("Generation model for CoHere was not set")
            return None

        max_output_tokens = (
            max_output_tokens or self.default_generation_max_output_tokens
        )
        temperature = temperature if temperature is not None else self.default_generation_temperature

        preamble = None
        history = []

        for message in chat_history or []:
            role = str(message.get("role", "USER")).upper()
            content = (
                message.get("text")
                or message.get("content")
                or message.get("message")
                or ""
            )

            if role == CoHereEnums.SYSTEM.value:
                preamble = content
            elif role in (CoHereEnums.USER.value, "USER"):
                history.append(UserMessage(message=content))
            else:
                history.append(ChatbotMessage(message=content))

        response = self.client.chat(
            model=self.generation_model_id,
            message=self.process_text(prompt),
            preamble=preamble,
            chat_history=history or None,
            temperature=temperature,
            max_tokens=max_output_tokens,
        )

        if not response or not response.text:
            self.logger.error("Error while generating text with CoHere")
            return None

        return response.text

    def embed_text(self, text: Union[str, List[str]], document_type: str = None):
        if not self.client:
            self.logger.error("CoHere client was not set")
            return None

        if isinstance(text, str):
            text = [text]

        if not self.embedding_model_id:
            self.logger.error("Embedding model for CoHere was not set")
            return None

        input_type = CoHereEnums.DOCUMENT.value
        if document_type == DocumentTypeEnum.QUERY.value:
            input_type = CoHereEnums.QUERY.value

        response = self.client.embed(
            model=self.embedding_model_id,
            texts=[self.process_text(t) for t in text],
            input_type=input_type,
            embedding_types=["float"],
        )

        if not response or not response.embeddings:
            self.logger.error("Error while embedding text with CoHere")
            return None

        embeddings = response.embeddings
        floats = getattr(embeddings, "float_", None)
        if floats is None:
            floats = getattr(embeddings, "float", None)
        if floats is None:
            floats = embeddings

        return [embedding for embedding in floats]

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "text": prompt,
        }
