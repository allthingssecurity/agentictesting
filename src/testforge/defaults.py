"""Default configurations per language and tool."""

from testforge.models.enums import Language

LANGUAGE_DEFAULTS: dict[str, dict] = {
    Language.PYTHON: {
        "test_dir": "tests/",
        "test_runner": "pytest",
        "sast": "semgrep",
    },
    Language.JAVASCRIPT: {
        "test_dir": "tests/",
        "test_runner": "jest",
        "sast": "semgrep",
    },
    Language.TYPESCRIPT: {
        "test_dir": "tests/",
        "test_runner": "vitest",
        "sast": "semgrep",
    },
    Language.GO: {
        "test_dir": ".",
        "test_runner": "go-test",
        "sast": "semgrep",
    },
    Language.RUST: {
        "test_dir": ".",
        "test_runner": "cargo-test",
        "sast": "semgrep",
    },
    Language.JAVA: {
        "test_dir": "src/test/",
        "test_runner": "junit5",
        "sast": "semgrep",
    },
    Language.KOTLIN: {
        "test_dir": "src/test/",
        "test_runner": "junit5",
        "sast": "semgrep",
    },
    Language.RUBY: {
        "test_dir": "spec/",
        "test_runner": "rspec",
        "sast": "semgrep",
    },
    Language.CSHARP: {
        "test_dir": ".",
        "test_runner": "dotnet-test",
        "sast": "semgrep",
    },
}
