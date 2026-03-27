"""SpaceGuard Qt menu bar application."""

from __future__ import annotations

import os
import sys
import time
from typing import Any

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from spaceguard import __version__
from spaceguard.cleanup import restart_noisy_daemons_via_osascript, run_cleanup
from spaceguard.launch_agent import (
    install_launch_agent,
    is_launch_agent_installed,
    remove_launch_agent,
)
from spaceguard.monitor import sample_metrics
from spaceguard.settings_store import load_settings, save_settings, settings_path
from spaceguard.state import (
    AlertState,
    TrayLevel,
    pressure_active,
    record_cleanup_completed,
    record_ignore,
    record_prompt_shown,
    step_should_prompt,
    tray_level,
)


def _debug(msg: str) -> None:
    if os.environ.get("SPACESGUARD_DEBUG"):
        print(msg, file=sys.stderr)


def _make_tray_icon(level: TrayLevel) -> QIcon:
    size = 22
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if level == TrayLevel.OK:
        color = QColor(72, 199, 116)
    elif level == TrayLevel.WARNING:
        color = QColor(230, 190, 72)
    else:
        color = QColor(224, 86, 86)
    painter.setBrush(color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(3, 3, size - 6, size - 6)
    painter.end()
    return QIcon(pm)


def _format_tooltip(metrics, level: TrayLevel, settings: dict[str, Any]) -> str:
    lines = [
        "SpaceGuard",
        f"Free disk: {metrics.disk_free_gb:.2f} GB",
    ]
    if metrics.swap_used_mb is None:
        lines.append("Swap: (unavailable)")
    else:
        lines.append(f"Swap used: {metrics.swap_used_mb:.0f} MB")
    lines.append(f"State: {level.value}")
    dw = settings["disk_warn_gb"]
    sw = settings["swap_warn_mb"]
    lines.append(f"Warn if disk < {dw} GB or swap > {sw} MB")
    return "\n".join(lines)


class SettingsDialog(QDialog):
    """Preferences: thresholds, debounce, cleanup targets, login item."""

    settings_changed = Signal()

    def __init__(self, settings: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("SpaceGuard Settings")
        self._settings = settings
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(300)
        self._save_timer.timeout.connect(self._flush_save)

        layout = QVBoxLayout(self)

        thr = QGroupBox("Thresholds")
        tform = QFormLayout(thr)
        self._disk_warn = QDoubleSpinBox()
        self._disk_warn.setRange(0.05, 500.0)
        self._disk_warn.setDecimals(3)
        self._disk_warn.setValue(float(settings["disk_warn_gb"]))
        self._disk_crit = QDoubleSpinBox()
        self._disk_crit.setRange(0.01, 500.0)
        self._disk_crit.setDecimals(3)
        self._disk_crit.setValue(float(settings["disk_crit_gb"]))
        self._swap_warn = QDoubleSpinBox()
        self._swap_warn.setRange(1.0, 65536.0)
        self._swap_warn.setValue(float(settings["swap_warn_mb"]))
        self._swap_crit = QDoubleSpinBox()
        self._swap_crit.setRange(1.0, 65536.0)
        self._swap_crit.setValue(float(settings["swap_crit_mb"]))
        for w in (self._disk_warn, self._disk_crit, self._swap_warn, self._swap_crit):
            w.valueChanged.connect(self._schedule_save)
        tform.addRow("Disk warning (GB free below):", self._disk_warn)
        tform.addRow("Disk critical (GB free below):", self._disk_crit)
        tform.addRow("Swap warning (MB used above):", self._swap_warn)
        tform.addRow("Swap critical (MB used above):", self._swap_crit)

        trig = QGroupBox("Triggers")
        t2 = QFormLayout(trig)
        self._en_disk = QCheckBox("Enable disk pressure alerts")
        self._en_disk.setChecked(bool(settings.get("enable_disk_trigger", True)))
        self._en_swap = QCheckBox("Enable swap pressure alerts")
        self._en_swap.setChecked(bool(settings.get("enable_swap_trigger", True)))
        self._en_disk.stateChanged.connect(self._schedule_save)
        self._en_swap.stateChanged.connect(self._schedule_save)
        t2.addRow(self._en_disk)
        t2.addRow(self._en_swap)

        deb = QGroupBox("Debounce & timing")
        dform = QFormLayout(deb)
        self._interval = QSpinBox()
        self._interval.setRange(15, 3600)
        self._interval.setValue(int(settings.get("check_interval_sec", 45)))
        self._consec = QSpinBox()
        self._consec.setRange(1, 10)
        self._consec.setValue(int(settings.get("consecutive_checks_required", 2)))
        self._cool_prompt = QSpinBox()
        self._cool_prompt.setRange(1, 1440)
        self._cool_prompt.setValue(int(settings.get("prompt_cooldown_min", 10)))
        self._cool_ignore = QSpinBox()
        self._cool_ignore.setRange(1, 1440)
        self._cool_ignore.setValue(int(settings.get("ignore_cooldown_min", 45)))
        for w in (self._interval, self._consec, self._cool_prompt, self._cool_ignore):
            w.valueChanged.connect(self._schedule_save)
        dform.addRow("Check interval (seconds):", self._interval)
        dform.addRow("Consecutive checks required:", self._consec)
        dform.addRow("Min minutes between prompts:", self._cool_prompt)
        dform.addRow("Ignore cooldown (minutes):", self._cool_ignore)

        ui = QGroupBox("Behavior")
        uform = QFormLayout(ui)
        self._notif_only = QCheckBox("Notifications only (no modal cleanup dialog)")
        self._notif_only.setChecked(bool(settings.get("notifications_only", False)))
        self._notif_only.stateChanged.connect(self._schedule_save)
        self._start_login = QCheckBox("Start at login (Launch Agent)")
        self._start_login.setChecked(
            bool(settings.get("start_at_login", False)) or is_launch_agent_installed()
        )
        self._start_login.stateChanged.connect(self._on_start_at_login)
        self._show_tray = QCheckBox("Show menu bar icon")
        self._show_tray.setChecked(bool(settings.get("show_tray_icon", True)))
        self._show_tray.stateChanged.connect(self._schedule_save)
        uform.addRow(self._notif_only)
        uform.addRow(self._start_login)
        uform.addRow(self._show_tray)

        clean = QGroupBox("Cleanup targets")
        cv = QVBoxLayout(clean)
        self._preset_checks: dict[str, QCheckBox] = {}
        presets = settings.get("cleanup_presets") or {}
        for key, label in (
            ("global_caches", "Global ~/Library/Caches"),
            ("logs", "Global ~/Library/Logs"),
            ("firefox_cache", "Firefox profile caches (cache2, startupCache)"),
            ("vscode_cache", "VS Code Cache / CachedData"),
            ("cursor_cache", "Cursor Cache / CachedData"),
            ("electron_slack", "Slack Cache / Code Cache"),
            ("electron_figma", "Figma Cache / Code Cache"),
        ):
            cb = QCheckBox(label)
            cb.setChecked(bool(presets.get(key, True)))
            cb.stateChanged.connect(self._schedule_save)
            self._preset_checks[key] = cb
            cv.addWidget(cb)

        custom_box = QGroupBox("Custom paths (under your home folder)")
        cvl = QVBoxLayout(custom_box)
        self._custom_list = QListWidget()
        for p in settings.get("custom_paths") or []:
            if isinstance(p, str) and p.strip():
                self._custom_list.addItem(p.strip())
        row = QHBoxLayout()
        self._custom_edit = QLineEdit()
        self._custom_edit.setPlaceholderText("~/path/to/dir")
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_custom)
        rem_btn = QPushButton("Remove selected")
        rem_btn.clicked.connect(self._remove_custom)
        row.addWidget(self._custom_edit)
        row.addWidget(add_btn)
        cvl.addWidget(self._custom_list)
        cvl.addLayout(row)
        cvl.addWidget(rem_btn)

        layout.addWidget(thr)
        layout.addWidget(trig)
        layout.addWidget(deb)
        layout.addWidget(ui)
        layout.addWidget(clean)
        layout.addWidget(custom_box)

        self._path_label = QLabel(f"Settings file: {settings_path()}")
        self._path_label.setWordWrap(True)
        layout.addWidget(self._path_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def closeEvent(self, event) -> None:
        self._flush_save()
        super().closeEvent(event)

    def _schedule_save(self) -> None:
        self._save_timer.start()

    def _flush_save(self) -> None:
        self._apply_to_dict()
        self.settings_changed.emit()

    def _apply_to_dict(self) -> None:
        s = self._settings
        s["disk_warn_gb"] = self._disk_warn.value()
        s["disk_crit_gb"] = self._disk_crit.value()
        s["swap_warn_mb"] = self._swap_warn.value()
        s["swap_crit_mb"] = self._swap_crit.value()
        s["enable_disk_trigger"] = self._en_disk.isChecked()
        s["enable_swap_trigger"] = self._en_swap.isChecked()
        s["check_interval_sec"] = self._interval.value()
        s["consecutive_checks_required"] = self._consec.value()
        s["prompt_cooldown_min"] = self._cool_prompt.value()
        s["ignore_cooldown_min"] = self._cool_ignore.value()
        s["notifications_only"] = self._notif_only.isChecked()
        s["start_at_login"] = self._start_login.isChecked()
        s["show_tray_icon"] = self._show_tray.isChecked()
        cp = s.setdefault("cleanup_presets", {})
        for k, cb in self._preset_checks.items():
            cp[k] = cb.isChecked()
        paths: list[str] = []
        for i in range(self._custom_list.count()):
            it = self._custom_list.item(i)
            if it:
                t = it.text().strip()
                if t:
                    paths.append(t)
        s["custom_paths"] = paths

    def _add_custom(self) -> None:
        t = self._custom_edit.text().strip()
        if not t:
            return
        self._custom_list.addItem(t)
        self._custom_edit.clear()
        self._schedule_save()

    def _remove_custom(self) -> None:
        for item in self._custom_list.selectedItems():
            self._custom_list.takeItem(self._custom_list.row(item))
        self._schedule_save()

    def _on_start_at_login(self) -> None:
        want = self._start_login.isChecked()
        if want:
            ok, msg = install_launch_agent()
            if not ok:
                QMessageBox.warning(
                    self,
                    "Launch Agent",
                    f"Could not install start-at-login: {msg}",
                )
                self._start_login.setChecked(False)
        else:
            remove_launch_agent()
        self._schedule_save()

    def apply_to_settings(self) -> None:
        """Sync widget values into shared settings dict."""
        self._apply_to_dict()


class SpaceGuardController(QObject):
    """Tray icon, polling timer, alerts, and settings."""

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self._app = app
        self.settings: dict[str, Any] = load_settings()
        self._alert_state = AlertState()
        self._tray: QSystemTrayIcon | None = None
        self._settings_dialog: SettingsDialog | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

        self._tray = QSystemTrayIcon(self)
        self._tray.setIcon(_make_tray_icon(TrayLevel.OK))
        menu = self._build_menu()
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()
        self._apply_timer_interval()
        self._timer.start()
        QTimer.singleShot(500, self._maybe_first_run_message)

    def _build_menu(self) -> QMenu:
        m = QMenu()
        act_settings = QAction("Settings…", self)
        act_settings.triggered.connect(self._open_settings)
        m.addAction(act_settings)
        act_clean = QAction("Run cleanup now…", self)
        act_clean.triggered.connect(self._manual_cleanup)
        m.addAction(act_clean)
        act_daemons = QAction("Restart noisy system daemons (admin)…", self)
        act_daemons.triggered.connect(self._restart_daemons)
        m.addAction(act_daemons)
        m.addSeparator()
        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(self._app.quit)
        m.addAction(act_quit)
        return m

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._open_settings()

    def _apply_timer_interval(self) -> None:
        sec = int(self.settings.get("check_interval_sec", 45))
        self._timer.setInterval(max(5, sec) * 1000)

    def _maybe_first_run_message(self) -> None:
        if self.settings.get("_shown_welcome", False):
            return
        self.settings["_shown_welcome"] = True
        save_settings(self.settings)
        QMessageBox.information(
            None,
            "SpaceGuard",
            "SpaceGuard runs in the menu bar and warns when disk space is low or "
            "swap use is high.\n\n"
            "Cleanup only affects paths you enable in Settings.\n\n"
            "Optional “Restart noisy daemons” asks macOS for an administrator password.",
        )

    def _open_settings(self) -> None:
        if self._settings_dialog is None:
            dlg = SettingsDialog(self.settings)
            dlg.settings_changed.connect(self._on_settings_changed_from_dialog)
            self._settings_dialog = dlg
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    def _on_settings_changed_from_dialog(self) -> None:
        if self._settings_dialog:
            self._settings_dialog.apply_to_settings()
        save_settings(self.settings)
        self._apply_timer_interval()
        if self._tray:
            vis = bool(self.settings.get("show_tray_icon", True))
            self._tray.setVisible(vis)

    def _on_tick(self) -> None:
        if not self._tray:
            return
        metrics = sample_metrics()
        level = tray_level(metrics, self.settings)
        pressure = pressure_active(metrics, self.settings)
        self._tray.setIcon(_make_tray_icon(level))
        self._tray.setToolTip(_format_tooltip(metrics, level, self.settings))
        _debug(
            f"[SpaceGuard] tick disk={metrics.disk_free_gb:.3f}GB "
            f"swap={metrics.swap_used_mb} level={level.value} pressure={pressure}"
        )

        now = time.monotonic()
        consec = int(self.settings.get("consecutive_checks_required", 2))
        prompt_cd = float(self.settings.get("prompt_cooldown_min", 10)) * 60.0
        ignore_cd = float(self.settings.get("ignore_cooldown_min", 45)) * 60.0

        new_state, should_prompt = step_should_prompt(
            now=now,
            pressure=pressure,
            consecutive_required=consec,
            prompt_cooldown_sec=prompt_cd,
            ignore_cooldown_sec=ignore_cd,
            state=self._alert_state,
        )
        self._alert_state = new_state

        if not should_prompt:
            return

        # Cooldown and debounce: mark prompt as shown before UI so ticks do not re-trigger.
        self._alert_state = record_prompt_shown(self._alert_state, now)

        disk = metrics.disk_free_gb
        swap = metrics.swap_used_mb
        swap_s = f"{swap:.0f} MB" if swap is not None else "n/a"
        body = (
            f"Disk free: {disk:.2f} GB\nSwap used: {swap_s}\n\n"
            "Run safe cleanup for selected cache locations?"
        )

        if self.settings.get("notifications_only", False):
            self._tray.showMessage(
                "SpaceGuard — system pressure",
                body,
                QSystemTrayIcon.MessageIcon.Warning,
                15000,
            )
        else:
            msg = QMessageBox()
            msg.setWindowTitle("SpaceGuard")
            msg.setText("System under pressure")
            msg.setInformativeText(body)
            msg.setStandardButtons(
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            msg.setDefaultButton(QMessageBox.StandardButton.Yes)
            result = msg.exec()
            if result == QMessageBox.StandardButton.Yes:
                self._run_cleanup_and_report()
                self._alert_state = record_cleanup_completed(self._alert_state, time.monotonic())
            else:
                self._alert_state = record_ignore(self._alert_state, time.monotonic())

    def _manual_cleanup(self) -> None:
        self._run_cleanup_and_report()

    def _run_cleanup_and_report(self) -> None:
        results, failures = run_cleanup(self.settings)
        lines = [f"{ok}\t{p}\t{detail}" for p, ok, detail in results[:40]]
        if len(results) > 40:
            lines.append("…")
        text = "\n".join(lines) if lines else "(nothing to clean)"
        QMessageBox.information(
            None,
            "Cleanup finished",
            f"Failures: {failures}\n\n{text}",
        )

    def _restart_daemons(self) -> None:
        ok, msg = restart_noisy_daemons_via_osascript()
        QMessageBox.information(
            None,
            "Daemons",
            "Completed." if ok else f"Issue: {msg}",
        )


def main() -> None:
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setApplicationName("SpaceGuard")
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None,
            "SpaceGuard",
            "System tray not available on this system.",
        )
        sys.exit(1)
    SpaceGuardController(app)
    sys.exit(app.exec())
