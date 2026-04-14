import importlib
import inspect
import pkgutil
from pathlib import Path

from testforge.models.enums import Language, ToolCategory
from testforge.tools.adapters._base import BaseToolAdapter
from testforge.tools.protocol import ToolAdapter


class ToolRegistry:
    """Discovers and manages tool adapters from three sources:

    1. Built-in adapters in testforge.tools.adapters package
    2. Python entry_points (group='testforge.tools')
    3. Project-local tools/ directory
    """

    def __init__(self):
        self._adapters: dict[str, ToolAdapter] = {}

    def register(self, adapter: ToolAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> ToolAdapter | None:
        return self._adapters.get(name)

    def list_all(self) -> list[ToolAdapter]:
        return list(self._adapters.values())

    def auto_discover(self) -> None:
        """Discover adapters from all three sources."""
        self._discover_builtins()
        self._discover_entry_points()

    def discover_project_tools(self, project_root: Path) -> None:
        """Discover adapters from a project's tools/ directory."""
        tools_dir = project_root / "tools"
        if not tools_dir.is_dir():
            return
        for py_file in tools_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    f"project_tools.{py_file.stem}", py_file,
                )
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    self._collect_from_module(mod)
            except Exception:
                pass

    def detect_applicable(
        self, project_root: Path, languages: set[Language] | None = None,
    ) -> list[ToolAdapter]:
        """Return adapters that are available and applicable to this project."""
        applicable = []
        for adapter in self._adapters.values():
            if languages and adapter.languages:
                if not set(adapter.languages) & languages:
                    continue
            try:
                if adapter.detect(project_root):
                    applicable.append(adapter)
            except Exception:
                pass
        return applicable

    def filter_by_category(self, category: ToolCategory) -> list[ToolAdapter]:
        return [a for a in self._adapters.values() if a.category == category]

    def filter_by_language(self, language: Language) -> list[ToolAdapter]:
        return [a for a in self._adapters.values() if language in a.languages or not a.languages]

    def snapshot(self) -> dict:
        """Serialize registry state for inclusion in graph state."""
        return {
            "adapters": [
                {
                    "name": a.name,
                    "category": a.category.value,
                    "languages": [l.value for l in a.languages],
                    "binary": a.binary,
                    "filesystem_mode": a.filesystem_mode,
                    "timeout": a.default_timeout,
                }
                for a in self._adapters.values()
            ]
        }

    def _discover_builtins(self) -> None:
        import testforge.tools.adapters as adapters_pkg
        for _, modname, _ in pkgutil.iter_modules(adapters_pkg.__path__):
            if modname.startswith("_"):
                continue
            try:
                mod = importlib.import_module(f"testforge.tools.adapters.{modname}")
                self._collect_from_module(mod)
            except Exception:
                pass

    def _discover_entry_points(self) -> None:
        try:
            from importlib.metadata import entry_points
            eps = entry_points(group="testforge.tools")
            for ep in eps:
                try:
                    cls = ep.load()
                    if isinstance(cls, type) and issubclass(cls, BaseToolAdapter):
                        self.register(cls())
                except Exception:
                    pass
        except Exception:
            pass

    def _collect_from_module(self, mod) -> None:
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if (
                issubclass(obj, BaseToolAdapter)
                and obj is not BaseToolAdapter
                and hasattr(obj, "name")
                and obj.name
            ):
                self.register(obj())
