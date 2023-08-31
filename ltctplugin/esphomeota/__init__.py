#  Copyright (c) Kuba Szczodrzyński 2023-8-31.

from typing import Any, Dict

from ltctplugin.base import PluginBase
from semantic_version.base import BaseSpec, SimpleSpec


class Plugin(PluginBase):
    @property
    def title(self) -> str:
        return "ESPHome OTA Uploader"

    @property
    def ltchiptool_version(self) -> BaseSpec | None:
        return SimpleSpec(">=4.4.0")

    @property
    def has_cli(self) -> bool:
        return False

    @property
    def has_gui(self) -> bool:
        return True

    def build_cli(self, *args, **kwargs) -> Dict[str, Any]:
        return dict()

    def build_gui(self, *args, **kwargs) -> Dict[str, Any]:
        from .gui import UploaderPanel

        return dict(
            uploader=UploaderPanel,
        )


entrypoint = Plugin

__all__ = [
    "entrypoint",
]
