from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ToolConfig(BaseModel):
    enabled: bool = True
    timeout: int = 120
    extra_args: list[str] = Field(default_factory=list)


class TestForgeManifest(BaseModel):
    project_name: str = "project"
    project_root: str = "."
    test_types: list[str] = Field(default_factory=lambda: ["unit"])

    # Language override (empty = auto-detect)
    languages: list[str] = Field(default_factory=list)

    # Per-type configs
    unit: ToolConfig = Field(default_factory=ToolConfig)
    integration: ToolConfig = Field(default_factory=ToolConfig)
    browser: ToolConfig = Field(default_factory=lambda: ToolConfig(enabled=False))
    api: ToolConfig = Field(default_factory=ToolConfig)
    security: ToolConfig = Field(default_factory=ToolConfig)

    # API
    openapi_spec: str | None = None
    base_url: str = "http://localhost:8000"

    # Healer
    heal_max_attempts: int = 2

    # LLM
    llm: dict = Field(default_factory=lambda: {"model": "gpt-5", "temperature": 0.0})

    # Memory
    memory: dict = Field(default_factory=lambda: {"window_size": 10, "token_budget": 16000})

    # Sandbox
    sandbox: dict = Field(default_factory=lambda: {"mode": "subprocess"})

    # Meta-harness
    meta_harness: dict = Field(default_factory=lambda: {"enabled": False, "auto_evolve": False})

    # Reporting
    reporting: dict = Field(default_factory=lambda: {"formats": ["json", "html", "junit_xml"], "output_dir": "artifacts"})

    # Logging
    logging: dict = Field(default_factory=lambda: {"level": "INFO", "format": "json"})


def load_manifest(path: Path) -> TestForgeManifest:
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return TestForgeManifest(**data)
