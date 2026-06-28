"""
MIT License

Copyright (c) 2020-2023 PhenoM4n4n
Copyright (c) 2023-2026 japandotorg
Copyright (c) 2026-present cool-aid-man

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from typing import Any, ClassVar, Dict, List, Optional, Tuple

from TagScriptEngine import Block, Context, helper_split

# Discord components v2 text limit
TEXT_LIMIT: int = 4000

# Discord allows in total 40 total components per message (nested components
# count toward this).
MAX_COMPONENTS: int = 40

# A single media gallery holds at most 10 items
MAX_MEDIA_ITEMS: int = 10

# Separator spacing keywords -> (visible, large)
SEPARATOR_KEYWORDS: Dict[str, Tuple[bool, bool]] = {
    "": (True, False),
    "small": (True, False),
    "large": (True, True),
    "big": (True, True),
    "hidden": (False, False),
    "invisible": (False, False),
    "blank": (False, False),
}


class ComponentBlock(Block):
    """
    The component block builds a `Components V2 <https://discord.com/developers/docs/components/reference>`_
    message in the tag response. It is the text-only counterpart of the embed
    block: it accepts manual attributes that are accumulated, in order, into a
    single layout.

    .. important::
        - A Components V2 message **cannot** be combined with a normal embed
          (``{embed}``). If both are used, the component layout wins and the
          embed is dropped.
        - Any plain text output from the tag is folded in as the first text
          block of the layout so it is never lost.
        - The combined text across all blocks must not exceed 4000 characters.

    By default the text blocks render plainly. Wrapping them in a **container**
    gives the framed, embed-like look. The frame can be enabled with or without
    a colour:

    *   ``container`` (aliases ``box``, ``frame``) - wraps the whole layout in a
        framed container. The payload optionally accepts a colour, e.g.
        ``{component(container):#5865F2}``, to add an embed-like accent bar.
    *   ``color`` / ``colour`` - sets the accent bar colour and implies the
        container frame.

    The following attributes can be set manually:

    *   ``text`` - a markdown text block (repeatable). Standard Discord markdown
        works, including ``#`` / ``##`` / ``###`` headings and ``-#`` small text.
    *   ``separator`` - inserts a divider (``small`` is the default). The payload
        optionally accepts ``large`` / ``big`` (more spacing) or ``hidden`` /
        ``invisible`` / ``blank`` (spacing only, no line).
    *   ``thumbnail`` - attaches a thumbnail image to the most recent text
        block, turning it into a section.
    *   ``image`` - adds one or more images to a media gallery. Multiple URLs
        can be passed at once, separated by ``;;``, ``|`` or ``~`` (up to 10
        total). Repeatable.

    Blocks are processed in **order**, so the order of the attribute blocks is
    the order they appear in the message.

    **Usage:** ``{component(<attribute>):<value>}``

    **Aliases:** ``cv2``, ``c2``

    **Payload:** value

    **Parameter:** attribute

    **Examples:**

    .. code-block:: yaml

        Framed with an accent bar:
        {component(color):#5865F2}
        {component(text):# Server Rules}
        {component(text):Please read these **carefully**.}
        {component(separator)}
        {component(text):1. Be respectful.}
        {component(text):-# Last updated today.}

        Framed with no colour:
        {component(container)}
        {component(text):This shows up boxed, like an embed without the bar.}

        Plain text, no frame:
        {component(text):Every obstacle carries an unseen aid for those willing to endure.}

        Framed without an accent bar:
        {component(box)}
        {component(text):## Quote of the Day}
        {component(separator)}
        {component(text):Remember {author(mention)}!
        - Every obstacle carries an unseen aid for those willing to endure.}

    """

    ACCEPTED_NAMES: ClassVar[Tuple[str, ...]] = ("component", "cv2", "c2")

    ATTRIBUTES: ClassVar[Tuple[str, ...]] = (
        "text",
        "container",
        "box",
        "frame",
        "color",
        "colour",
        "separator",
        "thumbnail",
        "image",
    )

    @classmethod
    def will_accept(cls, ctx: Context) -> bool:
        if not super().will_accept(ctx):
            return False
        return (ctx.verb.parameter or "").lower() in cls.ATTRIBUTES

    @staticmethod
    def _get_layout(ctx: Context) -> Dict[str, Any]:
        layout: Optional[Dict[str, Any]] = ctx.response.actions.get("components_v2")
        if layout is None:
            layout = {"framed": False, "accent_color": None, "items": []}
            ctx.response.actions["components_v2"] = layout
        return layout

    @staticmethod
    def _total_text(layout: Dict[str, Any]) -> int:
        total = 0
        for item in layout["items"]:
            if item["type"] in ("text", "section"):
                total += len(item["content"])
        return total

    @staticmethod
    def _component_count(layout: Dict[str, Any]) -> int:
        count = 1 if layout["framed"] else 0  # the wrapping container
        for item in layout["items"]:
            kind = item["type"]
            if kind == "section":
                count += 2  # section + its thumbnail accessory
            elif kind == "gallery":
                count += 1 + len(item["urls"])  # gallery + each media item
            else:
                count += 1  # text or separator
        return count

    def _at_component_limit(self, layout: Dict[str, Any], adding: int = 1) -> bool:
        # Reserve one slot (Always) for the plain-output text block folded in at send.
        return self._component_count(layout) + adding > MAX_COMPONENTS - 1

    def process(self, ctx: Context) -> Optional[str]:
        attribute = (ctx.verb.parameter or "").lower()
        payload = ctx.verb.payload
        layout = self._get_layout(ctx)

        if attribute == "text":
            if payload is None:
                return None
            if self._total_text(layout) + len(payload) > TEXT_LIMIT:
                return f"`MAX COMPONENT TEXT LENGTH REACHED ({TEXT_LIMIT})`"
            if self._at_component_limit(layout):
                return f"`MAX COMPONENT COUNT REACHED ({MAX_COMPONENTS})`"
            layout["items"].append({"type": "text", "content": payload})
            return ""

        if attribute in ("container", "box", "frame"):
            layout["framed"] = True
            if payload:
                color = self._parse_color(payload)
                if color is None:
                    return f"Component Parse Error: invalid colour `{payload}`"
                layout["accent_color"] = color
            return ""

        if attribute in ("color", "colour"):
            if not payload:
                return None
            color = self._parse_color(payload)
            if color is None:
                return f"Component Parse Error: invalid colour `{payload}`"
            # A colour can only be shown via a container, so it implies framing.
            layout["framed"] = True
            layout["accent_color"] = color
            return ""

        if attribute == "separator":
            if self._at_component_limit(layout):
                return f"`MAX COMPONENT COUNT REACHED ({MAX_COMPONENTS})`"
            keyword = (payload or "").strip().lower()
            visible, large = SEPARATOR_KEYWORDS.get(keyword, (True, False))
            layout["items"].append(
                {"type": "separator", "visible": visible, "large": large}
            )
            return ""

        if attribute == "thumbnail":
            if not payload:
                return None
            # Attach to the most recent text block, converting it to a section.
            for item in reversed(layout["items"]):
                if item["type"] == "text":
                    item["type"] = "section"
                    item["thumbnail"] = payload
                    break
            else:
                # A fresh section costs two components (section + thumbnail).
                if self._at_component_limit(layout, adding=2):
                    return f"`MAX COMPONENT COUNT REACHED ({MAX_COMPONENTS})`"
                layout["items"].append(
                    {"type": "section", "content": "", "thumbnail": payload}
                )
            return ""

        if attribute == "image":
            if not payload:
                return None
            # Delimiters: ;; takes priority (same as embed fields); when ;; is
            # present, | and ~ are not used. Otherwise split on | or ~. Basically same as ``embed``
            split = helper_split(payload, double_semicolon=True)
            raw = split if split is not None else [payload]
            urls = [url.strip() for url in raw if url.strip()]
            if not urls:
                return None
            # Only coalesce into the previous gallery when it is the most recent
            # item, so images keep document order relative to other blocks.
            items = layout["items"]
            if items and items[-1]["type"] == "gallery":
                gallery = items[-1]
            else:
                if self._at_component_limit(layout):
                    return f"`MAX COMPONENT COUNT REACHED ({MAX_COMPONENTS})`"
                gallery = {"type": "gallery", "urls": []}
                items.append(gallery)
            for url in urls:
                if len(gallery["urls"]) >= MAX_MEDIA_ITEMS:
                    break
                if self._at_component_limit(layout):
                    break
                gallery["urls"].append(url)
            return ""

        return None

    @staticmethod
    def _parse_color(argument: str) -> Optional[int]:
        arg = argument.strip().replace("0x", "").lstrip("#").lower()
        try:
            value = int(arg, base=16)
        except ValueError:
            return None
        if not (0 <= value <= 0xFFFFFF):
            return None
        return value
