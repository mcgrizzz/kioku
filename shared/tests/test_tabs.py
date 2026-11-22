"""kioku.windows: tabs wider than the screen (Preferences) get a strip that
scrolls sideways in place of Qt's tab bar, and Qt's again once they fit."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QScrollArea,
    QScroller,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from kioku.windows import TAB_STRIP, TabStrip, _fit_tabs

app = QApplication.instance() or QApplication([])

NAMES = [
    "Appearance",
    "Review",
    "Editing",
    "Syncing",
    "Backups",
    "Third-Party Services",
    "Experiments",
    "Advanced",
]


def make() -> tuple[QDialog, QTabWidget]:
    dialog = QDialog()
    tabs = QTabWidget()
    for name in NAMES:
        tabs.addTab(QWidget(), name)
    QVBoxLayout(dialog).addWidget(tabs)
    dialog.resize(400, 800)
    dialog.show()
    app.processEvents()
    return dialog, tabs


def strip_of(dialog: QDialog) -> TabStrip | None:
    return dialog.findChild(TabStrip, TAB_STRIP)


def test_narrow_screen_shows_scrolling_strip() -> None:
    dialog, tabs = make()
    _fit_tabs(tabs, 400)
    app.processEvents()
    strip = strip_of(dialog)
    assert strip is not None and not strip.isHidden()
    assert tabs.tabBar().isHidden()
    bar = strip.widget()
    assert [bar.tabText(i) for i in range(bar.count())] == NAMES
    # all tabs at full width, wider than the strip: it scrolls
    assert bar.width() > strip.viewport().width()
    assert strip.horizontalScrollBar().maximum() > 0
    # above the pages
    layout = dialog.layout()
    assert layout.indexOf(strip) == layout.indexOf(tabs) - 1


def test_strip_and_tabs_follow_each_other() -> None:
    dialog, tabs = make()
    _fit_tabs(tabs, 400)
    app.processEvents()
    strip = strip_of(dialog)
    bar = strip.widget()
    bar.setCurrentIndex(3)
    assert tabs.currentIndex() == 3
    tabs.setCurrentIndex(7)
    assert bar.currentIndex() == 7
    # the last tab was scrolled into view
    assert strip.horizontalScrollBar().value() == strip.horizontalScrollBar().maximum()


def test_hidden_tab_stays_hidden() -> None:
    dialog, tabs = make()
    tabs.setTabVisible(1, False)
    _fit_tabs(tabs, 400)
    bar = strip_of(dialog).widget()
    assert not bar.isTabVisible(1)
    bar.setCurrentIndex(2)
    assert tabs.currentIndex() == 2


def test_wide_screen_keeps_tabs() -> None:
    dialog, tabs = make()
    _fit_tabs(tabs, 400)
    # rotated to landscape on a big phone, or an iPad
    _fit_tabs(tabs, 3000)
    assert not tabs.tabBar().isHidden()
    assert strip_of(dialog).isHidden()
    _fit_tabs(tabs, 400)
    assert len(dialog.findChildren(TabStrip, TAB_STRIP)) == 1
    assert tabs.tabBar().isHidden()


def test_tabs_that_fit_get_no_strip() -> None:
    dialog, tabs = make()
    _fit_tabs(tabs, 3000)
    assert strip_of(dialog) is None


def _mouse(widget: QWidget, kind: QEvent.Type, x: int) -> None:
    pos = QPointF(x, widget.height() / 2)
    button = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseMove else Qt.MouseButton.LeftButton
    QApplication.sendEvent(
        widget,
        QMouseEvent(
            kind, pos, QPointF(widget.mapToGlobal(pos)), button, Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        ),
    )


def test_tap_picks_tab_even_if_the_finger_moved_a_little() -> None:
    dialog, tabs = make()
    _fit_tabs(tabs, 400)
    app.processEvents()
    bar = strip_of(dialog).widget()
    x = bar.tabRect(2).center().x()
    _mouse(bar, QEvent.Type.MouseButtonPress, x)
    # the press alone doesn't switch: it may be the start of a drag
    assert tabs.currentIndex() == 0
    _mouse(bar, QEvent.Type.MouseMove, x + 4)
    _mouse(bar, QEvent.Type.MouseButtonRelease, x + 4)
    assert tabs.currentIndex() == 2


def test_drag_scrolls_tabs_without_switching() -> None:
    dialog, tabs = make()
    _fit_tabs(tabs, 400)
    app.processEvents()
    strip = strip_of(dialog)
    bar = strip.widget()
    x = bar.tabRect(2).center().x()
    _mouse(bar, QEvent.Type.MouseButtonPress, x)
    _mouse(bar, QEvent.Type.MouseMove, x - 30)
    _mouse(bar, QEvent.Type.MouseMove, x - 120)
    _mouse(bar, QEvent.Type.MouseButtonRelease, x - 120)
    assert tabs.currentIndex() == 0
    assert strip.horizontalScrollBar().value() > 0


def test_page_that_scrolls_by_itself_scrolls_with_a_drag() -> None:
    # Kioku's own Advanced tab is a QScrollArea already
    dialog, tabs = make()
    page = QScrollArea()
    page.setWidget(QWidget())
    tabs.addTab(page, "Advanced")
    _fit_tabs(tabs, 400)
    assert tabs.widget(tabs.count() - 1) is page
    assert QScroller.hasScroller(page.viewport())
