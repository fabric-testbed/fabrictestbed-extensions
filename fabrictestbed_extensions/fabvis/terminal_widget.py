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

"""Embedded xterm.js terminal widget for Jupyter notebooks.

Provides a real terminal emulator (xterm.js) inside an ipywidget with
a Python communication bridge. Supports ANSI escape sequences, cursor
movement, colors, and inline typing — no separate input box needed.

The bridge uses two hidden widgets:

- ``_to_js`` (HTML): Python writes base64-encoded output here; a
  JavaScript MutationObserver picks it up and feeds it to xterm.js.
- ``_from_js`` (Text): JavaScript writes base64-encoded keystrokes
  here; Python reads them via ``observe``.

Output is buffered and flushed every 50 ms so rapid SSH data doesn't
overwhelm the widget sync channel.
"""

import base64
import logging
import queue
import threading
import uuid

import ipywidgets as widgets

logger = logging.getLogger(__name__)

# xterm.js 4.x CDN URLs (UMD builds — work with plain <script> tags)
_XTERM_JS = "https://cdn.jsdelivr.net/npm/xterm@4.19.0/lib/xterm.js"
_XTERM_CSS = "https://cdn.jsdelivr.net/npm/xterm@4.19.0/css/xterm.css"
_XTERM_FIT = "https://cdn.jsdelivr.net/npm/xterm-addon-fit@0.5.0/lib/xterm-addon-fit.js"


