import importlib
from types import SimpleNamespace

from stores.llm.LLMEnums import DocumentTypeEnum, GeminiEnums, LLMEnums
from stores.llm.LLMProviderFactory import LLMProviderFactory
from stores.llm.providers.GeminiProvider import GeminiProvider


class _Models:
    def __init__(self):
        self.generate_calls = []
        self.embed_calls = []

    def generate_content(self, **kwargs):
        self.generate_calls.append(kwargs)
        return SimpleNamespace(text="grounded answer")

    def embed_content(self, **kwargs):
        self.embed_calls.append(kwargs)
        return SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3])])


class _Client:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.models = _Models()


def _install_fake_client(monkeypatch):
    module = importlib.import_module("stores.llm.providers.GeminiProvider")
    monkeypatch.setattr(module.genai, "Client", _Client)


def test_generate_text_uses_gemini_roles_and_system_instruction(monkeypatch):
    _install_fake_client(monkeypatch)
    provider = GeminiProvider(api_key="test-key")
    provider.set_generation_model("gemini-2.5-flash")

    history = [
        provider.construct_prompt("You are an HR assistant.", GeminiEnums.SYSTEM.value),
        provider.construct_prompt("Earlier answer.", GeminiEnums.ASSISTANT.value),
    ]
    answer = provider.generate_text(
        "What is the leave policy?",
        chat_history=history,
        max_output_tokens=50,
        temperature=0.0,
    )

    assert answer == "grounded answer"
    call = provider.client.models.generate_calls[0]
    assert call["model"] == "gemini-2.5-flash"
    assert [content.role for content in call["contents"]] == ["model", "user"]
    assert call["config"].system_instruction == "You are an HR assistant."
    assert call["config"].temperature == 0.0
    assert call["config"].max_output_tokens == 50
    assert call["config"].http_options.timeout == 30000


def test_embed_text_sets_task_type_and_dimensionality(monkeypatch):
    _install_fake_client(monkeypatch)
    provider = GeminiProvider(api_key="test-key")
    provider.set_embedding_model("gemini-embedding-001", 768)

    values = provider.embed_text(
        "policy chunk", document_type=DocumentTypeEnum.DOCUMENT.value
    )
    provider.embed_text("policy question", document_type=DocumentTypeEnum.QUERY.value)

    assert values == [[0.1, 0.2, 0.3]]
    document_call, query_call = provider.client.models.embed_calls
    assert document_call["config"].task_type == "RETRIEVAL_DOCUMENT"
    assert query_call["config"].task_type == "RETRIEVAL_QUERY"
    assert document_call["config"].output_dimensionality == 768
    assert document_call["config"].http_options.timeout == 30000
    assert document_call["contents"] == ["policy chunk"]


def test_factory_builds_gemini_provider_from_settings(monkeypatch):
    _install_fake_client(monkeypatch)
    config = SimpleNamespace(
        OPENAI_API_KEY="",
        OPENAI_API_URL="",
        COHERE_API_KEY="",
        GEMINI_API_KEY="test-key",
        INPUT_DAFAULT_MAX_CHARACTERS=1000,
        GENERATION_DAFAULT_MAX_TOKENS=200,
        GENERATION_DAFAULT_TEMPERATURE=0.1,
    )

    provider = LLMProviderFactory(config).create(LLMEnums.GEMINI.value)

    assert isinstance(provider, GeminiProvider)
    assert provider.client.api_key == "test-key"
