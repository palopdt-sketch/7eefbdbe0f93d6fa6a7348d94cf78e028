#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Thông báo toàn màn hình kiểu "EMERGENCY ALERT" (PySide6).

Cài đặt:   pip install PySide6
Ví dụ:
    python canh_bao.py --noidung "UTF-8 Đã Được cài đặt, vui lòng kiểm tra và khởi động lại chương trình uniweb" --img "https://example.com/a.png"

Tham số:
    --noidung  (BẮT BUỘC) Nội dung thông báo. Không có nội dung -> chương trình thoát.
    --img      (tuỳ chọn) URL hoặc đường dẫn file ảnh.
    --tieude   (tuỳ chọn) Tiêu đề lớn, mặc định "[EMERGENCY ALERT]".
    --capdo    (tuỳ chọn) Chữ trong dải vàng, mặc định "SEVERE".
    --icon     (tuỳ chọn) File icon ứng dụng (mặc định dùng app.ico / app.png cạnh script).
    --timeout  (tuỳ chọn) Tự đóng sau N giây (mặc định: không tự đóng).

Đóng thông báo: phím ESC / Enter hoặc bấm nút "XÁC NHẬN".
"""
import argparse
import os
import random
import sys

from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, QUrl
from PySide6.QtGui import (QBrush, QColor, QFont, QIcon, QPainter, QPen, QPixmap,
                           QPolygonF, QPainterPath)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel,
                               QPushButton, QSizePolicy, QVBoxLayout, QWidget)

# ---------------------------------------------------------------- màu sắc
C_BG = "#0a0b10"
C_PANEL = "#1c1f2b"
C_LINE = "#d9d9d9"
C_TEXT = "#e6e6e6"
C_YELLOW = "#ffd620"
C_YELLOW_2 = "#fff08a"
C_DARK = "#1c1f2b"
C_ORANGE = "#f5a623"
C_RED = "#e8101e"

FONTS = ["Futura", "Century Gothic", "Josefin Sans", "Segoe UI", "Arial"]


def make_font(px: int, bold=True, spacing=0.0) -> QFont:
    f = QFont()
    f.setFamilies(FONTS)
    f.setPixelSize(max(8, int(px)))
    f.setBold(bold)
    if spacing:
        f.setLetterSpacing(QFont.PercentageSpacing, 100 + spacing)
    return f


# ---------------------------------------------------------------- icon ứng dụng
def resource_path(name: str) -> str:
    """Tìm file cạnh script (hoặc trong gói PyInstaller)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def load_app_icon(custom: str = "") -> QIcon:
    """Ưu tiên --icon, sau đó app.ico, app.png cạnh script."""
    for cand in ([custom] if custom else []) + [resource_path("app.ico"), resource_path("app.png")]:
        if cand and os.path.isfile(cand):
            src = QPixmap(cand)
            if src.isNull():
                continue
            icon = QIcon()
            for sz in (16, 24, 32, 48, 64, 128, 256, 512):
                icon.addPixmap(src.scaled(sz, sz, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            return icon
    return QIcon()


# ---------------------------------------------------------------- widget vẽ tay
class HazardBar(QWidget):
    """Thanh sọc vàng-đen chéo."""

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        p.setPen(QPen(QColor(C_DARK), 4))
        p.setBrush(QColor(C_YELLOW))
        p.drawRoundedRect(r, 3, 3)

        inner = r.adjusted(6, 6, -6, -6)
        clip = QPainterPath()
        clip.addRect(inner)
        p.setClipPath(clip)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C_DARK))
        step = inner.height() * 0.9
        w = step * 0.5
        x = inner.left() - inner.height()
        while x < inner.right():
            poly = QPolygonF([
                QPointF(x, inner.bottom()),
                QPointF(x + w, inner.bottom()),
                QPointF(x + w + inner.height(), inner.top()),
                QPointF(x + inner.height(), inner.top()),
            ])
            p.drawPolygon(poly)
            x += step
        p.end()


