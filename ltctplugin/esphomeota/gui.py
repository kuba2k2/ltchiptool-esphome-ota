#  Copyright (c) Kuba Szczodrzyński 2023-8-31.

import os
from logging import debug, warning
from os.path import dirname, isfile

import wx.adv
import wx.xrc
from ltchiptool.gui.panels.base import BasePanel
from ltchiptool.gui.utils import on_event, with_target
from zeroconf import IPVersion, ServiceBrowser, ServiceInfo, ServiceListener, Zeroconf

from ltctplugin.esphomeota.work import UploaderThread

ZEROCONF_SERVICE = "_esphomelib._tcp.local."
PLATFORM_PORT = {
    "ESP8266": 8266,
    "ESP32": 3232,
    "RP2040": 2040,
    "LibreTuya": 8892,
    "LibreTiny": 8892,
    "BK72": 8892,
    "RTL87": 8892,
}


# noinspection PyPep8Naming
class UploaderPanel(BasePanel, ServiceListener):
    zeroconf: Zeroconf | None = None
    zeroconf_sb: ServiceBrowser | None = None
    services: dict[str, ServiceInfo] = None
    address_by_label: dict[str, tuple[str, int | None]] = None

    def __init__(self, parent: wx.Window, frame):
        super().__init__(parent, frame)
        self.LoadXRCFile("uploader.xrc")
        self.LoadXRC("UploaderPanel")
        self.AddToNotebook("ESPHome OTA")

        self.Address = self.BindComboBox("combo_address")
        self.Devices = self.FindStaticText("text_devices")
        self.Port = self.BindComboBox("combo_port")
        self.Password = self.BindTextCtrl("input_password")
        self.File = self.BindTextCtrl("input_file")
        self.Ping = self.BindButton("button_ping", self.OnPingClick)
        self.Browse = self.BindButton("button_browse", self.OnBrowseClick)
        self.Start: wx.adv.CommandLinkButton = self.BindButton(
            "button_start", self.OnStartClick
        )
        self.Cancel: wx.adv.CommandLinkButton = self.BindButton(
            "button_cancel", self.OnCancelClick
        )

        self.zeroconf = Zeroconf()
        self.services = {}
        self.address_by_label = {}
        self.OnServicesUpdate()

        self.File.Bind(wx.EVT_KILL_FOCUS, self.OnBlur)
        self.Cancel.SetNote("")

        self.EnableFileDrop()

    def GetSettings(self) -> dict:
        return dict(
            address=self.address,
            port=self.port,
            password=self.password,
            file=self.file,
        )

    def SetSettings(
        self,
        address: str = None,
        port: int = None,
        password: str = None,
        file: str = None,
        **_,
    ) -> None:
        if address:
            self.address = address
        if port:
            self.port = port
        if password:
            self.password = password
        if file:
            self.file = file

    def OnActivate(self):
        if self.zeroconf_sb:
            return
        self.zeroconf_sb = ServiceBrowser(self.zeroconf, ZEROCONF_SERVICE, self)

    def OnUpdate(self, target: wx.Window = None):
        address = self.address
        file = self.file
        print(f"OnUpdate(address={address}, file={file})")
        errors = []

        if target == self.Address and address in self.address_by_label:
            _, self.port = self.address_by_label[address]

        if not self.file:
            errors.append("Choose an input file")
        elif not isfile(self.file):
            errors.append("File does not exist")

        if not self.real_address:
            errors.append("Enter device IP address or hostname")
        if not self.port:
            errors.append("Enter device OTA port number")

        if errors:
            self.Start.SetNote(errors[0])
            self.Start.Disable()
        else:
            self.Start.SetNote(f"Upload to {self.real_address}:{self.port}")
            self.Start.Enable()

        self.Cancel.Disable()

    def OnFileDrop(self, *files):
        if not files:
            return
        self.file = files[0]

    @with_target
    def OnBlur(self, event: wx.FocusEvent, target: wx.Window):
        event.Skip()
        if target == self.File:
            self.file = self.file

    @on_event
    def OnPingClick(self) -> None:
        pass

    @on_event
    def OnBrowseClick(self):
        title = "Open file"
        flags = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        init_dir = dirname(self.file) if self.file else os.getcwd()
        with wx.FileDialog(self, title, init_dir, style=flags) as dialog:
            dialog: wx.FileDialog
            if dialog.ShowModal() == wx.ID_CANCEL:
                return
            self.file = dialog.GetPath()

    @on_event
    def OnStartClick(self):
        work = UploaderThread(
            address=self.real_address,
            port=self.port,
            password=self.password,
            file=self.file,
        )
        self.StartWork(work)
        self.Start.SetNote("")
        self.Cancel.Enable()

    @on_event
    def OnCancelClick(self):
        self.StopWork(UploaderThread)

    def OnServicesUpdate(self):
        text = self.Address.GetValue()
        items = []
        self.address_by_label = {}
        for info in self.services.values():
            address = info.parsed_scoped_addresses(version=IPVersion.V4Only)[0]
            port = None

            label = f"{address} - {info.server}"
            if info.properties:
                debug(f"Device @ {address}: {info.properties}")
                version = info.properties.get(b"version", b"").decode()
                platform = info.properties.get(b"platform", b"").decode()
                board = info.properties.get(b"board", b"").decode()
                label += f" (ESPHome {version} on {platform} / {board})"
                for key, value in PLATFORM_PORT.items():
                    if platform.startswith(key):
                        port = value

            self.address_by_label[label] = (address, port)
            items.append(label)
        self.Devices.SetLabel(f"{len(self.services)} device(s) found")
        self.Address.SetItems(items)
        self.Address.SetValue(text)

    @property
    def address(self) -> str:
        return self.Address.GetValue().strip() or ""

    @address.setter
    def address(self, value: str) -> None:
        self.Address.ChangeValue(value or "")

    @property
    def real_address(self) -> str:
        address = self.address
        if address in self.address_by_label:
            address, _ = self.address_by_label[address]
        return address

    @property
    def port(self) -> int | None:
        text = self.Port.GetValue() or ""
        text = text.strip().partition(" ")[0] or ""
        if text.isnumeric():
            return int(text)
        return None

    @port.setter
    def port(self, value: int) -> None:
        for i, text in enumerate(self.Port.GetStrings()):
            if text.startswith(str(value)):
                self.Port.ChangeValue(text)
                return
        self.Port.ChangeValue(str(value))

    @property
    def password(self) -> str:
        return self.Password.GetValue().strip() or ""

    @password.setter
    def password(self, value: str) -> None:
        self.Password.ChangeValue(value or "")

    @property
    def file(self):
        return self.File.GetValue().strip() or ""

    @file.setter
    def file(self, value: str | None):
        value = value or ""
        self.File.ChangeValue(value)
        self.DoUpdate(self.File)

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        debug(f"mDNS service added: {name}")
        info = zc.get_service_info(type_, name)
        if info:
            self.services[name] = info
        else:
            warning("Couldn't read service info")
        self.OnServicesUpdate()

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        debug(f"mDNS service updated: {name}")
        info = zc.get_service_info(type_, name)
        if info:
            self.services[name] = info
        else:
            warning("Couldn't read service info")
            self.services.pop(name, None)
        self.OnServicesUpdate()

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        debug(f"mDNS service removed: {name}")
        self.services.pop(name, None)
        self.OnServicesUpdate()
