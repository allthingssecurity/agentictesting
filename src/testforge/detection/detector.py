from pathlib import Path

from testforge.models.enums import Language

# Package files → language
PACKAGE_FILES: dict[str, Language] = {
    "pyproject.toml": Language.PYTHON,
    "setup.py": Language.PYTHON,
    "setup.cfg": Language.PYTHON,
    "requirements.txt": Language.PYTHON,
    "Pipfile": Language.PYTHON,
    "package.json": Language.JAVASCRIPT,
    "Cargo.toml": Language.RUST,
    "go.mod": Language.GO,
    "pom.xml": Language.JAVA,
    "build.gradle": Language.JAVA,
    "build.gradle.kts": Language.KOTLIN,
    "Gemfile": Language.RUBY,
    "*.csproj": Language.CSHARP,
    "Package.swift": Language.SWIFT,
}

# File extensions → language
EXTENSION_MAP: dict[str, Language] = {
    ".py": Language.PYTHON,
    ".js": Language.JAVASCRIPT,
    ".jsx": Language.JAVASCRIPT,
    ".ts": Language.TYPESCRIPT,
    ".tsx": Language.TYPESCRIPT,
    ".go": Language.GO,
    ".rs": Language.RUST,
    ".java": Language.JAVA,
    ".kt": Language.KOTLIN,
    ".kts": Language.KOTLIN,
    ".rb": Language.RUBY,
    ".cs": Language.CSHARP,
    ".cpp": Language.CPP,
    ".cc": Language.CPP,
    ".c": Language.CPP,
    ".h": Language.CPP,
    ".swift": Language.SWIFT,
}

SKIP_DIRS = {
    "node_modules", ".venv", "venv", "__pycache__", ".git", "target",
    "build", "dist", "vendor", ".tox", ".mypy_cache", ".pytest_cache",
    "bin", "obj", ".next", ".nuxt",
}


class LanguageDetector:
    """Detect languages in a project by scanning package files and extensions."""

    def detect(self, project_root: Path) -> set[Language]:
        languages = set()

        # Phase 1: package file scan
        for filename, lang in PACKAGE_FILES.items():
            if "*" in filename:
                if list(project_root.glob(filename)):
                    languages.add(lang)
            elif (project_root / filename).exists():
                languages.add(lang)

        # TypeScript detection
        if (project_root / "tsconfig.json").exists():
            languages.add(Language.TYPESCRIPT)

        # Phase 2: extension sampling (walk top 3 levels)
        ext_counts: dict[Language, int] = {}
        for f in self._walk(project_root, max_depth=3):
            lang = EXTENSION_MAP.get(f.suffix.lower())
            if lang:
                ext_counts[lang] = ext_counts.get(lang, 0) + 1

        # Add languages with >= 3 source files
        for lang, count in ext_counts.items():
            if count >= 3:
                languages.add(lang)

        return languages

    def detect_with_confidence(self, project_root: Path) -> dict[Language, float]:
        """Return confidence scores (0-1) per language."""
        scores: dict[Language, float] = {}

        # Package files give high confidence
        for filename, lang in PACKAGE_FILES.items():
            if "*" in filename:
                if list(project_root.glob(filename)):
                    scores[lang] = max(scores.get(lang, 0), 0.9)
            elif (project_root / filename).exists():
                scores[lang] = max(scores.get(lang, 0), 0.9)

        if (project_root / "tsconfig.json").exists():
            scores[Language.TYPESCRIPT] = max(scores.get(Language.TYPESCRIPT, 0), 0.9)

        # Extension counts give proportional confidence
        ext_counts: dict[Language, int] = {}
        total_files = 0
        for f in self._walk(project_root, max_depth=3):
            lang = EXTENSION_MAP.get(f.suffix.lower())
            if lang:
                ext_counts[lang] = ext_counts.get(lang, 0) + 1
                total_files += 1

        if total_files > 0:
            for lang, count in ext_counts.items():
                ratio = count / total_files
                ext_score = min(ratio * 2, 0.8)  # Cap at 0.8 from extensions alone
                scores[lang] = max(scores.get(lang, 0), ext_score)

        return scores

    def _walk(self, root: Path, max_depth: int = 3, _depth: int = 0):
        if _depth >= max_depth or not root.is_dir():
            return
        try:
            for entry in root.iterdir():
                if entry.name in SKIP_DIRS:
                    continue
                if entry.is_file():
                    yield entry
                elif entry.is_dir():
                    yield from self._walk(entry, max_depth, _depth + 1)
        except PermissionError:
            pass
