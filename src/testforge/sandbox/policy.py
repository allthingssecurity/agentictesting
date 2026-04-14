"""Sandbox policy configuration."""

from testforge.sandbox.protocol import FilesystemPolicy, NetworkPolicy


def get_default_policy(filesystem_mode: str = "readwrite") -> tuple[FilesystemPolicy, NetworkPolicy]:
    """Return default sandbox policies."""
    return (
        FilesystemPolicy(mode=filesystem_mode),
        NetworkPolicy(allowed_urls=["http://localhost:*"], block_all=False),
    )


def get_strict_policy() -> tuple[FilesystemPolicy, NetworkPolicy]:
    """Strict policy: readonly filesystem, no network."""
    return (
        FilesystemPolicy(mode="readonly"),
        NetworkPolicy(block_all=True),
    )