class WarningIcon(QWidget):
    """Tam giác cảnh báo."""

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        tri = QPolygonF([QPointF(w / 2, 2), QPointF(w - 2, h - 2), QPointF(2, h - 2)])
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C_DARK))
        p.drawPolygon(tri)

        p.setPen(QPen(QColor(C_YELLOW), max(2, w // 18), Qt.SolidLine, Qt.RoundCap))
        # dấu "!"
        p.drawLine(QPointF(w / 2, h * 0.28), QPointF(w / 2, h * 0.46))
        p.drawPoint(QPointF(w / 2, h * 0.53))
        # biểu tượng nơ nhỏ phía dưới
        cx, cy, a, b = w / 2, h * 0.76, w * 0.17, h * 0.1
        p.setBrush(Qt.NoBrush)
        p.drawPolyline(QPolygonF([QPointF(cx - a, cy - b), QPointF(cx + a, cy + b),
                                  QPointF(cx + a, cy - b), QPointF(cx - a, cy + b),
                                  QPointF(cx - a, cy - b)]))
        p.end()


class Backdrop(QWidget):
    """Nền tối với dòng mã nhị phân mờ ở phía dưới."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        rnd = random.Random(7)
        self.rows = [" ".join("".join(rnd.choice("01") for _ in range(8))
                              for _ in range(26)) for _ in range(40)]

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(C_BG))
        p.setPen(QColor(255, 255, 255, 22))
        f = QFont("Consolas")
        f.setStyleHint(QFont.Monospace)
        f.setPixelSize(max(12, self.height() // 38))
        p.setFont(f)
        lh = int(self.height() / 30)
        for i in range(5):
            p.drawText(20, self.height() - lh * (i + 1) + lh // 2, self.rows[i])
        p.end()


# ---------------------------------------------------------------- panel chính
class AlertPanel(QFrame):
    def __init__(self, args, width_px, height_px, on_close):
        super().__init__()
        s = width_px / 1400.0  # hệ số co giãn
        self.s = s
        self.setFixedWidth(width_px)
        self.setMaximumHeight(height_px)
        self.setStyleSheet(f"AlertPanel {{ background:{C_PANEL}; border:2px solid {C_LINE}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- thanh trạng thái
        top = QFrame()
        top.setStyleSheet(f"border-bottom:2px solid {C_LINE};")
        th = QHBoxLayout(top)
        th.setContentsMargins(int(40 * s), int(8 * s), int(20 * s), int(8 * s))
        lb1 = QLabel("SYSTEM A.I - PHAN")
        lb1.setFont(make_font(26 * s, False, 4))
        lb1.setStyleSheet(f"color:{C_TEXT}; border:none;")
        sep = QFrame()
        sep.setFixedWidth(2)
        sep.setStyleSheet(f"background:{C_LINE}; border:none;")
        lb2 = QLabel("STATUS: " + args.capdo.upper())
        lb2.setFont(make_font(26 * s, False, 4))
        lb2.setStyleSheet(f"color:{C_ORANGE}; border:none;")
        th.addWidget(lb1)
        th.addWidget(sep)
        th.addSpacing(int(10 * s))
        th.addWidget(lb2)
        th.addStretch(1)
        root.addWidget(top)

        # --- tiêu đề lớn
        title = QLabel(args.tieude)
        title.setFont(make_font(100 * s, False, 2))
        title.setStyleSheet(f"color:{C_TEXT}; padding-left:{int(40*s)}px; "
                            f"padding-top:{int(6*s)}px; padding-bottom:{int(6*s)}px; border:none;")
        title.setWordWrap(True)
        root.addWidget(title)

        # --- dải vàng
        self.band = QFrame()
        self.band.setStyleSheet(f"background:{C_YELLOW}; border:none;")
        bh = QHBoxLayout(self.band)
        bh.setContentsMargins(int(40 * s), int(10 * s), int(40 * s), int(10 * s))
        bh.setSpacing(int(30 * s))
        lv = QLabel(args.capdo.upper())
        lv.setFont(make_font(100 * s, False))
        lv.setStyleSheet(f"color:{C_DARK}; border:none;")
        bar = HazardBar()
        bar.setFixedHeight(int(76 * s))
        bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        icon = WarningIcon()
        icon.setFixedSize(int(110 * s), int(100 * s))
        bh.addWidget(lv)
        bh.addWidget(bar, 1)
        bh.addWidget(icon)
        root.addWidget(self.band)

        # --- nội dung
        body = QFrame()
        body.setStyleSheet(f"border-top:2px solid {C_LINE};")
        self.body_l = QHBoxLayout(body)
        self.body_l.setContentsMargins(int(40 * s), int(24 * s), int(40 * s), int(24 * s))
        self.body_l.setSpacing(int(30 * s))

        n = len(args.noidung)
        px = 56 if n < 60 else 44 if n < 140 else 34 if n < 280 else 26
        self.msg = QLabel(args.noidung)
        self.msg.setFont(make_font(px * s, False))
        self.msg.setWordWrap(True)
        self.msg.setTextInteractionFlags(Qt.NoTextInteraction)
        self.msg.setStyleSheet(f"color:{C_TEXT}; border:none;")
        self.msg.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.body_l.addWidget(self.msg, 1)

        self.img_lbl = QLabel()
        self.img_lbl.setStyleSheet(f"border:2px solid {C_LINE};")
        self.img_lbl.setAlignment(Qt.AlignCenter)
        self.img_lbl.hide()
        self.body_l.addWidget(self.img_lbl, 0, Qt.AlignTop)
        root.addWidget(body, 1)

        # --- chân: nút đóng
        foot = QFrame()
        foot.setStyleSheet(f"border-top:2px solid {C_LINE};")
        fh = QHBoxLayout(foot)
        fh.setContentsMargins(int(40 * s), int(14 * s), int(40 * s), int(14 * s))
        hint = QLabel("NHẤN [ESC] HOẶC XÁC NHẬN ĐỂ ĐÓNG")
        hint.setFont(make_font(34 * s, True))
        hint.setStyleSheet(f"color:{C_RED}; border:none;")
        btn = QPushButton("XÁC NHẬN")
        btn.setFont(make_font(30 * s, True))
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton {{ background:{C_RED}; color:white; border:none; "
            f"padding:{int(10*s)}px {int(36*s)}px; }}"
            f"QPushButton:hover {{ background:#ff3a46; }}")
        btn.clicked.connect(on_close)
        fh.addWidget(hint)
        fh.addStretch(1)
        fh.addWidget(btn)
        root.addWidget(foot)

        # --- nhấp nháy dải vàng
        self._on = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._blink)
        self._timer.start(550)

    def _blink(self):
        self._on = not self._on
        c = C_YELLOW if self._on else C_YELLOW_2
        self.band.setStyleSheet(f"background:{c}; border:none;")

    def set_image(self, pix: QPixmap):
        if pix.isNull():
            return
        max_w, max_h = int(520 * self.s), int(380 * self.s)
        pix = pix.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.img_lbl.setPixmap(pix)
        self.img_lbl.show()


# ---------------------------------------------------------------- cửa sổ phủ màn hình
class Overlay(Backdrop):
    def __init__(self, screen, args, show_panel, icon=None):
        super().__init__()
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
        if not show_panel:
            flags |= Qt.Tool  # màn hình phụ: không hiện thêm icon taskbar
        self.setWindowFlags(flags)
        self.setWindowTitle("Emergency Alert")
        if icon is not None:
            self.setWindowIcon(icon)
        self.setScreen(screen)
        self.setGeometry(screen.geometry())
        self.setCursor(Qt.ArrowCursor)
        self.panel = None

        if show_panel:
            geo = screen.geometry()
            pw = min(int(geo.width() * 0.86), 1500)
            self.panel = AlertPanel(args, pw, int(geo.height() * 0.92), QApplication.quit)
            lay = QVBoxLayout(self)
            lay.addStretch(1)
            lay.addWidget(self.panel, 0, Qt.AlignHCenter)
            lay.addStretch(1)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Escape, Qt.Key_Return, Qt.Key_Enter):
            QApplication.quit()
        else:
            super().keyPressEvent(e)


def main():
    ap = argparse.ArgumentParser(description="Thông báo toàn màn hình (PySide6)")
    ap.add_argument("--noidung", default="", help="Nội dung thông báo (bắt buộc)")
    ap.add_argument("--img", default="", help="URL hoặc đường dẫn ảnh (tuỳ chọn)")
    ap.add_argument("--tieude", default="[EMERGENCY ALERT]", help="Tiêu đề lớn")
    ap.add_argument("--capdo", default="SEVERE", help="Chữ trong dải vàng")
    ap.add_argument("--icon", default="", help="File icon ứng dụng (mặc định: app.ico / app.png)")
    ap.add_argument("--timeout", type=int, default=0, help="Tự đóng sau N giây")
    args = ap.parse_args()

    args.noidung = (args.noidung or "").replace("\\n", "\n").strip()
    if not args.noidung:
        ap.print_usage(sys.stderr)
        print("Thiếu --noidung: không có nội dung nên chương trình không hiển thị.",
              file=sys.stderr)
        return 1

    # Windows: tách khỏi nhóm python.exe để taskbar hiện đúng icon
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("uniweb.emergency.alert")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("Emergency Alert")
    icon = load_app_icon(args.icon)
    if not icon.isNull():
        app.setWindowIcon(icon)
    screens = app.screens()
    primary = app.primaryScreen()

    windows = []
    main_win = None
    for sc in screens:
        is_primary = sc == primary
        w = Overlay(sc, args, show_panel=is_primary, icon=icon)
        windows.append(w)
        if is_primary:
            main_win = w
        w.showFullScreen()
    main_win.activateWindow()
    main_win.raise_()
    main_win.setFocus()

    # --- tải ảnh (tuỳ chọn)
    nam = None
    if args.img:
        src = args.img.strip()
        if src.lower().startswith(("http://", "https://")):
            nam = QNetworkAccessManager()
            nam.setRedirectPolicy(QNetworkRequest.NoLessSafeRedirectPolicy)
            req = QNetworkRequest(QUrl(src))
            req.setHeader(QNetworkRequest.UserAgentHeader, "Mozilla/5.0")
            reply = nam.get(req)

            def done():
                if reply.error() == reply.NetworkError.NoError:
                    pix = QPixmap()
                    pix.loadFromData(reply.readAll())
                    main_win.panel.set_image(pix)
                reply.deleteLater()

            reply.finished.connect(done)
        else:
            main_win.panel.set_image(QPixmap(src))

    if args.timeout > 0:
        QTimer.singleShot(args.timeout * 1000, app.quit)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
