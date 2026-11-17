from helpers.config import get_settings


def test_security_and_retrieval_defaults():
    settings = get_settings()
    assert settings.API_KEY == ""
    assert settings.METRICS_PATH == "/metrics"
    assert settings.MIN_RETRIEVAL_SCORE == 0.25
    assert settings.FLOWER_AUTH_USER == "admin"
