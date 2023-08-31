#  Copyright (c) Kuba Szczodrzyński 2023-8-31.

import os
from os.path import dirname, isfile

import wx.adv
import wx.xrc
from ltchiptool.gui.panels.base import BasePanel
from ltchiptool.gui.utils import on_event, with_target
from ltchiptool.util.logging import verbose

from ltctplugin.esphomeota.work import UploaderThread


# noinspection PyPep8Naming
class UploaderPanel(BasePanel):
    def __init__(self, parent: wx.Window, frame):
        super().__init__(parent, frame)
        self.LoadXRCFile("uploader.xrc")
        self.LoadXRC("UploaderPanel")
        self.AddToNotebook("ESPHome OTA")

        self.Address = self.BindTextCtrl("input_address")
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

    def OnUpdate(self, target: wx.Window = None):
        verbose(f"OnUpdate({self.file})")
        errors = []

        if not self.file:
            errors.append("Choose an input file")
        elif not isfile(self.file):
            errors.append("File does not exist")

        if not self.address:
            errors.append("Enter device IP address or hostname")
        if not self.port:
            errors.append("Enter device OTA port number")

        if errors:
            self.Start.SetNote(errors[0])
            self.Start.Disable()
        else:
            self.Start.SetNote("")
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
    def OnBrowseClick(self) -> None:
        pass

    @property
    def address(self) -> str:
        return self.Address.GetValue().strip() or ""

    @address.setter
    def address(self, value: str) -> None:
        self.Address.ChangeValue(value or "")

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
            address=self.address,
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
