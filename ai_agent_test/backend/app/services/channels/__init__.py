"""Channel adapter registry."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.channels.base import ChannelAdapter

_adapters: dict[str, "ChannelAdapter"] = {}


def register_adapter(adapter: "ChannelAdapter") -> None:
    """Register a channel adapter by its platform name."""
    _adapters[adapter.platform] = adapter


def get_adapter(platform: str) -> "ChannelAdapter":
    """Retrieve a registered adapter by platform name.

    Raises:
        KeyError: If no adapter is registered for the given platform.
    """
    if platform not in _adapters:
        raise KeyError(f"No channel adapter registered for platform '{platform}'")
    return _adapters[platform]


def list_platforms() -> list[str]:
    """Return a list of all registered platform names."""
    return list(_adapters.keys())
