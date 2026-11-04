from PySide6.QtWidgets import QApplication

from ui.fixed_routines_tab import FixedRoutinesTab, SESSIONS


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_sessions_offer_default_extended_programming():
    reqs = [req for _label, req in SESSIONS]
    assert reqs == ["1001", "1003", "1002"]


def test_tab_signals_and_busy():
    _app()
    tab = FixedRoutinesTab()
    tab.set_levels(["develop", "app"])
    assert tab._combo_level.count() == 2

    got = []
    tab.session_requested.connect(lambda v: got.append(v))
    tab._btn_session.click()
    assert got == ["1003"]  # 默认选中扩展会话

    unlocked = []
    tab.unlock_requested.connect(lambda v: unlocked.append(v))
    tab._btn_unlock.click()
    assert unlocked == ["app"]  # set_levels 已排序，develop 排后

    fired = []
    tab.dem_requested.connect(lambda: fired.append(True))
    tab._btn_dem.click()
    assert fired == [True]

    tab.set_busy(True)
    assert not tab._btn_session.isEnabled()
    assert not tab._btn_unlock.isEnabled()
    assert not tab._btn_dem.isEnabled()
    assert not tab._combo_session.isEnabled()
    tab.set_busy(False)
    assert tab._btn_dem.isEnabled()

    tab.set_status("done")
    assert tab._label.text() == "done"
