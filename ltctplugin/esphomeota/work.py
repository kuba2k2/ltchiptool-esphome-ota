#  Copyright (c) Kuba Szczodrzyński 2023-8-31.

from typing import IO

from ltchiptool.gui.work.base import BaseThread
from ltchiptool.util.streams import ClickProgressCallback

from ltctplugin.esphomeota.esphome import ESPHomeUploader


class UploaderThread(BaseThread):
    callback: ClickProgressCallback
    io: IO[bytes] | None = None
    esphome: ESPHomeUploader = None

    def __init__(
        self,
        address: str,
        port: int,
        password: str | None,
        file: str,
    ):
        super().__init__()
        self.address = address
        self.port = port
        self.password = password
        self.file = file

    def run_impl(self):
        self.callback = ClickProgressCallback()
        with self.callback:
            self.callback.on_message("Reading firmware file...")

            self.io = open(self.file, "rb")
            self.esphome = ESPHomeUploader(
                file=self.io,
                host=self.address,
                port=self.port,
                password=self.password or None,
                callback=self.callback,
            )
            self.esphome.upload()
            self.io.close()
            self.io = None

    def stop(self):
        super().stop()
        if self.io:
            self.io.close()
        if self.esphome:
            self.esphome.close()
