"""The review screen's bottom bar is measured when the screen opens, before
its Show Answer or answer buttons are put in; on a phone (no Edit or More
buttons below 583 px) it came out as tall as the home indicator's padding
and cut its buttons off. kioku.patches measures it again after each change."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import aqt.reviewer
from aqt.qt import QApplication, QObject

from kioku import patches

app = QApplication.instance() or QApplication([])


class Bar(QObject):
    def __init__(self) -> None:
        super().__init__()
        self.hidden = False
        self.calls: list[str] = []

    def eval(self, js: str) -> None:
        self.calls.append("eval")

    def adjustHeightToFit(self) -> None:
        self.calls.append("fit")


class Reviewer:
    def __init__(self) -> None:
        self.mw = type("MW", (), {})()
        self.mw.bottomWeb = Bar()

    def _showAnswerButton(self) -> None:
        self.mw.bottomWeb.eval("showQuestion(...)")

    def _showEaseButtons(self) -> None:
        self.mw.bottomWeb.eval("showAnswer(...)")


def test_bottom_bar_is_measured_after_its_buttons_change(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(aqt.reviewer, "Reviewer", Reviewer)
    monkeypatch.setattr(Reviewer, "_showAnswerButton", Reviewer._showAnswerButton)
    monkeypatch.setattr(Reviewer, "_showEaseButtons", Reviewer._showEaseButtons)
    patches._patch_review_bar_height()

    reviewer = Reviewer()
    bar = reviewer.mw.bottomWeb
    reviewer._showAnswerButton()
    reviewer._showEaseButtons()
    assert bar.calls == ["eval", "fit", "eval", "fit"]

    # Anki's "hide bottom bar during review" shrinks it to 1 px: left alone
    bar.calls.clear()
    bar.hidden = True
    reviewer._showAnswerButton()
    assert bar.calls == ["eval"]
