from PySide6.QtCore import QRectF

from ui.background import cover_rect, load_pixmap


def test_cover_rect_wide_target_crops_portrait_sides():
    # 竖图 100x200 铺宽窗口 400x100：scale=max(4,0.5)=4，高溢出上下居中裁剪
    r = cover_rect(100, 200, 400, 100)
    assert r == QRectF(0.0, -350.0, 400.0, 800.0)


def test_cover_rect_tall_target_crops_top_bottom():
    # 横图 200x100 铺竖窗口 100x400：scale=max(0.5,4)=4，宽溢出左右居中裁剪
    r = cover_rect(200, 100, 100, 400)
    assert r == QRectF(-350.0, 0.0, 800.0, 400.0)


def test_cover_rect_exact_fit():
    r = cover_rect(320, 240, 320, 240)
    assert r == QRectF(0.0, 0.0, 320.0, 240.0)


def test_cover_rect_invalid_zero():
    assert cover_rect(0, 100, 50, 50) == QRectF(0, 0, 0, 0)
    assert cover_rect(100, 100, 0, 50) == QRectF(0, 0, 0, 0)


def test_cover_rect_align_top_right():
    # 横图 200x100 铺竖窗口 100x400：scale=4 → 800x400，右对齐/顶对齐
    r = cover_rect(200, 100, 100, 400, h_align="right", v_align="top")
    assert r == QRectF(-700.0, 0.0, 800.0, 400.0)


def test_cover_rect_align_left_bottom():
    # 竖图 100x200 铺宽窗口 400x100：scale=4 → 400x800，左对齐/底对齐
    r = cover_rect(100, 200, 400, 100, h_align="left", v_align="bottom")
    assert r == QRectF(0.0, -700.0, 400.0, 800.0)


def test_load_pixmap_missing_file_returns_none(tmp_path):
    assert load_pixmap(tmp_path / "nope.png") is None
