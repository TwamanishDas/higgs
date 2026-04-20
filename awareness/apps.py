import winreg
import os


_REGISTRY_PATHS = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
]

_cached_apps: list[str] = []


def get_installed_apps(force_refresh: bool = False) -> list[str]:
    global _cached_apps
    if _cached_apps and not force_refresh:
        return _cached_apps

    apps = set()
    for hive, path in _REGISTRY_PATHS:
        try:
            key = winreg.OpenKey(hive, path)
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    sub_key_name = winreg.EnumKey(key, i)
                    sub_key = winreg.OpenKey(key, sub_key_name)
                    try:
                        name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
                        if name and isinstance(name, str):
                            apps.add(name.strip())
                    except FileNotFoundError:
                        pass
                    winreg.CloseKey(sub_key)
                except Exception:
                    pass
            winreg.CloseKey(key)
        except Exception:
            pass

    _cached_apps = sorted(apps)
    return _cached_apps
