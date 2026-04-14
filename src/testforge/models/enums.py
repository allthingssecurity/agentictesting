from enum import StrEnum


class TestType(StrEnum):
    UNIT = "unit"
    INTEGRATION = "integration"
    BROWSER = "browser"
    API = "api"
    SECURITY = "security"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Status(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    SKIPPED = "skipped"
    HEALED = "healed"


class Language(StrEnum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    KOTLIN = "kotlin"
    RUBY = "ruby"
    CSHARP = "csharp"
    CPP = "cpp"
    SWIFT = "swift"


class ToolCategory(StrEnum):
    UNIT_TEST = "unit_test"
    INTEGRATION_TEST = "integration_test"
    E2E_TEST = "e2e_test"
    API_FUZZ = "api_fuzz"
    SAST = "sast"
    DAST = "dast"
    LINT = "lint"
