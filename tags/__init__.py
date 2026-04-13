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

import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from redbot.core.bot import Red
from redbot.core.errors import CogLoadError

from .core import Tags
from .utils import validate_tagscriptengine

with open(Path(__file__).parent / "info.json") as fp:
    data = json.load(fp)

__red_end_user_data_statement__ = data["end_user_data_statement"]

try:
    tse_version = version("AdvancedTagScript")
except PackageNotFoundError:
    raise CogLoadError(
        "AdvancedTagScript is not installed. Please install it with: pip install AdvancedTagScript"
    )


conflicting_cogs = (
    ("Alias", "alias", "aliases"),
    ("CustomCommands", "customcom", "custom commands"),
)


async def setup(bot: Red) -> None:
    await validate_tagscriptengine(bot, tse_version)

    for cog_name, module_name, tag_name in conflicting_cogs:
        if bot.get_cog(cog_name):
            raise CogLoadError(
                f"This cog conflicts with {cog_name} and both cannot be loaded at the same time. "
                f"After unloading `{module_name}`, you can migrate {tag_name} to tags with `[p]migrate{module_name}`."
            )

    tags = Tags(bot)
    await bot.add_cog(tags)
