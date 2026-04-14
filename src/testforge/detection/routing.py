from testforge.models.enums import Language, ToolCategory
from testforge.tools.registry import ToolRegistry


class LanguageRouter:
    """Maps detected languages to tool adapters and agent configurations."""

    def __init__(self, registry: ToolRegistry):
        self.registry = registry

    def route(self, languages: set[Language]) -> list[dict]:
        """For each language, return the set of applicable tools and config.

        Returns a list of dicts, each with:
            language: Language
            tools: list of adapter snapshots
            test_categories: list of ToolCategory values that apply
        """
        routes = []
        for lang in sorted(languages, key=lambda l: l.value):
            lang_tools = self.registry.filter_by_language(lang)
            if not lang_tools:
                continue

            categories = set()
            tool_snapshots = []
            for adapter in lang_tools:
                categories.add(adapter.category)
                tool_snapshots.append({
                    "name": adapter.name,
                    "category": adapter.category.value,
                    "binary": adapter.binary,
                    "filesystem_mode": adapter.filesystem_mode,
                    "timeout": adapter.default_timeout,
                })

            routes.append({
                "language": lang.value,
                "tools": tool_snapshots,
                "test_categories": [c.value for c in categories],
            })

        return routes