class XtermWidget:
    """xterm.js terminal embedded in an ipywidget.

    Usage::

        xt = XtermWidget()
        xt.on_data = lambda data: ssh_channel.send(data)
        display(xt.widget)

        # From a reader thread:
        xt.write(ssh_channel.recv(4096).decode())

    Parameters
    ----------
    theme : str
        ``"dark"`` (default) or ``"light"``.
    """

    # Special prefix for out-of-band messages (resize events)
    _RESIZE_PREFIX = "__XTERM_RESIZE__:"

    def __init__(self, theme: str = "dark"):
        self._uid = uuid.uuid4().hex[:8]
        self._seq_out = 0
        self._seq_in = 0
        self._theme = theme

        # Output buffer + flush timer
        self._out_queue: queue.Queue = queue.Queue()
        self._flush_timer = None
        self._flush_lock = threading.Lock()

        # ── Hidden communication widgets ──

        # Python → JS: HTML widget whose value Python updates.
        # JS watches it with MutationObserver.
        self._to_js = widgets.HTML(value="")
        self._to_js.layout.height = "0px"
        self._to_js.layout.overflow = "hidden"
        self._to_js.layout.padding = "0"
        self._to_js.layout.margin = "0"
        self._to_js.add_class(f"fabvis-xt-out-{self._uid}")

        # JS → Python: Text widget whose value JS sets via DOM.
        # Python watches it with observe().
        self._from_js = widgets.Text(value="")
        self._from_js.layout.height = "0px"
        self._from_js.layout.overflow = "hidden"
        self._from_js.layout.padding = "0"
        self._from_js.layout.margin = "0"
        self._from_js.add_class(f"fabvis-xt-in-{self._uid}")

        # ── xterm.js container ──
        self._term_html = widgets.HTML(
            value=self._build_html(),
            layout=widgets.Layout(width="100%", flex="1"),
        )

        # ── Public widget ──
        self.widget = widgets.VBox(
            [self._term_html, self._to_js, self._from_js],
            layout=widgets.Layout(
                width="100%",
                flex="1",
                min_height="120px",
            ),
        )

        # ── Callbacks ──
        self.on_data = None       # called with (data: str) for user input
        self.on_resize = None     # called with (cols: int, rows: int)
        self._from_js.observe(self._on_js_input, names="value")

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def write(self, data: str) -> None:
        """Write data to the terminal (thread-safe, buffered).

        Call this from any thread (e.g. an SSH reader thread).
        Output is flushed to the frontend every ~50 ms.
        """
        self._out_queue.put(data)
        self._schedule_flush()

    def clear(self) -> None:
        """Clear the terminal screen."""
        self.write("\x1b[2J\x1b[H")

    # ----------------------------------------------------------------
    # Output buffering
    # ----------------------------------------------------------------

    def _schedule_flush(self) -> None:
        with self._flush_lock:
            if self._flush_timer is None:
                self._flush_timer = threading.Timer(0.05, self._flush)
                self._flush_timer.daemon = True
                self._flush_timer.start()

    def _flush(self) -> None:
        with self._flush_lock:
            self._flush_timer = None

        chunks = []
        while not self._out_queue.empty():
            try:
                chunks.append(self._out_queue.get_nowait())
            except queue.Empty:
                break

        if chunks:
            data = "".join(chunks)
            self._seq_out += 1
            encoded = base64.b64encode(data.encode("utf-8")).decode("ascii")
            self._to_js.value = (
                f'<span data-seq="{self._seq_out}" '
                f'data-d="{encoded}"></span>'
            )

    # ----------------------------------------------------------------
    # JS → Python input handling
    # ----------------------------------------------------------------

    def _on_js_input(self, change) -> None:
        val = change.get("new", "")
        if not val or ":" not in val:
            return

        sep = val.index(":")
        try:
            seq = int(val[:sep])
        except ValueError:
            return

        if seq <= self._seq_in:
            return
        self._seq_in = seq

        encoded = val[sep + 1:]
        try:
            data = base64.b64decode(encoded).decode("utf-8", errors="replace")
        except Exception:
            return

        # Check for resize event
        if data.startswith(self._RESIZE_PREFIX):
            try:
                rest = data[len(self._RESIZE_PREFIX):]
                cols, rows = rest.split(":", 1)
                if self.on_resize:
                    self.on_resize(int(cols), int(rows))
            except Exception:
                pass
            return

        # Normal input
        if self.on_data:
            self.on_data(data)

    # ----------------------------------------------------------------
    # HTML / JavaScript
    # ----------------------------------------------------------------

    def _build_html(self) -> str:
        uid = self._uid
        in_class = f"fabvis-xt-in-{uid}"
        out_class = f"fabvis-xt-out-{uid}"

        if self._theme == "light":
            bg = "#f8f9fa"
            fg = "#374955"
            cursor = "#374955"
            sel = "rgba(87,152,188,0.2)"
        else:
            bg = "#1e1e1e"
            fg = "#d4d4d4"
            cursor = "#d4d4d4"
            sel = "rgba(87,152,188,0.3)"

        return f"""
<link rel="stylesheet"
      href="{_XTERM_CSS}"
      id="fabvis-xterm-css-{uid}">
<div id="fabvis-xterm-{uid}"
     style="width:100%;height:100%;min-height:120px;background:{bg};"></div>
<script>
(function() {{
    var uid = '{uid}';
    var inClass = '{in_class}';
    var outClass = '{out_class}';
    var lastOutSeq = 0;
    var inSeq = 0;
    var inputBuf = '';
    var inputTimer = null;

    function loadScript(url, cb) {{
        var existing = document.querySelector('script[src="' + url + '"]');
        if (existing) {{
            if (existing._loaded) {{ cb(); return; }}
            existing.addEventListener('load', cb);
            return;
        }}
        var s = document.createElement('script');
        s.src = url;
        s._loaded = false;
        s.onload = function() {{ s._loaded = true; cb(); }};
        s.onerror = function() {{
            var c = document.getElementById('fabvis-xterm-' + uid);
            if (c) c.innerHTML = '<div style="color:#ff6b6b;padding:20px;'
                + 'font-family:monospace;">Failed to load xterm.js from CDN.'
                + ' Check your internet connection.</div>';
        }};
        document.head.appendChild(s);
    }}

    function sendInput() {{
        if (!inputBuf) return;
        inSeq++;
        var raw = inputBuf;
        inputBuf = '';
        inputTimer = null;
        try {{
            var encoded = btoa(unescape(encodeURIComponent(raw)));
        }} catch(e) {{
            return;
        }}
        var inp = document.querySelector('.' + inClass + ' input');
        if (!inp) return;
        var setter = Object.getOwnPropertyDescriptor(
            HTMLInputElement.prototype, 'value'
        ).set;
        setter.call(inp, inSeq + ':' + encoded);
        inp.dispatchEvent(new Event('input', {{bubbles:true}}));
        inp.dispatchEvent(new Event('change', {{bubbles:true}}));
    }}

    function init() {{
        var container = document.getElementById('fabvis-xterm-' + uid);
        if (!container) return;

        var term = new Terminal({{
            cursorBlink: true,
            theme: {{
                background: '{bg}',
                foreground: '{fg}',
                cursor: '{cursor}',
                cursorAccent: '{bg}',
                selectionBackground: '{sel}',
            }},
            fontFamily: "'Courier New', Courier, monospace",
            fontSize: 13,
            scrollback: 5000,
            convertEol: false,
        }});

        var fitAddon = new FitAddon.FitAddon();
        term.loadAddon(fitAddon);
        term.open(container);
        try {{ fitAddon.fit(); }} catch(e) {{}}

        /* Re-fit when container is resized (e.g. by splitter drag) */
        if (typeof ResizeObserver !== 'undefined') {{
            var ro = new ResizeObserver(function() {{
                try {{ fitAddon.fit(); }} catch(e) {{}}
            }});
            ro.observe(container);
        }}

        /* Notify Python of terminal size changes */
        term.onResize(function(evt) {{
            inSeq++;
            var msg = '{XtermWidget._RESIZE_PREFIX}' + evt.cols + ':' + evt.rows;
            var encoded = btoa(msg);
            var inp = document.querySelector('.' + inClass + ' input');
            if (!inp) return;
            var setter = Object.getOwnPropertyDescriptor(
                HTMLInputElement.prototype, 'value'
            ).set;
            setter.call(inp, inSeq + ':' + encoded);
            inp.dispatchEvent(new Event('input', {{bubbles:true}}));
            inp.dispatchEvent(new Event('change', {{bubbles:true}}));
        }});

        /* ── User input → Python ── */
        term.onData(function(data) {{
            inputBuf += data;
            if (!inputTimer) {{
                inputTimer = setTimeout(sendInput, 20);
            }}
        }});

        /* ── Python output → terminal ── */
        function processOutput() {{
            var outEl = document.querySelector('.' + outClass);
            if (!outEl) return;
            var content = outEl.querySelector('.widget-html-content');
            if (!content) return;
            var span = content.querySelector('span[data-seq]');
            if (!span) return;
            var seq = parseInt(span.dataset.seq);
            if (seq <= lastOutSeq) return;
            lastOutSeq = seq;
            var d = span.dataset.d;
            try {{
                term.write(decodeURIComponent(escape(atob(d))));
            }} catch(e) {{
                try {{ term.write(atob(d)); }} catch(e2) {{}}
            }}
        }}

        /* MutationObserver for prompt response */
        var outEl = document.querySelector('.' + outClass);
        if (outEl) {{
            var content = outEl.querySelector('.widget-html-content');
            if (content) {{
                var obs = new MutationObserver(processOutput);
                obs.observe(content, {{
                    childList: true, subtree: true, characterData: true
                }});
            }}
        }}

        /* Fallback polling in case MutationObserver misses updates */
        setInterval(processOutput, 100);

        /* Focus the terminal */
        setTimeout(function() {{ term.focus(); }}, 200);

        /* Store reference for potential external access */
        container._term = term;
        container._fitAddon = fitAddon;
    }}

    /* Load xterm.js → fit addon → initialise */
    setTimeout(function() {{
        loadScript('{_XTERM_JS}', function() {{
            loadScript('{_XTERM_FIT}', function() {{
                setTimeout(init, 100);
            }});
        }});
    }}, 300);
}})();
</script>
"""
