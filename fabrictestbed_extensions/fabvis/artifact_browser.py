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

"""Interactive artifact browser GUI for FABRIC testbed.

Provides a styled interface for searching, filtering, and downloading
artifacts from the FABRIC Artifact Manager. Each artifact is shown as a
card with title, description, tags, version selector, and download
button inside a scrollable container.

Usage::

    from fabrictestbed_extensions.fabvis import ArtifactBrowser

    fablib = FablibManager()
    browser = ArtifactBrowser(fablib)
    browser.show()
"""

import logging
import os
import tarfile
import traceback

import ipywidgets as widgets
from IPython.display import display

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
    get_logo_data_url,
)

logger = logging.getLogger(__name__)


class ArtifactBrowser:
    """Interactive FABRIC Artifact Manager browser.

    Displays artifacts as styled cards with title/tag filtering,
    version selection, and one-click download with auto-extraction.
    The card list is scrollable so it works well with 100+ artifacts.

    Parameters
    ----------
    fablib : FablibManager
        An initialized FablibManager instance.
    download_dir : str, optional
        Directory for downloaded artifacts. Defaults to ``~/work``.
    """

    def __init__(self, fablib, download_dir: "str | None" = None):
        self._fablib = fablib
        self._download_dir = download_dir or os.path.expanduser("~/work")
        self._artifacts: list = []
        self._card_container = None
        self._build_ui()

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
                f'FABRIC Artifact Browser</span></div>'
            )
        )

        # ── Filter bar ──
        self._title_filter = widgets.Text(
            placeholder="Filter by title...",
            layout=widgets.Layout(flex="1", min_width="200px"),
        )
        self._tag_filter = widgets.Text(
            placeholder="Filter by tag...",
            layout=widgets.Layout(flex="1", min_width="150px"),
        )
        self._refresh_btn = widgets.Button(
            description="Refresh",
            icon="refresh",
            layout=widgets.Layout(width="100px", height="32px"),
        )
        self._refresh_btn.style.button_color = FABRIC_PRIMARY

        filter_label = widgets.HTML(
            value=(
                f'<span style="font-family:{FABRIC_BODY_FONT}; font-size:12px;'
                f' font-weight:500; color:{FABRIC_DARK};">Search:</span>'
            ),
            layout=widgets.Layout(width="55px"),
        )
        filter_bar = widgets.HBox(
            [filter_label, self._title_filter, self._tag_filter, self._refresh_btn],
            layout=widgets.Layout(
                padding="8px 16px",
                gap="8px",
                align_items="center",
                border_bottom=f"1px solid {FABRIC_BG_TINT}",
            ),
        )

        self._title_filter.observe(self._on_filter_change, names="value")
        self._tag_filter.observe(self._on_filter_change, names="value")
        self._refresh_btn.on_click(self._on_refresh)

        # ── Scrollable card container ──
        self._card_container = widgets.VBox(
            layout=widgets.Layout(
                padding="8px 16px",
                flex="0 0 auto",
                width="100%",
                min_width="500px",
            )
        )
        # Wrap in a box with fixed height and overflow scroll.
        # align_items="flex-start" prevents flex from squashing cards.
        # overflow_x="auto" adds a horizontal scrollbar only when needed.
        self._scroll_box = widgets.Box(
            [self._card_container],
            layout=widgets.Layout(
                height="500px",
                overflow_y="scroll",
                overflow_x="auto",
                border_bottom=f"1px solid {FABRIC_BG_TINT}",
                align_items="flex-start",
                width="100%",
            ),
        )

        # ── Status bar ──
        self._status = widgets.HTML(
            value=self._status_html("Loading artifacts...", "info"),
            layout=widgets.Layout(padding="8px 16px"),
        )

        # ── Output for download messages ──
        self._output = widgets.Output(
            layout=widgets.Layout(
                max_height="150px",
                overflow_y="auto",
                padding="4px 16px",
            )
        )

        # ── Assemble ──
        body = widgets.VBox(
            [filter_bar, self._scroll_box, self._status, self._output],
            layout=widgets.Layout(
                padding="0 0 12px 0",
                border=f"1px solid {FABRIC_PRIMARY_LIGHT}",
                border_radius="0 0 10px 10px",
                background_color=FABRIC_WHITE,
                width="100%",
            ),
        )

        css_widget = widgets.HTML(value=WIDGET_SOFT_CSS)
        self._widget = widgets.VBox(
            [css_widget, header, body],
            layout=widgets.Layout(
                width="100%",
                margin="8px 0",
            ),
        )
        self._widget.add_class("fabvis-soft")

        # Load artifacts
        self._load_artifacts()

    def _status_html(self, message: str, level: str = "info") -> str:
        color_map = {
            "info": FABRIC_PRIMARY_DARK,
            "success": FABRIC_SUCCESS,
            "error": FABRIC_DANGER,
            "warning": FABRIC_WARNING,
        }
        bg_map = {
            "info": FABRIC_BG_TINT,
            "success": "#e0f2f1",
            "error": "#fce4ec",
            "warning": "#fff3e0",
        }
        icon_map = {
            "info": "&#9432;",
            "success": "&#10004;",
            "error": "&#10060;",
            "warning": "&#9888;",
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

    def _load_artifacts(self) -> None:
        """Fetch artifacts from the artifact manager."""
        try:
            self._artifacts = self._fablib.get_manager().list_artifacts()
            self._update_cards(self._artifacts)
            count = len(self._artifacts)
            self._status.value = self._status_html(
                f"Found {count} artifact{'s' if count != 1 else ''}.", "success"
            )
        except Exception as e:
            self._artifacts = []
            self._status.value = self._status_html(
                f"Failed to load artifacts: {e}", "error"
            )
            logger.exception("Failed to load artifacts")

    def _on_refresh(self, _btn) -> None:
        self._output.clear_output()
        self._status.value = self._status_html("Refreshing...", "info")
        self._load_artifacts()

    def _on_filter_change(self, _change) -> None:
        title_text = self._title_filter.value.lower()
        tag_text = self._tag_filter.value.lower()
        filtered = self._artifacts
        if title_text:
            filtered = [a for a in filtered if title_text in a["title"].lower()]
        if tag_text:
            filtered = [
                a for a in filtered
                if tag_text in ", ".join(a.get("tags", [])).lower()
            ]
        self._update_cards(filtered)
        self._status.value = self._status_html(
            f"Showing {len(filtered)} of {len(self._artifacts)} artifacts.", "info"
        )

    def _update_cards(self, artifacts: list) -> None:
        """Rebuild the card list from the given artifacts."""
        cards = []
        for artifact in artifacts:
            card = self._build_card(artifact)
            cards.append(card)

        if not cards:
            cards.append(widgets.HTML(
                value=(
                    f'<div style="font-family:{FABRIC_BODY_FONT}; font-size:13px;'
                    f' color:{FABRIC_SECONDARY}; padding:20px; text-align:center;">'
                    f'No artifacts found.</div>'
                )
            ))
        self._card_container.children = cards

    def _build_card(self, artifact: dict) -> widgets.Widget:
        """Build a styled card widget for one artifact."""
        title = artifact.get("title", "Untitled")
        desc = artifact.get("description_short", "")
        tags = artifact.get("tags", [])
        authors = ", ".join(a["name"] for a in artifact.get("authors", []))
        project = artifact.get("project_name", "N/A")

        # Tags as small pills
        tag_pills = " ".join(
            f'<span style="display:inline-block; background:{FABRIC_BG_TINT};'
            f' color:{FABRIC_PRIMARY_DARK}; padding:2px 8px; border-radius:10px;'
            f' font-size:10px; margin:1px 2px;">{t}</span>'
            for t in tags
        )

        info_html = widgets.HTML(
            value=(
                f'<div style="font-family:{FABRIC_BODY_FONT}; word-wrap:break-word;'
                f' overflow-wrap:break-word;">'
                f'<div style="font-size:13px; font-weight:600; color:{FABRIC_DARK};'
                f' margin-bottom:3px;">{title}</div>'
                f'<div style="font-size:11px; color:{FABRIC_SECONDARY};'
                f' margin-bottom:4px;">{desc}</div>'
                f'<div style="margin-bottom:3px;">{tag_pills}</div>'
                f'<div style="font-size:10px; color:{FABRIC_SECONDARY};">'
                f'Project: {project} &nbsp;|&nbsp; Authors: {authors}</div>'
                f'</div>'
            ),
            layout=widgets.Layout(flex="1 1 0px", min_width="0px", overflow="hidden"),
        )

        # Version dropdown
        versions = artifact.get("versions", [])
        version_options = [
            (f"v{v['version']}", v["urn"]) for v in versions
        ]
        version_dd = widgets.Dropdown(
            options=version_options if version_options else [("--", "")],
            layout=widgets.Layout(width="90px"),
        )

        # Download button
        dl_btn = widgets.Button(
            description="Download",
            icon="download",
            layout=widgets.Layout(width="100px", height="30px"),
        )
        dl_btn.style.button_color = FABRIC_SUCCESS

        dl_btn.on_click(
            lambda _b, _title=title, _dd=version_dd: self._on_download(
                _title, _dd.value, _dd.label
            )
        )

        controls = widgets.VBox(
            [version_dd, dl_btn],
            layout=widgets.Layout(
                align_items="flex-end",
                gap="4px",
                min_width="120px",
            ),
        )

        card = widgets.HBox(
            [info_html, controls],
            layout=widgets.Layout(
                padding="10px 14px",
                margin="0 0 6px 0",
                border=f"1px solid {FABRIC_BG_TINT}",
                border_radius="8px",
                align_items="center",
                background_color=FABRIC_WHITE,
                flex="0 0 auto",
            ),
        )
        return card

    def _on_download(self, title: str, version_urn: str, version_label: str) -> None:
        """Download and optionally extract an artifact."""
        if not version_urn:
            self._status.value = self._status_html("No version selected.", "warning")
            return

        self._output.clear_output()
        self._status.value = self._status_html(
            f"Downloading '{title}' {version_label}...", "info"
        )
        try:
            with self._output:
                location = self._fablib.download_artifact(
                    download_dir=self._download_dir,
                    version_urn=version_urn,
                    version=version_label,
                )
                print(f"Downloaded '{title}' {version_label} to {location}")

                if tarfile.is_tarfile(location):
                    extract_path = os.path.dirname(location)
                    with tarfile.open(location, "r:*") as tar:
                        tar.extractall(path=extract_path)
                    os.remove(location)
                    print(f"Extracted to {extract_path} (tar removed)")
                else:
                    print(f"File is not a tar archive — kept as-is at {location}")

            self._status.value = self._status_html(
                f"Downloaded '{title}' {version_label} successfully!", "success"
            )
        except Exception as e:
            self._status.value = self._status_html(
                f"Download failed: {e}", "error"
            )
            with self._output:
                traceback.print_exc()

    def show(self) -> None:
        """Display the artifact browser."""
        display(self._widget)

    def _repr_mimebundle_(self, **kwargs):
        """Allow direct cell display in Jupyter."""
        return self._widget._repr_mimebundle_(**kwargs)
