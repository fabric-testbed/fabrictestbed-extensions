#!/usr/bin/env python3
# MIT License
#
# Copyright (c) 2020 FABRIC Testbed
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Author: Paul Ruth (pruth@renci.org)

"""Interactive environment configuration GUI for FABRIC testbed.

Provides a beginner-friendly interface for configuring FABlib with
sensible defaults, validation, and one-click save.  Matches the fabvis
visual style.

Features:

- Pre-populates all values from an existing ``fabric_rc`` if found
- Token file at top of Identity section; auto-loads projects on start
- Project dropdown (or manual UUID entry via toggle button)
- Bastion username auto-filled from user info
- Browse buttons for all file paths
- Log level dropdown, log file, SSH command line
- Clickable site-avoid toggle buttons
- Preview RC file before saving

Usage::

    from fabrictestbed_extensions.fabvis import ConfigureGUI

    gui = ConfigureGUI()
    gui.show()
"""

import html as html_mod
import logging
import os
import re
import traceback
from pathlib import Path
from typing import Optional

import ipywidgets as widgets
from IPython.display import display

from fabrictestbed_extensions.fablib.constants import Constants

from .styles import (
    FABRIC_BODY_FONT,
    FABRIC_DARK,
    FABRIC_LIGHT,
    FABRIC_PRIMARY,
    FABRIC_PRIMARY_DARK,
    FABRIC_PRIMARY_LIGHT,
    FABRIC_SUCCESS,
    FABRIC_DANGER,
    FABRIC_WARNING,
    FABRIC_WHITE,
    FABRIC_BG_TINT,
    FABRIC_SECONDARY,
    FONT_IMPORT_CSS,
    WIDGET_SOFT_CSS,
    SITE_LOCATIONS,
    get_logo_data_url,
)

logger = logging.getLogger(__name__)

