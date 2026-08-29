"""Shared visual language for the Syllavox desktop interface."""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication


APP_STYLESHEET = """
QMainWindow, QWidget#appPage {
    background: #f5f7fb;
    color: #172238;
}

QScrollArea#contentScroll, QWidget#scrollContent, QWidget#contentColumn,
QWidget#appFooterHost, QWidget#appFooter {
    background: transparent;
    border: none;
}

QLabel#eyebrowLabel {
    color: #6c7890;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1px;
}

QLabel#pageTitle {
    color: #14213d;
    font-size: 27px;
    font-weight: 700;
}

QLabel#pageSubtitle {
    color: #6c7890;
    font-size: 12px;
}

QLabel#stateLabel, QLabel#hotkeyStatus {
    background: #ffffff;
    border: 1px solid #e0e6f0;
    border-radius: 10px;
    color: #56647a;
    padding: 7px 10px;
}

QLabel#hotkeyStatus {
    background: #e9f8fa;
    border-color: #c6ecef;
    color: #126975;
}

QWidget#card, QGroupBox#card {
    background: #ffffff;
    border: 1px solid #e0e6f0;
    border-radius: 16px;
    padding: 18px 16px 16px 16px;
}

QGroupBox#card {
    margin-top: 12px;
}

QGroupBox#card::title {
    color: #14213d;
    left: 16px;
    padding: 0 6px;
    subcontrol-origin: margin;
}

QLabel#sectionHint, QLabel#characterCount, QLabel#feedbackLabel {
    color: #6c7890;
}

QLabel#feedbackLabel {
    padding-top: 4px;
}

QLabel#fieldError {
    color: #b94b46;
    font-size: 11px;
}

QPlainTextEdit#speechText, QLineEdit#hotkeyEditor,
QComboBox, QSpinBox, QDoubleSpinBox {
    background: #fbfcff;
    border: 1px solid #d8dfeb;
    border-radius: 10px;
    color: #172238;
    padding: 8px 10px;
    selection-background-color: #bcecf1;
    selection-color: #10233f;
}

QPlainTextEdit#speechText:focus, QLineEdit#hotkeyEditor:focus,
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #18b7d5;
    padding: 7px 9px;
}

QComboBox::drop-down {
    border: none;
    width: 28px;
}

QPushButton {
    background: #ffffff;
    border: 1px solid #d8dfeb;
    border-radius: 10px;
    color: #26354d;
    min-height: 34px;
    padding: 0 14px;
}

QPushButton:hover {
    background: #f1f5fa;
    border-color: #b9c7d9;
}

QPushButton:pressed {
    background: #e6edf5;
}

QPushButton:disabled {
    background: #f3f5f8;
    color: #a6afbd;
    border-color: #e5e9ef;
}

QPushButton#primaryButton {
    background: #14213d;
    border-color: #14213d;
    color: #ffffff;
    font-weight: 700;
}

QPushButton#primaryButton:hover {
    background: #22365d;
    border-color: #22365d;
}

QPushButton#accentButton {
    background: #18b7d5;
    border-color: #18b7d5;
    color: #062d39;
    font-weight: 700;
}

QPushButton#accentButton:hover {
    background: #55cbdc;
    border-color: #55cbdc;
}

QPushButton#quietButton {
    background: transparent;
    border-color: transparent;
    color: #397383;
}

QPushButton#quietButton:hover {
    background: #e9f8fa;
    border-color: #c6ecef;
}

QSlider::groove:horizontal {
    background: #e0e6f0;
    border-radius: 3px;
    height: 6px;
}

QSlider::sub-page:horizontal {
    background: #18b7d5;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 2px solid #18b7d5;
    border-radius: 7px;
    margin: -5px 0;
    width: 14px;
}

QCheckBox {
    color: #26354d;
    spacing: 8px;
}

QCheckBox::indicator {
    height: 18px;
    width: 18px;
}

QToolTip {
    background: #14213d;
    border: 1px solid #22365d;
    color: #ffffff;
    padding: 5px;
}
"""


def apply_app_theme(application: QApplication) -> None:
    """Apply the stable Syllavox palette and widget styling."""
    application.setStyle("Fusion")
    application.setFont(QFont("Segoe UI", 10))
    application.setStyleSheet(APP_STYLESHEET)


__all__ = ["APP_STYLESHEET", "apply_app_theme"]
