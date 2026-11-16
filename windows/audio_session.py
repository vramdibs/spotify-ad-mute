"""Mute only Spotify.exe audio sessions. COM is touched when a call runs."""

import ctypes
from ctypes import (
    POINTER,
    WINFUNCTYPE,
    byref,
    c_int,
    c_long,
    c_ubyte,
    c_ulong,
    c_ushort,
    c_void_p,
    cast,
)
import uuid

from policy import is_spotify_image

HRESULT = c_long
DWORD = c_ulong
BOOL = c_int
CLSCTX_ALL = 23
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", c_ulong),
        ("Data2", c_ushort),
        ("Data3", c_ushort),
        ("Data4", c_ubyte * 8),
    ]


def make_guid(text):
    parsed = uuid.UUID(text)
    data4 = (c_ubyte * 8).from_buffer_copy(parsed.bytes[8:])
    return GUID(parsed.time_low, parsed.time_mid, parsed.time_hi_version, data4)


CLSID_MMDEVICE = make_guid("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
IID_ENUMERATOR = make_guid("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
IID_SESSION_MANAGER2 = make_guid("{77AA99A0-1BD6-484F-8BC7-2C654C9A9B6F}")
IID_SIMPLE_VOLUME = make_guid("{87CE5498-68D6-44E5-9215-6DA47EF883D8}")
IID_SESSION_CONTROL2 = make_guid("{BFB7FF88-7239-4FC9-8FA2-07C950BE9C6D}")

_COM_READY = False


def _vtable(ptr):
    return cast(ptr, POINTER(POINTER(c_void_p)))[0]


def _method(ptr, index, restype, *argtypes):
    prototype = WINFUNCTYPE(restype, c_void_p, *argtypes)
    return prototype(_vtable(ptr)[index])


def _check(hr):
    if hr < 0:
        raise OSError("com 0x%08X" % (hr & 0xFFFFFFFF))


def _release(ptr):
    if ptr:
        _method(ptr, 2, c_ulong)(ptr)


def _query(ptr, iid):
    out = c_void_p()
    _check(_method(ptr, 0, HRESULT, POINTER(GUID), POINTER(c_void_p))(ptr, byref(iid), byref(out)))
    return out


def _ensure_com():
    global _COM_READY
    if _COM_READY:
        return
    ole32 = ctypes.windll.ole32
    ole32.CoInitializeEx.argtypes = [c_void_p, DWORD]
    ole32.CoInitializeEx.restype = HRESULT
    hr = ole32.CoInitializeEx(None, 0)
    if hr < 0 and (hr & 0xFFFFFFFF) != 0x80010106:
        _check(hr)
    _COM_READY = True


def _image_name(pid):
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.argtypes = [DWORD, BOOL, DWORD]
    kernel32.OpenProcess.restype = c_void_p
    kernel32.CloseHandle.argtypes = [c_void_p]
    kernel32.CloseHandle.restype = BOOL
    kernel32.QueryFullProcessImageNameW.argtypes = [c_void_p, DWORD, ctypes.c_wchar_p, POINTER(DWORD)]
    kernel32.QueryFullProcessImageNameW.restype = BOOL
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = DWORD(1024)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buf, byref(size)):
            return ""
        return buf.value
    finally:
        kernel32.CloseHandle(handle)


def _create_enumerator():
    ole32 = ctypes.windll.ole32
    ole32.CoCreateInstance.argtypes = [POINTER(GUID), c_void_p, DWORD, POINTER(GUID), POINTER(c_void_p)]
    ole32.CoCreateInstance.restype = HRESULT
    out = c_void_p()
    _check(ole32.CoCreateInstance(byref(CLSID_MMDEVICE), None, 1, byref(IID_ENUMERATOR), byref(out)))
    return out


def _default_endpoint(enumerator):
    out = c_void_p()
    _check(_method(enumerator, 4, HRESULT, c_int, c_int, POINTER(c_void_p))(enumerator, 0, 0, byref(out)))
    return out


def _session_manager(endpoint):
    out = c_void_p()
    _check(
        _method(endpoint, 3, HRESULT, POINTER(GUID), DWORD, c_void_p, POINTER(c_void_p))(
            endpoint, byref(IID_SESSION_MANAGER2), CLSCTX_ALL, None, byref(out)
        )
    )
    return out


def _sessions(manager):
    out = c_void_p()
    _check(_method(manager, 5, HRESULT, POINTER(c_void_p))(manager, byref(out)))
    return out


def spotify_pids():
    _ensure_com()
    enumerator = endpoint = manager = sessions = None
    found = []
    try:
        enumerator = _create_enumerator()
        endpoint = _default_endpoint(enumerator)
        manager = _session_manager(endpoint)
        sessions = _sessions(manager)
        count = c_int()
        _check(_method(sessions, 3, HRESULT, POINTER(c_int))(sessions, byref(count)))
        for index in range(count.value):
            control = control2 = None
            try:
                control = c_void_p()
                _check(_method(sessions, 4, HRESULT, c_int, POINTER(c_void_p))(sessions, index, byref(control)))
                control2 = _query(control, IID_SESSION_CONTROL2)
                pid = DWORD()
                hr = _method(control2, 14, HRESULT, POINTER(DWORD))(control2, byref(pid))
                if hr < 0:
                    continue
                if is_spotify_image(_image_name(pid.value)):
                    found.append(int(pid.value))
            finally:
                _release(control2)
                _release(control)
    finally:
        _release(sessions)
        _release(manager)
        _release(endpoint)
        _release(enumerator)
    return found


def set_pid_muted(pid, muted):
    _ensure_com()
    enumerator = endpoint = manager = sessions = None
    try:
        enumerator = _create_enumerator()
        endpoint = _default_endpoint(enumerator)
        manager = _session_manager(endpoint)
        sessions = _sessions(manager)
        count = c_int()
        _check(_method(sessions, 3, HRESULT, POINTER(c_int))(sessions, byref(count)))
        for index in range(count.value):
            control = control2 = volume = None
            try:
                control = c_void_p()
                _check(_method(sessions, 4, HRESULT, c_int, POINTER(c_void_p))(sessions, index, byref(control)))
                control2 = _query(control, IID_SESSION_CONTROL2)
                found = DWORD()
                if _method(control2, 14, HRESULT, POINTER(DWORD))(control2, byref(found)) < 0:
                    continue
                if int(found.value) != int(pid):
                    continue
                volume = _query(control, IID_SIMPLE_VOLUME)
                _check(_method(volume, 5, HRESULT, BOOL, c_void_p)(volume, 1 if muted else 0, None))
            finally:
                _release(volume)
                _release(control2)
                _release(control)
    finally:
        _release(sessions)
        _release(manager)
        _release(endpoint)
        _release(enumerator)