_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Mapping from fabric_rc env-var names (after stripping FABRIC_ prefix
# and lowering) to our internal field keys.  The rc file stores lines
# like ``export FABRIC_PROJECT_ID=xxx`` which the loader converts to
# key ``project_id``.
_RC_KEY_TO_FIELD = {
    "project_id": "project_id",
    "bastion_username": "bastion_username",
    "token_location": "token_location",
    "bastion_key_location": "bastion_key_location",
    "slice_private_key_file": "slice_private_key_file",
    "slice_public_key_file": "slice_public_key_file",
    "bastion_ssh_config_file": "bastion_ssh_config_file",
    "bastion_host": "bastion_host",
    "orchestrator_host": "orchestrator_host",
    "credmgr_host": "credmgr_host",
    "core_api_host": "core_api_host",
    "log_level": "log_level",
    "log_file": "log_file",
    "ssh_command_line": "ssh_command_line",
    "avoid": "avoid",
}


class ConfigureGUI:
    """Interactive FABRIC environment configuration GUI.

    Parameters
    ----------
    fabric_rc : str, optional
        Path to the fabric_rc config file.  Defaults to the standard
        location.  If the file exists, all values are pre-populated.
    """

    def __init__(self, fabric_rc: Optional[str] = None):
        self._fabric_rc = fabric_rc or Constants.DEFAULT_FABRIC_RC
        self._fields: dict = {}
        self._fablib = None
        self._projects: list = []
        self._loading_projects = False  # guard for re-entrant calls
        self._build_ui()
        self._load_existing_rc()
        # Try to auto-load projects after UI is built
        self._auto_load_projects()

    # ================================================================
    # UI Construction
    # ================================================================

    def _build_ui(self) -> None:
        """Construct the full widget tree."""
        # ── Header ──
        logo_url = get_logo_data_url()
        logo_html = (
            f'<img src="{logo_url}" style="height:36px; margin-right:12px;">'
            if logo_url else ""
        )
        header = widgets.HTML(
            value=(
                f'{FONT_IMPORT_CSS}'
                f'<div style="display:flex; align-items:center; padding:10px 16px;'
                f' background:linear-gradient(135deg, {FABRIC_PRIMARY_DARK}, {FABRIC_PRIMARY});'
                f' border-radius:10px 10px 0 0;">'
                f'{logo_html}'
                f'<span style="font-family:{FABRIC_BODY_FONT}; font-size:18px;'
                f' font-weight:600; color:{FABRIC_WHITE};">'
                f'FABRIC Environment Configuration</span></div>'
            )
        )

        # ── Sections ──
        identity_section = self._build_identity_section()
        path_section = self._build_path_section()
        logging_section = self._build_logging_section()
        avoid_section = self._build_avoid_section()
        host_section = self._build_host_section()

        # ── Action buttons ──
        self._validate_btn = widgets.Button(
            description="Validate & Configure",
            icon="check-circle",
            layout=widgets.Layout(width="180px", height="36px"),
        )
        self._validate_btn.style.button_color = FABRIC_SUCCESS

        self._save_btn = widgets.Button(
            description="Save Config",
            icon="save",
            layout=widgets.Layout(width="140px", height="36px"),
        )
        self._save_btn.style.button_color = FABRIC_PRIMARY

        self._preview_btn = widgets.Button(
            description="Preview RC File",
            icon="eye",
            layout=widgets.Layout(width="150px", height="36px"),
        )
        self._preview_btn.style.button_color = FABRIC_PRIMARY_LIGHT

        self._reset_btn = widgets.Button(
            description="Reset Defaults",
            icon="refresh",
            layout=widgets.Layout(width="140px", height="36px"),
        )
        self._reset_btn.style.button_color = FABRIC_WARNING

        self._validate_btn.on_click(self._on_validate)
        self._save_btn.on_click(self._on_save)
        self._preview_btn.on_click(self._on_preview)
        self._reset_btn.on_click(self._on_reset)

        button_bar = widgets.HBox(
            [self._validate_btn, self._save_btn, self._preview_btn, self._reset_btn],
            layout=widgets.Layout(
                padding="10px 16px",
                justify_content="flex-start",
                gap="8px",
            ),
        )

        # ── Status ──
        self._status = widgets.HTML(
            value=self._status_html("Initializing...", "info"),
            layout=widgets.Layout(padding="8px 16px"),
        )

        # ── Output ──
        self._output = widgets.Output(
            layout=widgets.Layout(
                max_height="300px",
                overflow_y="auto",
                padding="4px 16px",
            )
        )

        # ── Preview area (hidden by default) ──
        self._preview_html = widgets.HTML(
            value="",
            layout=widgets.Layout(padding="0 16px", display="none"),
        )

        # ── Assemble body ──
        self._body = widgets.VBox(
            [
                identity_section,
                path_section,
                logging_section,
                avoid_section,
                host_section,
                button_bar,
                self._status,
                self._preview_html,
                self._output,
            ],
            layout=widgets.Layout(
                padding="0 0 12px 0",
                border=f"1px solid {FABRIC_PRIMARY_LIGHT}",
                border_radius="0 0 10px 10px",
                background_color=FABRIC_WHITE,
            ),
        )

        css_widget = widgets.HTML(value=WIDGET_SOFT_CSS)
        self._widget = widgets.VBox(
            [css_widget, header, self._body],
            layout=widgets.Layout(width="100%", margin="8px 0"),
        )
        self._widget.add_class("fabvis-soft")

    # ── Identity Section ────────────────────────────────────────────

    def _build_identity_section(self) -> widgets.Widget:
        section_label = self._section_label("Identity")

        # Token file — at the top, with browse
        self._token_text = widgets.Text(
            value=Constants.DEFAULT_TOKEN_LOCATION,
            placeholder=Constants.DEFAULT_TOKEN_LOCATION,
            layout=widgets.Layout(flex="1", min_width="280px"),
        )
        self._fields["token_location"] = self._token_text
        self._token_text.observe(self._on_token_changed, names="value")

        self._token_indicator = widgets.HTML(value="", layout=widgets.Layout(width="20px"))

        token_browse = widgets.Button(
            description="Browse", icon="folder-open",
            layout=widgets.Layout(width="90px", height="28px"),
        )
        token_browse.style.button_color = FABRIC_BG_TINT
        token_browse.on_click(
            lambda _b: self._open_file_chooser("token_location", self._token_text)
        )

        token_row = widgets.HBox(
            [self._make_label("Token File", required=True),
             self._token_text, token_browse, self._token_indicator],
            layout=widgets.Layout(align_items="center", padding="3px 16px", gap="6px"),
        )

        # Project — dropdown (default) or manual text entry (toggle)
        self._project_dropdown = widgets.Dropdown(
            options=[("(loading...)", "")],
            value="",
            layout=widgets.Layout(flex="1", min_width="300px"),
        )
        self._project_dropdown.observe(self._on_project_selected, names="value")

        self._project_id_text = widgets.Text(
            value="",
            placeholder="Paste project UUID manually",
            layout=widgets.Layout(flex="1", min_width="300px", display="none"),
        )
        self._fields["project_id"] = self._project_id_text

        self._manual_toggle = widgets.ToggleButton(
            value=False,
            description="Manual",
            icon="pencil",
            tooltip="Toggle manual project ID entry",
            layout=widgets.Layout(width="90px", height="30px"),
        )
        self._manual_toggle.style.button_color = FABRIC_BG_TINT
        self._manual_toggle.observe(self._on_manual_toggle, names="value")

        self._load_projects_btn = widgets.Button(
            description="Reload",
            icon="refresh",
            layout=widgets.Layout(width="80px", height="30px"),
        )
        self._load_projects_btn.style.button_color = FABRIC_PRIMARY
        self._load_projects_btn.on_click(self._on_load_projects)

        project_row = widgets.HBox(
            [
                self._make_label("Project", required=True),
                self._project_dropdown,
                self._project_id_text,
                self._manual_toggle,
                self._load_projects_btn,
            ],
            layout=widgets.Layout(align_items="center", padding="3px 16px", gap="6px"),
        )

        # Bastion username
        self._bastion_username_text = widgets.Text(
            value="",
            placeholder="Auto-filled when projects load, or enter manually",
            layout=widgets.Layout(flex="1", min_width="300px"),
        )
        self._fields["bastion_username"] = self._bastion_username_text

        bastion_row = widgets.HBox(
            [self._make_label("Bastion Username", required=True), self._bastion_username_text],
            layout=widgets.Layout(align_items="center", padding="3px 16px"),
        )

        return widgets.VBox([section_label, token_row, project_row, bastion_row])

    # ── File Paths Section ──────────────────────────────────────────

    def _build_path_section(self) -> widgets.Widget:
        section_label = self._section_label("File Paths")
        rows = []

        path_defs = [
            ("bastion_key_location", "Bastion Private Key",
             Constants.DEFAULT_BASTION_KEY_LOCATION, True),
            ("slice_private_key_file", "Slice Private Key",
             Constants.DEFAULT_SLICE_PRIVATE_KEY_FILE, False),
            ("slice_public_key_file", "Slice Public Key",
             Constants.DEFAULT_SLICE_PUBLIC_KEY_FILE, False),
            ("bastion_ssh_config_file", "SSH Config File",
             Constants.DEFAULT_FABRIC_BASTION_SSH_CONFIG_FILE, False),
        ]

        for key, label, default, required in path_defs:
            text_w = widgets.Text(
                value=str(default), placeholder=str(default),
                layout=widgets.Layout(flex="1", min_width="280px"),
            )
            self._fields[key] = text_w

            browse_btn = widgets.Button(
                description="Browse", icon="folder-open",
                layout=widgets.Layout(width="90px", height="28px"),
            )
            browse_btn.style.button_color = FABRIC_BG_TINT
            browse_btn.on_click(
                lambda _b, _k=key, _t=text_w: self._open_file_chooser(_k, _t)
            )

            row = widgets.HBox(
                [self._make_label(label, required=required), text_w, browse_btn],
                layout=widgets.Layout(align_items="center", padding="3px 16px", gap="6px"),
            )
            rows.append(row)

        return widgets.VBox([section_label] + rows)

    # ── Logging & SSH Section ───────────────────────────────────────

    def _build_logging_section(self) -> widgets.Widget:
        section_label = self._section_label("Logging & SSH")

        self._log_level_dd = widgets.Dropdown(
            options=_LOG_LEVELS, value=Constants.DEFAULT_LOG_LEVEL,
            layout=widgets.Layout(width="140px"),
        )
        self._fields["log_level"] = self._log_level_dd

        log_level_row = widgets.HBox(
            [self._make_label("Log Level"), self._log_level_dd],
            layout=widgets.Layout(align_items="center", padding="3px 16px"),
        )

        log_file_text = widgets.Text(
            value=Constants.DEFAULT_LOG_FILE, placeholder=Constants.DEFAULT_LOG_FILE,
            layout=widgets.Layout(flex="1", min_width="280px"),
        )
        self._fields["log_file"] = log_file_text

        log_browse = widgets.Button(
            description="Browse", icon="folder-open",
            layout=widgets.Layout(width="90px", height="28px"),
        )
        log_browse.style.button_color = FABRIC_BG_TINT
        log_browse.on_click(
            lambda _b: self._open_file_chooser("log_file", log_file_text)
        )

        log_file_row = widgets.HBox(
            [self._make_label("Log File"), log_file_text, log_browse],
            layout=widgets.Layout(align_items="center", padding="3px 16px", gap="6px"),
        )

        ssh_cmd_text = widgets.Text(
            value=Constants.DEFAULT_FABRIC_SSH_COMMAND_LINE,
            placeholder="SSH command template",
            layout=widgets.Layout(flex="1", min_width="280px"),
        )
        self._fields["ssh_command_line"] = ssh_cmd_text

        ssh_row = widgets.HBox(
            [self._make_label("SSH Command"), ssh_cmd_text],
            layout=widgets.Layout(align_items="center", padding="3px 16px"),
        )

        return widgets.VBox([section_label, log_level_row, log_file_row, ssh_row])

    # ── Avoid Sites Section ─────────────────────────────────────────

    def _build_avoid_section(self) -> widgets.Widget:
        section_label = self._section_label("Sites to Avoid")

        hint = widgets.HTML(
            value=(
                f'<div style="font-family:{FABRIC_BODY_FONT}; font-size:11px;'
                f' color:{FABRIC_SECONDARY}; padding:2px 16px;">'
                f'Click sites to toggle. Orange = avoided.</div>'
            )
        )

        site_names = sorted(SITE_LOCATIONS.keys())
        self._avoid_buttons: dict = {}
        btn_list = []
        for site in site_names:
            tb = widgets.ToggleButton(
                value=False, description=site,
                layout=widgets.Layout(width="72px", height="30px"),
                tooltip=f"Toggle {site}",
            )
            tb.style.button_color = FABRIC_LIGHT
            tb.observe(self._on_avoid_toggle, names="value")
            self._avoid_buttons[site] = tb
            btn_list.append(tb)

        self._avoid_text = widgets.Text(
            value="", placeholder="Comma-separated (auto-updated by toggles)",
            layout=widgets.Layout(flex="1", min_width="280px"),
        )
        self._avoid_text.observe(self._on_avoid_text_change, names="value")
        self._fields["avoid"] = self._avoid_text

        grid = widgets.GridBox(
            btn_list,
            layout=widgets.Layout(
                grid_template_columns="repeat(auto-fill, 76px)",
                grid_gap="4px", padding="4px 16px",
            ),
        )

        avoid_text_row = widgets.HBox(
            [self._make_label("Avoid List"), self._avoid_text],
            layout=widgets.Layout(align_items="center", padding="3px 16px"),
        )

        return widgets.VBox([section_label, hint, grid, avoid_text_row])

    # ── Host Section (Advanced) ─────────────────────────────────────

    def _build_host_section(self) -> widgets.Widget:
        host_defs = [
            ("bastion_host", "Bastion Host", Constants.DEFAULT_FABRIC_BASTION_HOST),
            ("orchestrator_host", "Orchestrator",
             Constants.DEFAULT_FABRIC_ORCHESTRATOR_HOST),
            ("credmgr_host", "Credential Mgr",
             Constants.DEFAULT_FABRIC_CREDMGR_HOST),
            ("core_api_host", "Core API Host",
             Constants.DEFAULT_FABRIC_CORE_API_HOST),
        ]
        rows = []
        for key, label, default in host_defs:
            text_w = widgets.Text(
                value=str(default), placeholder=str(default),
                layout=widgets.Layout(flex="1", min_width="300px"),
            )
            self._fields[key] = text_w
            row = widgets.HBox(
                [self._make_label(label), text_w],
                layout=widgets.Layout(align_items="center", padding="3px 16px"),
            )
            rows.append(row)

        content = widgets.VBox(rows)
        accordion = widgets.Accordion(children=[content])
        accordion.set_title(0, "Service Hosts (Advanced)")
        accordion.selected_index = None
        return accordion

    # ================================================================
    # Helpers
    # ================================================================

    def _make_label(self, text: str, required: bool = False) -> widgets.HTML:
        asterisk = f' <span style="color:{FABRIC_DANGER};">*</span>' if required else ""
        return widgets.HTML(
            value=(
                f'<span style="font-family:{FABRIC_BODY_FONT}; font-size:12px;'
                f' font-weight:500; color:{FABRIC_DARK};">'
                f'{text}{asterisk}</span>'
            ),
            layout=widgets.Layout(width="160px", min_width="160px", margin="0 8px 0 0"),
        )

    def _section_label(self, title: str) -> widgets.HTML:
        return widgets.HTML(
            value=(
                f'<div style="font-family:{FABRIC_BODY_FONT}; font-size:13px;'
                f' font-weight:600; color:{FABRIC_PRIMARY_DARK};'
                f' padding:10px 16px 4px 16px; border-bottom:1px solid {FABRIC_BG_TINT};">'
                f'{title}</div>'
            )
        )

    def _status_html(self, message: str, level: str = "info") -> str:
        color_map = {
            "info": FABRIC_PRIMARY_DARK, "success": FABRIC_SUCCESS,
            "error": FABRIC_DANGER, "warning": FABRIC_WARNING,
        }
        bg_map = {
            "info": FABRIC_BG_TINT, "success": "#e0f2f1",
            "error": "#fce4ec", "warning": "#fff3e0",
        }
        icon_map = {
            "info": "&#9432;", "success": "&#10004;",
            "error": "&#10060;", "warning": "&#9888;",
        }
        color = color_map.get(level, FABRIC_DARK)
        bg = bg_map.get(level, FABRIC_BG_TINT)
        icon = icon_map.get(level, "")
        return (
            f'<div style="font-family:{FABRIC_BODY_FONT}; font-size:12px;'
            f' color:{color}; background:{bg}; padding:8px 12px;'
            f' border-radius:6px; border-left:4px solid {color};">'
            f'{icon} {message}</div>'
        )

    def _set_token_indicator(self, ok: Optional[bool]) -> None:
        """Show a green check, red X, or nothing next to the token field."""
        if ok is True:
            self._token_indicator.value = (
                f'<span style="color:{FABRIC_SUCCESS}; font-size:16px;" '
                f'title="Token file found">&#10004;</span>'
            )
        elif ok is False:
            self._token_indicator.value = (
                f'<span style="color:{FABRIC_DANGER}; font-size:16px;" '
                f'title="Token file not found — set this first">&#10060;</span>'
            )
        else:
            self._token_indicator.value = ""

    def _highlight_token(self) -> None:
        """Visually highlight the token field to draw attention."""
        self._token_text.layout.border = f"2px solid {FABRIC_DANGER}"
        self._set_token_indicator(False)

    def _unhighlight_token(self) -> None:
        self._token_text.layout.border = ""
        self._set_token_indicator(True)

    # ================================================================
    # Load existing fabric_rc
    # ================================================================

    def _load_existing_rc(self) -> None:
        """If fabric_rc exists, parse it and populate all fields."""
        rc_path = Path(self._fabric_rc).expanduser()
        if not rc_path.is_file():
            self._status.value = self._status_html(
                f"No existing config found at <b>{self._fabric_rc}</b>. "
                "Using defaults.", "info"
            )
            return

        try:
            parsed = self._parse_rc_file(rc_path)
            if not parsed:
                return

            for rc_key, field_key in _RC_KEY_TO_FIELD.items():
                val = parsed.get(rc_key, "")
                if not val:
                    continue
                w = self._fields.get(field_key)
                if w is None:
                    continue

                if field_key == "log_level" and isinstance(w, widgets.Dropdown):
                    upper = str(val).upper()
                    if upper in _LOG_LEVELS:
                        w.value = upper
                elif field_key == "avoid":
                    if isinstance(val, list):
                        val = ",".join(val)
                    w.value = str(val)
                    # Sync avoid toggles
                    self._on_avoid_text_change(None)
                else:
                    w.value = str(val)

            self._status.value = self._status_html(
                f"Loaded existing config from <b>{self._fabric_rc}</b>.", "success"
            )
        except Exception as e:
            logger.debug(f"Could not load existing rc: {e}")

    @staticmethod
    def _parse_rc_file(path: Path) -> dict:
        """Parse a fabric_rc (bash export) file into a dict."""
        result = {}
        export_pat = re.compile(r"^export\s+([^=]+)=(.*)$", re.IGNORECASE)
        with open(path, "r") as f:
            for line in f:
                m = export_pat.match(line.strip())
                if m:
                    key, value = m.groups()
                    value = value.strip().strip("'").strip('"')
                    # Convert FABRIC_XXX to lower xxx
                    key = key.replace("FABRIC_", "").lower()
                    if key == "avoid" and value:
                        value = value.split(",")
                    result[key] = value
        return result

    # ================================================================
    # Token change → auto-reload projects
    # ================================================================

    def _on_token_changed(self, change) -> None:
        """When the token file path changes, try to reload projects."""
        token_path = (change.get("new") or "").strip()
        if token_path:
            p = Path(token_path).expanduser()
            if p.is_file():
                self._unhighlight_token()
                self._auto_load_projects()
                return
        # File doesn't exist or empty
        self._set_token_indicator(None)

    # ================================================================
    # Project loading
    # ================================================================

    def _auto_load_projects(self) -> None:
        """Try to load projects silently.  Highlight token on failure."""
        if self._loading_projects:
            return
        token_path = self._token_text.value.strip()
        if not token_path:
            self._highlight_token()
            self._status.value = self._status_html(
                "Set the <b>Token File</b> path to load your projects.", "warning"
            )
            return
        p = Path(token_path).expanduser()
        if not p.is_file():
            self._highlight_token()
            self._status.value = self._status_html(
                f"Token file not found: <b>{token_path}</b>. "
                "Please set a valid token file.", "warning"
            )
            return

        self._do_load_projects()

    def _on_load_projects(self, _btn) -> None:
        """Manual reload button handler."""
        self._do_load_projects()

    def _do_load_projects(self) -> None:
        """Fetch projects and user info from FABRIC."""
        if self._loading_projects:
            return
        self._loading_projects = True
        self._output.clear_output()
        self._status.value = self._status_html("Loading projects from FABRIC...", "info")

        try:
            from fabrictestbed_extensions.fablib.fablib import FablibManager

            kwargs = {}
            token_val = self._token_text.value.strip()
            if token_val:
                kwargs["token_location"] = token_val
            for fkey in ("credmgr_host", "core_api_host"):
                w = self._fields.get(fkey)
                if w and w.value.strip():
                    kwargs[fkey] = w.value.strip()

            # Need some project_id to create FablibManager
            pid = self._project_id_text.value.strip()
            kwargs["project_id"] = pid if pid else "placeholder"

            fl = FablibManager(**kwargs)
            manager = fl.get_manager()

            # Fetch user info → bastion username
            try:
                user_info = manager.get_user_info()
                bastion_login = user_info.get(Constants.BASTION_LOGIN, "")
                if bastion_login and not self._bastion_username_text.value.strip():
                    self._bastion_username_text.value = bastion_login
            except Exception as e:
                logger.debug(f"Could not fetch user info: {e}")

            # Fetch projects
            self._projects = manager.get_project_info()
            options = [("-- select a project --", "")]
            for proj in self._projects:
                p_uuid = proj.get("uuid", "")
                p_name = proj.get("name", p_uuid)
                options.append((f"{p_name}  ({p_uuid[:8]}...)", p_uuid))

            self._project_dropdown.options = options

            # If there's a pre-populated project_id, select it
            existing_pid = self._project_id_text.value.strip()
            if existing_pid:
                known_ids = [opt[1] for opt in options]
                if existing_pid in known_ids:
                    self._project_dropdown.value = existing_pid

            self._unhighlight_token()
            self._status.value = self._status_html(
                f"Loaded {len(self._projects)} project(s). "
                "Select one from the dropdown.", "success"
            )
        except Exception as e:
            err_msg = str(e)
            if "token" in err_msg.lower() or "credential" in err_msg.lower():
                self._highlight_token()
            self._project_dropdown.options = [("(failed to load — check token file)", "")]
            self._status.value = self._status_html(
                f"Failed to load projects: {html_mod.escape(str(e))}", "error"
            )
            with self._output:
                traceback.print_exc()
        finally:
            self._loading_projects = False

    def _on_project_selected(self, change) -> None:
        pid = change.get("new", "")
        if pid:
            self._project_id_text.value = pid

    def _on_manual_toggle(self, change) -> None:
        """Toggle between dropdown and manual text entry for project."""
        manual = change.get("new", False)
        if manual:
            self._project_dropdown.layout.display = "none"
            self._project_id_text.layout.display = ""
            self._manual_toggle.style.button_color = FABRIC_WARNING
        else:
            self._project_dropdown.layout.display = ""
            self._project_id_text.layout.display = "none"
            self._manual_toggle.style.button_color = FABRIC_BG_TINT

    # ================================================================
    # Avoid toggles
    # ================================================================

    def _on_avoid_toggle(self, change) -> None:
        avoided = sorted(
            site for site, btn in self._avoid_buttons.items() if btn.value
        )
        for site, btn in self._avoid_buttons.items():
            btn.style.button_color = FABRIC_WARNING if btn.value else FABRIC_LIGHT
        self._avoid_text.unobserve(self._on_avoid_text_change, names="value")
        self._avoid_text.value = ",".join(avoided)
        self._avoid_text.observe(self._on_avoid_text_change, names="value")

    def _on_avoid_text_change(self, change) -> None:
        sites_in_text = {
            s.strip().upper() for s in self._avoid_text.value.split(",") if s.strip()
        }
        for site, btn in self._avoid_buttons.items():
            btn.unobserve(self._on_avoid_toggle, names="value")
            btn.value = site in sites_in_text
            btn.style.button_color = FABRIC_WARNING if btn.value else FABRIC_LIGHT
            btn.observe(self._on_avoid_toggle, names="value")

    # ================================================================
    # File chooser
    # ================================================================

    def _open_file_chooser(self, key: str, target_text: widgets.Text) -> None:
        start_path = target_text.value.strip()
        if start_path:
            start_dir = str(Path(start_path).expanduser().parent)
        else:
            start_dir = str(Path.home())

        try:
            p = Path(start_dir).expanduser()
            if not p.is_dir():
                p = Path.home()
        except Exception:
            p = Path.home()

        entries = self._list_dir_entries(p)

        path_text = widgets.Text(
            value=str(p), placeholder="Directory path",
            layout=widgets.Layout(flex="1"),
        )
        file_select = widgets.Select(
            options=entries, rows=8,
            layout=widgets.Layout(flex="1", min_width="350px"),
        )
        go_btn = widgets.Button(
            description="Go", layout=widgets.Layout(width="50px", height="28px"),
        )
        go_btn.style.button_color = FABRIC_PRIMARY
        up_btn = widgets.Button(
            description="Up", icon="arrow-up",
            layout=widgets.Layout(width="60px", height="28px"),
        )
        up_btn.style.button_color = FABRIC_BG_TINT
        select_btn = widgets.Button(
            description="Select", icon="check",
            layout=widgets.Layout(width="80px", height="28px"),
        )
        select_btn.style.button_color = FABRIC_SUCCESS
        cancel_btn = widgets.Button(
            description="Cancel",
            layout=widgets.Layout(width="80px", height="28px"),
        )
        cancel_btn.style.button_color = FABRIC_WARNING

        nav_bar = widgets.HBox(
            [path_text, go_btn, up_btn],
            layout=widgets.Layout(gap="4px", align_items="center"),
        )
        btn_bar = widgets.HBox(
            [select_btn, cancel_btn],
            layout=widgets.Layout(gap="6px", padding="4px 0"),
        )
        chooser_box = widgets.VBox(
            [nav_bar, file_select, btn_bar],
            layout=widgets.Layout(
                padding="8px",
                border=f"1px solid {FABRIC_PRIMARY_LIGHT}",
                border_radius="6px",
                margin="4px 16px",
                background_color=FABRIC_WHITE,
            ),
        )

        self._body.children = list(self._body.children) + [chooser_box]

        def _navigate(directory: Path):
            file_select.options = self._list_dir_entries(directory)
            path_text.value = str(directory)

        def _on_go(_b):
            try:
                d = Path(path_text.value.strip()).expanduser()
                if d.is_dir():
                    _navigate(d)
            except Exception:
                pass

        def _on_up(_b):
            try:
                d = Path(path_text.value.strip()).expanduser().parent
                _navigate(d)
            except Exception:
                pass

        def _on_dbl_click(change):
            val = change.get("new")
            if not val:
                return
            cur = Path(path_text.value.strip()).expanduser()
            target = cur / val
            try:
                if target.is_dir():
                    _navigate(target)
            except Exception:
                pass

        def _on_select(_b):
            selected = file_select.value
            if selected:
                cur = Path(path_text.value.strip()).expanduser()
                full = cur / selected
                target_text.value = str(full)
            _close()

        def _on_cancel(_b):
            _close()

        def _close():
            self._body.children = [c for c in self._body.children if c is not chooser_box]

        go_btn.on_click(_on_go)
        up_btn.on_click(_on_up)
        file_select.observe(_on_dbl_click, names="value")
        select_btn.on_click(_on_select)
        cancel_btn.on_click(_on_cancel)

    @staticmethod
    def _list_dir_entries(directory: Path) -> list[str]:
        try:
            items = sorted(directory.iterdir(),
                           key=lambda x: (not x.is_dir(), x.name.lower()))
            entries = []
            for item in items:
                if item.name.startswith("."):
                    continue
                name = item.name + "/" if item.is_dir() else item.name
                entries.append(name)
            return entries if entries else ["(empty)"]
        except PermissionError:
            return ["(permission denied)"]
        except Exception:
            return ["(error reading directory)"]

    # ================================================================
    # Config collection
    # ================================================================

    def _get_config_kwargs(self) -> dict:
        """Collect current field values into kwargs for FablibManager."""
        kwargs = {}
        for key, widget in self._fields.items():
            if isinstance(widget, widgets.Dropdown):
                val = widget.value if widget.value else ""
            elif isinstance(widget, widgets.Text):
                val = widget.value.strip()
            else:
                val = str(widget.value).strip() if hasattr(widget, "value") else ""
            if val:
                kwargs[key] = val
        kwargs["fabric_rc"] = self._fabric_rc
        return kwargs

    # ================================================================
    # RC file preview
    # ================================================================

    def _generate_rc_preview(self) -> str:
        """Generate the fabric_rc file content from current field values."""
        from fabrictestbed_extensions.fablib.config.config import Config
        lines = []
        for attr, attr_props in Config.REQUIRED_ATTRS.items():
            env_var = attr_props.get(Constants.ENV_VAR)
            if not env_var:
                continue
            # Look up field value
            w = self._fields.get(attr)
            if w is None:
                # Try to get a default
                value = attr_props.get(Constants.DEFAULT, "")
            elif isinstance(w, widgets.Dropdown):
                value = w.value or ""
            elif isinstance(w, widgets.Text):
                value = w.value.strip()
            else:
                value = str(getattr(w, "value", "")).strip()

            if isinstance(value, list):
                value = ",".join(value)
            lines.append(f"export {env_var}={value}")
        return "\n".join(lines)

    def _on_preview(self, _btn) -> None:
        """Toggle the RC file preview panel."""
        if self._preview_html.layout.display == "none":
            content = self._generate_rc_preview()
            escaped = html_mod.escape(content)
            self._preview_html.value = (
                f'<div style="font-family:{FABRIC_BODY_FONT}; padding:8px 0;">'
                f'<div style="font-size:12px; font-weight:600; color:{FABRIC_PRIMARY_DARK};'
                f' margin-bottom:6px;">Preview: {html_mod.escape(self._fabric_rc)}</div>'
                f'<pre style="background:{FABRIC_BG_TINT}; color:{FABRIC_DARK};'
                f' padding:10px 14px; border-radius:6px; font-size:11px;'
                f' line-height:1.6; overflow-x:auto; border:1px solid {FABRIC_PRIMARY_LIGHT};'
                f' white-space:pre-wrap; word-break:break-all;">{escaped}</pre></div>'
            )
            self._preview_html.layout.display = ""
            self._preview_btn.description = "Hide Preview"
            self._preview_btn.icon = "eye-slash"
        else:
            self._preview_html.layout.display = "none"
            self._preview_btn.description = "Preview RC File"
            self._preview_btn.icon = "eye"

    # ================================================================
    # Action button handlers
    # ================================================================

    def _on_validate(self, _btn) -> None:
        self._output.clear_output()
        self._preview_html.layout.display = "none"
        self._status.value = self._status_html("Validating configuration...", "info")
        try:
            from fabrictestbed_extensions.fablib.fablib import FablibManager
            kwargs = self._get_config_kwargs()
            self._fablib = FablibManager(**kwargs)
            with self._output:
                self._fablib.show_config()
                print("\n--- Running verify_and_configure ---\n")
                self._fablib.verify_and_configure()
                print("\nValidation complete.")
            self._status.value = self._status_html(
                "Configuration validated successfully!", "success"
            )
        except Exception as e:
            self._status.value = self._status_html(
                f"Validation failed: {html_mod.escape(str(e))}", "error"
            )
            with self._output:
                traceback.print_exc()

    def _on_save(self, _btn) -> None:
        self._output.clear_output()
        self._preview_html.layout.display = "none"
        self._status.value = self._status_html("Saving configuration...", "info")
        try:
            from fabrictestbed_extensions.fablib.fablib import FablibManager
            kwargs = self._get_config_kwargs()
            fablib = self._fablib or FablibManager(**kwargs)
            self._fablib = fablib
            with self._output:
                fablib.save_config()
                print(f"Configuration saved to: {self._fabric_rc}")
            self._status.value = self._status_html(
                f"Configuration saved to <b>{html_mod.escape(self._fabric_rc)}</b>",
                "success",
            )
        except Exception as e:
            self._status.value = self._status_html(
                f"Save failed: {html_mod.escape(str(e))}", "error"
            )
            with self._output:
                traceback.print_exc()

    def _on_reset(self, _btn) -> None:
        defaults = {
            "project_id": "",
            "bastion_username": "",
            "token_location": Constants.DEFAULT_TOKEN_LOCATION,
            "bastion_key_location": Constants.DEFAULT_BASTION_KEY_LOCATION,
            "slice_private_key_file": Constants.DEFAULT_SLICE_PRIVATE_KEY_FILE,
            "slice_public_key_file": Constants.DEFAULT_SLICE_PUBLIC_KEY_FILE,
            "bastion_ssh_config_file": Constants.DEFAULT_FABRIC_BASTION_SSH_CONFIG_FILE,
            "log_file": Constants.DEFAULT_LOG_FILE,
            "ssh_command_line": Constants.DEFAULT_FABRIC_SSH_COMMAND_LINE,
            "bastion_host": Constants.DEFAULT_FABRIC_BASTION_HOST,
            "orchestrator_host": Constants.DEFAULT_FABRIC_ORCHESTRATOR_HOST,
            "credmgr_host": Constants.DEFAULT_FABRIC_CREDMGR_HOST,
            "core_api_host": Constants.DEFAULT_FABRIC_CORE_API_HOST,
            "avoid": "",
        }
        for key, default in defaults.items():
            w = self._fields.get(key)
            if w:
                w.value = str(default)

        self._log_level_dd.value = Constants.DEFAULT_LOG_LEVEL
        self._project_dropdown.options = [("-- select a project --", "")]
        self._project_dropdown.value = ""
        self._manual_toggle.value = False

        for btn in self._avoid_buttons.values():
            btn.unobserve(self._on_avoid_toggle, names="value")
            btn.value = False
            btn.style.button_color = FABRIC_LIGHT
            btn.observe(self._on_avoid_toggle, names="value")

        self._token_text.layout.border = ""
        self._set_token_indicator(None)
        self._preview_html.layout.display = "none"
        self._status.value = self._status_html("Fields reset to defaults.", "info")

    # ================================================================
    # Display
    # ================================================================

    def show(self) -> None:
        """Display the configuration GUI."""
        display(self._widget)

    def _repr_mimebundle_(self, **kwargs):
        """Allow direct cell display in Jupyter."""
        return self._widget._repr_mimebundle_(**kwargs)
