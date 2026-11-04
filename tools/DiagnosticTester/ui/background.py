"""主窗口背景图与窗口图标：cover 缩放绘制（保持比例、可对齐边角裁剪）。

图片路径 <base>/image/<BACKGROUND_FILE>，缺失或损坏时静默降级（无背景/默认图标）。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

BACKGROUND_FILE = "mikasa.jpg"


def background_path(base_dir: Path) -> Path:
    return Path(base_dir) / "image" / BACKGROUND_FILE


def load_pixmap(path: Path) -> QPixmap | None:
    p = Path(path)
    if not p.is_file():
        return None
    pix = QPixmap(str(p))
    return pix if not pix.isNull() else None


def load_icon(path: Path) -> QIcon | None:
    pix = load_pixmap(path)
    return QIcon(pix) if pix is not None else None


# 半透明面板（约 78% 不透明白）：背景图透出、文字仍可读
TRANSLUCENT_BG = "rgba(255, 255, 255, 200)"
# QTabWidget 面板透明化：页面区透出背景，仅保留淡边框
TAB_PANE_STYLE = ("QTabWidget::pane { background: transparent;"
                  " border: 1px solid rgba(120, 120, 120, 150); }")


def make_translucent(widget) -> None:
    """给内容视图（列表/表格/文本）套半透明背景样式。"""
    cls = widget.metaObject().className()
    widget.setStyleSheet(f"{cls} {{ background-color: {TRANSLUCENT_BG}; }}")


def cover_rect(pix_w: int, pix_h: int, w: int, h: int,
               h_align: str = "center", v_align: str = "center") -> QRectF:
    """等比缩放至完全覆盖 (w, h)，按 h_align/v_align 对齐裁剪；非法尺寸返回零矩形。"""
    if pix_w <= 0 or pix_h <= 0 or w <= 0 or h <= 0:
        return QRectF(0, 0, 0, 0)
    scale = max(w / pix_w, h / pix_h)
    dw, dh = pix_w * scale, pix_h * scale
    x = {"left": 0.0, "center": (w - dw) / 2, "right": w - dw}[h_align]
    y = {"top": 0.0, "center": (h - dh) / 2, "bottom": h - dh}[v_align]
    return QRectF(x, y, dw, dh)


class BackgroundWidget(QWidget):
    """中央容器：背景图 cover 填满；子控件各自不透明，背景显示在控件间隙与留白区。"""

    def __init__(self, pixmap: QPixmap | None,
                 h_align: str = "center", v_align: str = "center", parent=None):
        super().__init__(parent)
        self._pixmap = pixmap
        self._h_align = h_align
        self._v_align = v_align

    def paintEvent(self, event):
        if (self._pixmap is not None and not self._pixmap.isNull()
                and self.width() > 0 and self.height() > 0):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            rect = cover_rect(self._pixmap.width(), self._pixmap.height(),
                              self.width(), self.height(),
                              self._h_align, self._v_align)
            src = QRectF(0.0, 0.0, float(self._pixmap.width()),
                         float(self._pixmap.height()))
            painter.drawPixmap(rect, self._pixmap, src)
        super().paintEvent(event)
