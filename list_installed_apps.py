
# -*- coding: utf-8 -*-
"""
List Installed Apps - Windows
- Liệt kê ứng dụng bên thứ ba đã cài đặt.
- Bỏ qua phần lớn thành phần Windows và hệ thống.
- Đọc Registry 32-bit / 64-bit, HKLM / HKCU.
- In Name, Version, Publisher, InstallLocation, DisplayIcon.
- Không cần cài thêm thư viện.
"""

import os
import re
import winreg
from pathlib import Path

OUTPUT_FILE = Path.home() / "Desktop" / "installed_apps.txt"

UNINSTALL_KEY = (
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
)

REGISTRY_ROOTS = [
    winreg.HKEY_LOCAL_MACHINE,
    winreg.HKEY_CURRENT_USER,
]

# Các tên thường gặp của thành phần hệ thống cần bỏ qua.
SYSTEM_NAME_PATTERNS = [
    r"^security update\b",
    r"^update for windows\b",
    r"^update for microsoft windows\b",
    r"^hotfix\b",
    r"^kb\d{6,}\b",
    r"^windows (10|11|server)\s+update\b",
    r"^microsoft windows operating system\b",
    r"^windows software development kit\b",
    r"^windows driver package\b",
    r"^driver package\b",
]

# Các mục hệ thống thường được đăng ký dưới dạng ứng dụng.
SYSTEM_PUBLISHER_PATTERNS = [
    r"^microsoft windows$",
    r"^microsoft corporation$",
]

COMPILED_NAME_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in SYSTEM_NAME_PATTERNS
]

COMPILED_PUBLISHER_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in SYSTEM_PUBLISHER_PATTERNS
]


def read_value(key, value_name, default=""):
    """Đọc một giá trị Registry an toàn."""
    try:
        value, _ = winreg.QueryValueEx(key, value_name)
        if value is None:
            return default
        return str(value).strip()
    except (OSError, ValueError):
        return default


def read_dword(key, value_name, default=0):
    """Đọc DWORD trong Registry."""
    try:
        value, _ = winreg.QueryValueEx(key, value_name)
        return int(value)
    except (OSError, ValueError, TypeError):
        return default


def should_skip(key, name, publisher):
    """Lọc thành phần Windows và các mục không phải ứng dụng độc lập."""

    # Các cờ đánh dấu thành phần hệ thống.
    if read_dword(key, "SystemComponent", 0) == 1:
        return True

    # Bản cập nhật hoặc thành phần phụ thuộc ứng dụng khác.
    if read_value(key, "ReleaseType"):
        return True

    if read_value(key, "ParentKeyName"):
        return True

    # Các bản vá Windows thường có tên KBxxxxxxx.
    for pattern in COMPILED_NAME_PATTERNS:
        if pattern.search(name):
            return True

    # Chỉ loại publisher Microsoft Windows cụ thể,
    # không loại toàn bộ ứng dụng của Microsoft.
    for pattern in COMPILED_PUBLISHER_PATTERNS:
        if pattern.fullmatch(publisher.strip()):
            return True

    return False


def get_installed_apps():
    """Thu thập ứng dụng từ các Registry view."""
    apps = {}
    registry_views = [
        ("64-bit", getattr(winreg, "KEY_WOW64_64KEY", 0)),
        ("32-bit", getattr(winreg, "KEY_WOW64_32KEY", 0)),
    ]

    for root in REGISTRY_ROOTS:
        root_name = (
            "HKLM" if root == winreg.HKEY_LOCAL_MACHINE else "HKCU"
        )

        for view_name, view_flag in registry_views:
            try:
                base = winreg.OpenKey(
                    root,
                    UNINSTALL_KEY,
                    0,
                    winreg.KEY_READ | view_flag,
                )
            except OSError:
                continue

            with base:
                try:
                    subkey_count = winreg.QueryInfoKey(base)[0]
                except OSError:
                    continue

                for index in range(subkey_count):
                    try:
                        subkey_name = winreg.EnumKey(base, index)
                        with winreg.OpenKey(
                            base,
                            subkey_name,
                            0,
                            winreg.KEY_READ | view_flag,
                        ) as key:
                            name = read_value(key, "DisplayName")
                            if not name:
                                continue

                            version = read_value(
                                key, "DisplayVersion"
                            )
                            publisher = read_value(key, "Publisher")
                            install_location = read_value(
                                key, "InstallLocation"
                            )
                            display_icon = read_value(
                                key, "DisplayIcon"
                            )

                            if should_skip(key, name, publisher):
                                continue

                            # Loại một số mục chỉ là thành phần hệ thống
                            # theo tên, nhưng vẫn giữ ứng dụng Microsoft
                            # như Office, Edge, PowerToys...
                            identity = (
                                name.casefold(),
                                version.casefold(),
                                publisher.casefold(),
                                display_icon.casefold(),
                            )

                            app = {
                                "Name": name,
                                "Version": version,
                                "Publisher": publisher,
                                "InstallLocation": install_location,
                                "DisplayIcon": display_icon,
                            }

                            # Ưu tiên bản ghi có nhiều thông tin hơn.
                            score = sum(bool(v) for v in app.values())
                            previous = apps.get(identity)

                            if (
                                previous is None
                                or score > previous["_score"]
                            ):
                                app["_score"] = score
                                app["_source"] = (
                                    root_name + " / " + view_name
                                )
                                apps[identity] = app

                    except OSError:
                        continue

    result = list(apps.values())
    result.sort(key=lambda app: app["Name"].casefold())
    return result


def format_app(app):
    """Định dạng giống mẫu yêu cầu."""
    fields = [
        ("Name", "Name"),
        ("Version", "Version"),
        ("Publisher", "Publisher"),
        ("InstallLocation", "InstallLocation"),
        ("DisplayIcon", "DisplayIcon"),
    ]

    return "\n".join(
        f"{label:<16}: {app[key]}"
        for label, key in fields
    )


def main():
    apps = get_installed_apps()

    lines = [
        "DANH SACH UNG DUNG DA CAI DAT",
        f"Tong so: {len(apps)}",
        "=" * 75,
        "",
    ]

    for app in apps:
        lines.append(format_app(app))
        lines.append("-" * 75)

    output = "\n".join(lines)

    print(output)

    # Lưu file UTF-8 trên Desktop.
    try:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(output, encoding="utf-8")
        print(f"\nDa luu danh sach: {OUTPUT_FILE}")
    except OSError as exc:
        print(f"\nKhong the luu file: {exc}")


if __name__ == "__main__":
    main()
