"""Configuration regressions; no external API calls."""
from pathlib import Path

import pytest

from integrations import integracao_openai as module


@pytest.fixture
def project(tmp_path, monkeypatch):
    source = tmp_path / "analise-medica-api/integrations/integracao_openai.py"
    source.parent.mkdir(parents=True)
    monkeypatch.setattr(module, "__file__", str(source))
    for key in ("OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
    other = tmp_path / "unrelated"
    other.mkdir()
    monkeypatch.chdir(other)
    return tmp_path


def test_root_file_is_loaded_independently_of_working_directory(project):
    (project / ".env").write_text(
        "OPENAI_API_KEY=test-root\nOPENAI_MODEL=test-model\n"
        "OPENAI_BASE_URL=https://example.invalid/v1\n", encoding="utf-8"
    )
    (project / "analise-medica-api/.env").write_text(
        "OPENAI_API_KEY=legacy-value\n", encoding="utf-8"
    )
    config = module.IntegracaoOpenAI()
    assert config.api_key == "test-root"
    assert config.modelo == "test-model"
    assert config.base_url == "https://example.invalid/v1"
    config.verificar_configuracao()


def test_injected_environment_has_priority_over_root_file(project, monkeypatch):
    (project / ".env").write_text(
        "OPENAI_API_KEY=file-key\nOPENAI_MODEL=file-model\n"
        "OPENAI_BASE_URL=https://file.invalid/v1\n", encoding="utf-8"
    )
    monkeypatch.setenv("OPENAI_API_KEY", " injected-key ")
    monkeypatch.setenv("OPENAI_MODEL", " injected-model ")
    monkeypatch.setenv("OPENAI_BASE_URL", " https://injected.invalid/v1 ")
    config = module.IntegracaoOpenAI()
    assert config.api_key == "injected-key"
    assert config.modelo == "injected-model"
    assert config.base_url == "https://injected.invalid/v1"
    config.verificar_configuracao()


def test_missing_file_allows_environment_only_configuration(project, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "environment-key")
    config = module.IntegracaoOpenAI()
    config.verificar_configuracao()
    assert config.api_key == "environment-key"


def test_legacy_file_is_not_used_and_missing_key_is_reported(project):
    (project / "analise-medica-api/.env").write_text(
        "OPENAI_API_KEY=legacy-key\n", encoding="utf-8"
    )
    config = module.IntegracaoOpenAI()
    with pytest.raises(module.ErroConfiguracaoAnaliseIA, match="OPENAI_API_KEY"):
        config.verificar_configuracao()


@pytest.mark.parametrize("key", ["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL"])
def test_blank_environment_values_are_rejected(project, monkeypatch, key):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv(key, "   ")
    with pytest.raises(module.ErroConfiguracaoAnaliseIA, match=key):
        module.IntegracaoOpenAI().verificar_configuracao()
