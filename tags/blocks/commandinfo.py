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

from typing import ClassVar, Optional, Tuple

from redbot.core.bot import Red

from TagScriptEngine import Block, Context, RedCommandAdapter


class CommandInfoBlock(Block):
    """
    The commandinfo block returns information about a bot command as text.

    Unlike the :ref:`Command Block` (``{c}`` / ``{command}``), which *runs* a
    command, this block only *reads* a command's metadata. Pass the command name
    as the payload and the attribute as the parameter. Subcommands work too
    (e.g. ``set bot``). If the command does not exist, an error message is
    returned.

    The names ``c``, ``com`` and ``command`` are already used by the Command
    Block, so this block uses ``commandinfo``.

    **Usage:** ``{commandinfo([attribute]):<command>}``

    **Aliases:** ``None``

    **Payload:** command

    **Parameter:** attribute, None

    Attributes
    ----------
    name
        The command's name.
    qualified_name
        The command's full name, including any parent groups. This is also what
        the block returns when no attribute is passed.
    cog_name
        The name of the cog the command belongs to.
    description
        The command's description. Most commands don't set one, so this falls
        back to the first line of the help text when empty.
    short_doc
        The first line of the command's help text.
    help
        The command's full help text.
    aliases
        The command's aliases, or ``None`` if it has none.
    signature
        The command's argument signature. This is empty for commands that take
        no arguments (e.g. ``ping``).

    **Examples:** ::

        {commandinfo:userinfo}
        # userinfo

        {commandinfo(signature):ban}
        # <user> [reason]

        {commandinfo(description):userinfo}
        # Show information about a member.

        {commandinfo(help):warn}
        # Shows: Complete help docstring for the command.

        {commandinfo(cog_name):ping}
        # Core
    """

    ACCEPTED_NAMES: ClassVar[Tuple[str, ...]] = ("commandinfo",)

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot
        super().__init__()

    @classmethod
    def will_accept(cls, ctx: Context) -> bool:
        if not super().will_accept(ctx):
            return False
        # A command name (payload) is required - {commandinfo} alone is invalid.
        return bool(ctx.verb.payload)

    def process(self, ctx: Context) -> Optional[str]:
        name: str = (ctx.verb.payload or "").strip()
        if not name:
            return None
        command = self.bot.get_command(name)
        if command is None:
            return f"`Command Not Found: {name}`"
        adapter = RedCommandAdapter(command, signature=command.signature)
        return adapter.get_value(ctx.verb)
