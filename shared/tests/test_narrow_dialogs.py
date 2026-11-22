"""kioku.windows: desktop dialogs fitted to a phone's width. Long check box
texts wrap, side-by-side rows and label/field grids stack, a fixed-height box
grows with its wrapped text (Preferences on an iPhone: GitHub issue reports
of pages wider than the screen and AnkiHub's text cut off)."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QRect
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from kioku import windows

app = QApplication.instance() or QApplication([])
SCREEN = QRect(0, 0, 400, 800)
LONG = "Show fuzz delta next to answer button intervals, and a little more text"


def fit(dialog: QDialog) -> None:
    windows._screen_available = lambda: QRect(SCREEN)
    dialog.show()
    app.processEvents()
    windows._fit_children(dialog, SCREEN)
    dialog.resize(SCREEN.size())
    for _ in range(5):
        app.processEvents()


def test_long_check_box_text_wraps_and_still_toggles() -> None:
    dialog = QDialog()
    box = QCheckBox(LONG * 2)
    QVBoxLayout(dialog).addWidget(box)
    fit(dialog)
    label = dialog.findChild(windows._ButtonText)
    assert label is not None and label.wordWrap() and label.text() == LONG * 2
    assert box.text() == ""
    assert dialog.layout().totalMinimumSize().width() <= SCREEN.width()
    label.mouseReleaseEvent(type("E", (), {"position": lambda self: label.rect().center().toPointF()})())
    assert box.isChecked()
    # Anki hides and disables check boxes after building the dialog
    box.setEnabled(False)
    assert not label.isEnabled()
    box.hide()
    assert label.parentWidget().isHidden()
    box.show()
    assert not label.parentWidget().isHidden()
    # fitting again (the phone turned) doesn't wrap twice
    windows._fit_children(dialog, SCREEN)
    assert len(dialog.findChildren(windows._ButtonText)) == 1


def test_group_boxes_side_by_side_stack() -> None:
    dialog = QDialog()
    row = QHBoxLayout()
    for title in ("Review", "Answer keys"):
        group = QGroupBox(title)
        QVBoxLayout(group).addWidget(QLabel(title))
        row.addWidget(group)
    QVBoxLayout(dialog).addLayout(row)
    fit(dialog)
    assert row.direction() == row.Direction.TopToBottom


def test_label_field_grid_stacks_when_too_wide() -> None:
    dialog = QDialog()
    grid = QGridLayout()
    label = QLabel("Next day starts at, a long label")
    spin = QSpinBox()
    spin.setSuffix(" hours past midnight, and then some")
    grid.addWidget(label, 0, 0)
    grid.addWidget(spin, 0, 1)
    QVBoxLayout(dialog).addLayout(grid)
    fit(dialog)
    assert grid.getItemPosition(grid.indexOf(label))[:2] == (0, 0)
    assert grid.getItemPosition(grid.indexOf(spin))[:2] == (1, 0)
    # the spin box isn't squeezed below its text
    assert spin.width() >= spin.sizeHint().width() or spin.width() >= SCREEN.width() - 64


def test_narrow_rows_stay_side_by_side() -> None:
    dialog = QDialog()
    row = QHBoxLayout()
    row.addWidget(QLabel("Name"))
    row.addWidget(QPushButton("Log In"))
    QVBoxLayout(dialog).addLayout(row)
    fit(dialog)
    assert row.direction() == row.Direction.LeftToRight


def test_fixed_height_box_grows_with_wrapped_text() -> None:
    dialog = QDialog()
    group = QGroupBox("AnkiHub")
    group.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    text = QLabel("AnkiHub provides collaborative deck editing and additional study tools. " * 3)
    text.setWordWrap(True)
    row = QHBoxLayout(group)
    row.addWidget(text)
    row.addWidget(QPushButton("Log In"))
    layout = QVBoxLayout(dialog)
    layout.addWidget(group)
    layout.addStretch()
    fit(dialog)
    assert text.height() >= text.heightForWidth(text.width())


def test_main_window_rows_are_left_alone() -> None:
    # only dialogs: the browser's search row has its own handling
    window = QWidget()
    row = QHBoxLayout(window)
    for title in ("A", "B"):
        row.addWidget(QGroupBox(title))
    fit_window = windows._fit_children
    fit_window(window, SCREEN)
    assert row.direction() == row.Direction.LeftToRight
