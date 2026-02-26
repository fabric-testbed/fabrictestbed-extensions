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

"""Draggable splitter widgets for resizing adjacent panels.

Provides thin, styled drag handles that can be placed between ipywidgets
panels in HBox (horizontal) or VBox (vertical) containers. Dragging the
handle resizes the target panel while the flex sibling auto-fills.
"""

import uuid

import ipywidgets as widgets

from .styles import FABRIC_BG_TINT, FABRIC_PRIMARY, FABRIC_PRIMARY_LIGHT

# Shared JavaScript helpers (inlined into each splitter for isolation)
_JS_HELPERS = """
    function findFlexChild(n){
        var c=n;
        while(c&&c.parentElement){
            var d=getComputedStyle(c.parentElement).display;
            if(d==='flex'||d==='inline-flex')return c;
            c=c.parentElement;
        }
        return null;
    }
    function visSib(n,dir){
        var s=dir<0?n.previousElementSibling:n.nextElementSibling;
        while(s){
            if(getComputedStyle(s).display!=='none')return s;
            s=dir<0?s.previousElementSibling:s.nextElementSibling;
        }
        return null;
    }
"""


def create_h_splitter(resize_side: str = "prev") -> widgets.HTML:
    """Create a horizontal (column-resize) drag splitter.

    Parameters
    ----------
    resize_side : str
        Which adjacent panel to resize on drag: ``"prev"`` (left sibling)
        or ``"next"`` (right sibling). The opposite sibling should use
        ``flex: 1`` so it auto-fills the remaining space.
    """
    uid = f"fabvis-hs-{uuid.uuid4().hex[:8]}"
    sign = 1 if resize_side == "prev" else -1

    return widgets.HTML(
        value=f"""
<div id="{uid}" style="width:6px;height:100%;cursor:col-resize;
     background:{FABRIC_BG_TINT};border-radius:3px;
     transition:background 0.15s;"
     onmouseenter="this.style.background='{FABRIC_PRIMARY_LIGHT}'"
     onmouseleave="if(!this._dragging)this.style.background='{FABRIC_BG_TINT}'"
></div>
<script>
(function(){{
    setTimeout(function(){{
        var el=document.getElementById('{uid}');
        if(!el)return;
        {_JS_HELPERS}
        el.addEventListener('mousedown',function(e){{
            e.preventDefault();
            var w=findFlexChild(el);
            if(!w)return;
            var t=visSib(w,{sign});
            if(!t)return;
            var sx=e.clientX,tw=t.getBoundingClientRect().width;
            el._dragging=true;
            el.style.background='{FABRIC_PRIMARY}';
            function mv(e){{
                var dx=(e.clientX-sx)*{sign};
                var nw=Math.max(80,tw+dx);
                t.style.flex='0 0 '+nw+'px';
                t.style.width=nw+'px';
                t.style.minWidth='0px';
            }}
            function mu(){{
                el._dragging=false;
                el.style.background='{FABRIC_BG_TINT}';
                document.removeEventListener('mousemove',mv);
                document.removeEventListener('mouseup',mu);
            }}
            document.addEventListener('mousemove',mv);
            document.addEventListener('mouseup',mu);
        }});
    }},200);
}})();
</script>
""",
        layout=widgets.Layout(
            width="6px",
            min_width="6px",
            flex="0 0 6px",
            overflow="visible",
        ),
    )


def create_v_splitter(resize_side: str = "next") -> widgets.HTML:
    """Create a vertical (row-resize) drag splitter.

    Parameters
    ----------
    resize_side : str
        Which adjacent panel to resize on drag: ``"prev"`` (above) or
        ``"next"`` (below). The opposite sibling should use ``flex: 1``
        so it auto-fills.
    """
    uid = f"fabvis-vs-{uuid.uuid4().hex[:8]}"
    sign = 1 if resize_side == "prev" else -1

    return widgets.HTML(
        value=f"""
<div id="{uid}" style="height:6px;width:100%;cursor:row-resize;
     background:{FABRIC_BG_TINT};border-radius:3px;
     transition:background 0.15s;"
     onmouseenter="this.style.background='{FABRIC_PRIMARY_LIGHT}'"
     onmouseleave="if(!this._dragging)this.style.background='{FABRIC_BG_TINT}'"
></div>
<script>
(function(){{
    setTimeout(function(){{
        var el=document.getElementById('{uid}');
        if(!el)return;
        {_JS_HELPERS}
        el.addEventListener('mousedown',function(e){{
            e.preventDefault();
            var w=findFlexChild(el);
            if(!w)return;
            var t=visSib(w,{sign});
            if(!t)return;
            var sy=e.clientY,th=t.getBoundingClientRect().height;
            el._dragging=true;
            el.style.background='{FABRIC_PRIMARY}';
            function mv(e){{
                var dy=(e.clientY-sy)*{sign};
                var nh=Math.max(40,th+dy);
                t.style.flex='0 0 '+nh+'px';
                t.style.height=nh+'px';
            }}
            function mu(){{
                el._dragging=false;
                el.style.background='{FABRIC_BG_TINT}';
                document.removeEventListener('mousemove',mv);
                document.removeEventListener('mouseup',mu);
            }}
            document.addEventListener('mousemove',mv);
            document.addEventListener('mouseup',mu);
        }});
    }},200);
}})();
</script>
""",
        layout=widgets.Layout(
            height="6px",
            min_height="6px",
            flex="0 0 6px",
            overflow="visible",
        ),
    )
