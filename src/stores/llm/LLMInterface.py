# ======================================================
# Import Libs
# ======================================================

from abc import ABC, abstractmethod


# ======================================================
# Func.
# ======================================================
# - LLMInterface — abstract contract for LLM providers
#   - set_generation_model — select the generation model id
#   - set_embedding_model — select the embedding model and size
#   - generate_text — generate a grounded text response
#   - embed_text — embed one or more text inputs
#   - construct_prompt — build a provider-specific message dict
# ======================================================

class LLMInterface(ABC):

    @abstractmethod
    def set_generation_model(self, model_id: str):
        pass

    @abstractmethod
    def set_embedding_model(self, model_id: str, embedding_size: int):
        pass

    @abstractmethod
    def generate_text(self, prompt: str, chat_history: list = None,
                      max_output_tokens: int = None, temperature: float = None):
        pass

    @abstractmethod
    def embed_text(self, text, document_type: str = None):
        pass

    @abstractmethod
    def construct_prompt(self, prompt: str, role: str):
        pass
