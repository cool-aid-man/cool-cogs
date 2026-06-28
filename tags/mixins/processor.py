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

import asyncio
import contextlib
import logging
import re
import time
from copy import copy
from typing import Any, Coroutine, Dict, List, Optional, Type, Union

import discord
import TagScriptEngine as tse
from redbot.core import commands
from redbot.core.utils.chat_formatting import text_to_file
from redbot.core.utils.menus import start_adding_reactions

from ..abc import MixinMeta
from ..blocks import (
    AllowedMentionsBlock,
    CommandInfoBlock,
    ComponentBlock,
    DeleteBlock,
    ReactBlock,
    ReplyBlock,
    SilentBlock,
)
from ..errors import BlacklistCheckFailure, RequireCheckFailure, WhitelistCheckFailure
from ..objects import ReplyContext, SilentContext, Tag

log = logging.getLogger("red.coolaid.tags.processor")


class Processor(MixinMeta):
    # Matches {author(roleids)} / {author.roleids} and the user/target/member aliases
    ROLEIDS_RE = re.compile(
        r"\{(?:author|user|target|member)\s*[.(]\s*roleids", re.IGNORECASE
    )

    # A bare Discord user id (snowflake) appearing in a tag's arguments.
    TARGET_ID_RE = re.compile(r"\b(\d{17,20})\b")

    # Matches {author(banner)} / {author.banner} and the user/target/member aliases
    BANNER_RE = re.compile(
        r"\{(?:author|user|target|member)\s*[.(]\s*banner", re.IGNORECASE
    )

    # How long a fetched banner url is reused before another fetch is allowed.
    BANNER_CACHE_TTL: int = 1800  # 30 minutes

    def __init__(self) -> None:
        self.role_converter: commands.RoleConverter = commands.RoleConverter()
        self.channel_converter: commands.TextChannelConverter = commands.TextChannelConverter()
        self.member_converter: commands.MemberConverter = commands.MemberConverter()
        self.emoji_converter: commands.EmojiConverter = commands.EmojiConverter()

        # A banner is fetched at most once per TTL window per user.
        self._banner_cache: Dict[int, tuple] = {}
        # Per-invoker throttle on banner *fetches* (cache misses only). And reading Cache is FREE
        self._banner_cooldown: commands.CooldownMapping = commands.CooldownMapping.from_cooldown(
            1, 10.0, commands.BucketType.user
        )

        self.bot.add_dev_env_value("tse", lambda ctx: tse)
        super().__init__()

    async def cog_unload(self) -> None:
        self.bot.remove_dev_env_value("tse")
        await super().cog_unload()

    async def initialize_interpreter(self, data: Optional[Dict[str, Any]] = None) -> None:
        if not data:
            data = await self.config.all()
        self.dot_parameter = data["dot_parameter"]

        tse_blocks: List[tse.Block] = [
            tse.MathBlock(),
            tse.RandomBlock(),
            tse.RangeBlock(),
            tse.AnyBlock(),
            tse.IfBlock(),
            tse.AllBlock(),
            tse.BreakBlock(),
            tse.StrfBlock(),
            tse.StopBlock(),
            tse.AssignmentBlock(),
            tse.FiftyFiftyBlock(),
            tse.ShortCutRedirectBlock("args"),
            tse.LooseVariableGetterBlock(),
            tse.StrictVariableGetterBlock(),
            tse.SubstringBlock(),
            tse.EmbedBlock(),
            tse.ReplaceBlock(),
            tse.PythonBlock(),
            tse.URLEncodeBlock(),
            tse.RequireBlock(),
            tse.BlacklistBlock(),
            tse.CommandBlock(),
            tse.OverrideBlock(),
            tse.RedirectBlock(),
            tse.CooldownBlock(),
            tse.UpperBlock(),
            tse.LowerBlock(),
            tse.CountBlock(),
            tse.LengthBlock(),
            tse.JoinBlock(),
            tse.ListBlock(),
            tse.CycleBlock(),
            tse.OrdinalBlock(),
        ]
        tag_blocks: List[tse.Block] = [
            AllowedMentionsBlock(),
            CommandInfoBlock(self.bot),
            ComponentBlock(),
            DeleteBlock(),
            SilentBlock(),
            ReplyBlock(),
            ReactBlock(),
        ]
        interpreter: Union[Type[tse.AsyncInterpreter], Type[tse.Interpreter]] = (
            tse.AsyncInterpreter if data["async_enabled"] else tse.Interpreter
        )
        self.async_enabled = data["async_enabled"]
        self.engine: Union[tse.AsyncInterpreter, tse.Interpreter] = interpreter(
            tse_blocks + tag_blocks
        )
        for block in await self.compile_blocks(data):
            self.engine.blocks.append(block())

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError, unhandled_by_cog: bool = False
    ):
        if not isinstance(error, commands.CommandNotFound):
            return
        message: discord.Message = ctx.message
        tag = self.get_tag(ctx.guild, ctx.invoked_with, check_global=True)
        if tag and await self.message_eligible_as_tag(message):
            prefix = ctx.prefix
            tag_command = message.content[len(prefix) :]
            await self.invoke_tag_message(message, prefix, tag_command)

    async def message_eligible_as_tag(self, message: discord.Message) -> bool:
        if message.guild:
            return isinstance(
                message.author, discord.Member
            ) and await self.bot.message_eligible_as_command(message)
        else:
            return await self.bot.allowed_by_whitelist_blacklist(message.author)

    async def invoke_tag_message(
        self, message: discord.Message, prefix: str, tag_command: str
    ) -> None:
        new_message = copy(message)
        new_message.content = f"{prefix}invoketag False {tag_command}"
        ctx = await self.bot.get_context(new_message)
        await self.bot.invoke(ctx)

    @classmethod
    def _resolve_target_member(
        cls, ctx: commands.Context, args: str
    ) -> Optional[discord.Member]:
        # Only the first match is used, the rest are ignored.
        # An @mention always wins; failing that, the first raw user id
        # in the arguments is resolved - but only if that id is a member of this guild
        if ctx.message.mentions:
            first = ctx.message.mentions[0]
            return first if isinstance(first, discord.Member) else None
        if ctx.guild and args:
            match = cls.TARGET_ID_RE.search(args)
            if match:
                return ctx.guild.get_member(int(match.group(1)))
        return None

    @classmethod
    def get_seed_from_context(
        cls, ctx: commands.Context, args: str = ""
    ) -> Dict[str, tse.Adapter]:
        author = tse.MemberAdapter(ctx.author)
        member = cls._resolve_target_member(ctx, args)
        target = tse.MemberAdapter(member) if member is not None else author
        channel = tse.ChannelAdapter(ctx.channel)
        bot = tse.RedBotAdapter(
            ctx.bot, owner=ctx.author.id in (ctx.bot.owner_ids or set())
        )
        seed = {
            "author": author,
            "user": author,
            "target": target,
            "member": target,
            "channel": channel,
            "bot": bot,
        }
        if ctx.guild:
            guild = tse.GuildAdapter(ctx.guild)
            seed.update(guild=guild, server=guild)
        return seed

    async def _inject_banners(
        self, ctx: commands.Context, seed: Dict[str, tse.Adapter]
    ) -> None:
        # The banner is empty by default; we only override it when a fetch succeeds.
        for key in ("author", "target"):
            adapter = seed.get(key)
            member = getattr(adapter, "object", None)
            if member is None:
                continue
            url = await self._resolve_banner(ctx, member.id)
            if url is not None:
                adapter._attributes["banner"] = url

    async def _resolve_banner(self, ctx: commands.Context, user_id: int) -> Optional[str]:
        # A fresh cache hit is free - it never touches
        # the cooldown or the API. Only a miss/expiry attempts a fetch, and that
        # fetch is gated by a per-invoker cooldown; if the caller is on cooldown
        # the last-known (stale) url is served instead, or None if there is none.
        now = time.monotonic()
        cached = self._banner_cache.get(user_id)
        if cached is not None and now - cached[0] < self.BANNER_CACHE_TTL:
            return cached[1]
        bucket = self._banner_cooldown.get_bucket(ctx.message)
        if bucket is not None and bucket.update_rate_limit():
            return cached[1] if cached is not None else None
        try:
            user = await self.bot.fetch_user(user_id)
        except discord.HTTPException:
            return cached[1] if cached is not None else None
        url = user.banner.url if user.banner else ""
        self._banner_cache[user_id] = (now, url)
        return url

    async def process_tag(
        self,
        ctx: commands.Context,
        tag: Tag,
        *,
        seed_variables: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Optional[str]:
        seed_variables = {} if seed_variables is None else seed_variables
        # If the tag was invoked with arguments, let {target} fall back to the
        # first raw user id in them (guild members only) when no @mention exists.
        args_adapter = seed_variables.get("args")
        args_text = args_adapter.string if isinstance(args_adapter, tse.StringAdapter) else ""
        seed = self.get_seed_from_context(ctx, args_text)
        if self.BANNER_RE.search(tag.tagscript):
            await self._inject_banners(ctx, seed)
        seed_variables.update(seed)

        output = await tag.run(seed_variables, **kwargs)
        await tag.update_config()
        dispatch_prefix = "tag" if tag.guild_id else "g-tag"
        self.bot.dispatch("commandstats_action_v2", f"{dispatch_prefix}:{tag}", ctx.guild)
        to_gather = []
        command_messages = []
        content = output.body if output.body else None
        # Output longer than Discord's limit is normally truncated. The ONly
        # exception is {author(roleids)} (and its user/target/member aliases):
        # the full list is sent as a .txt attachment instead of being cut off.
        # Everything else keeps the original truncation behaviour.
        send_as_file = False
        if content and len(content) > 2000:
            if self.ROLEIDS_RE.search(tag.tagscript):
                send_as_file = True
            else:
                content = content[:2000]
        actions = output.actions

        if actions:
            try:
                await self.validate_checks(ctx, actions)
            except RequireCheckFailure as error:
                response = error.response
                if response is None:
                    start_adding_reactions(ctx.message, ["❌"])
                elif response.strip():
                    await ctx.send(response[:2000])
                return
            if delete := actions.get("delete", False):
                to_gather.append(self.delete_quietly(ctx))

            if delete is False and (reactu := actions.get("reactu")):
                to_gather.append(self.react_to_list(ctx, ctx.message, reactu))

            if actions.get("commands"):
                for command in actions["commands"]:
                    if command.split()[0] == "invoketag":
                        await ctx.send("Tag looping isn't allowed.")
                        return
                    new = copy(ctx.message)
                    new.content = ctx.prefix + command
                    command_messages.append(new)

        # this is going to become an asynchronous swamp
        msg = await self.send_tag_response(ctx, actions, content, as_file=send_as_file)
        if msg and (react := actions.get("react")):
            to_gather.append(self.react_to_list(ctx, msg, react))
        if command_messages:
            silent = actions.get("silent", False)
            reply = actions.get("reply", False)
            overrides = actions.get("overrides", {})
            to_gather.append(self.process_commands(command_messages, silent, reply, overrides))

        if to_gather:
            await asyncio.gather(*to_gather)

    @staticmethod
    async def send_quietly(
        destination: discord.abc.Messageable, content: Optional[str] = None, **kwargs: Any
    ) -> Optional[discord.Message]:
        with contextlib.suppress(discord.HTTPException):
            return await destination.send(content, **kwargs)

    async def send_tag_response(
        self,
        ctx: commands.Context,
        actions: Dict[str, Any],
        content: Optional[str] = None,
        *,
        as_file: bool = False,
        **kwargs: Any,
    ) -> Optional[discord.Message]:
        destination = ctx.channel
        embed = actions.get("embed")
        components_v2 = actions.get("components_v2")
        replying = False

        if reply := actions.get("reply"):
            if reply:
                replying = True

        if target := actions.get("target"):
            if target == "dm":
                destination = ctx.author
            elif target == "reply":
                replying = True
            else:
                try:
                    chan = await self.channel_converter.convert(ctx, target)
                except commands.BadArgument:
                    pass
                else:
                    if chan.permissions_for(ctx.me).send_messages:
                        destination = chan

        if not (content or embed is not None or components_v2):
            return

        if components_v2:
            # A Components V2 message cannot carry content or embeds, so 
            # plain text is folded as 1st block & anything else is dropped
            leading = content
            if as_file and content:
                # {author(roleids)} overflow: keep it as a .txt attachment
                # rather than folding a huge id list into the layout.
                kwargs.setdefault("files", []).append(
                    text_to_file(content, filename="roleids.txt")
                )
                leading = None
            kwargs["view"] = self.build_components_v2_view(components_v2, leading)
            content = None
        else:
            kwargs["embed"] = embed

        if allowed_mentions := actions.get("allowed_mentions"):
            if isinstance(ctx.author, discord.Member):
                if (
                    self.bot.is_owner(ctx.author)
                    or ctx.author.guild_permissions.manage_guild
                    or allowed_mentions.get("override", False)
                ):
                    mentions = allowed_mentions.get("mentions", True)
                    if isinstance(mentions, list):
                        roles: List[discord.Role] = await self._get_roles(ctx, mentions)
                        if roles:
                            kwargs["allowed_mentions"] = discord.AllowedMentions(roles=roles)
                    else:
                        kwargs["allowed_mentions"] = discord.AllowedMentions(roles=mentions)

        if replying:
            ref = ctx.message.to_reference(fail_if_not_exists=False)
            kwargs["reference"] = ref

        # Only set for {author(roleids)} overflow: send the full list as a .txt
        # attachment instead of truncating it. Any embed/reply still applies.
        if content and as_file:
            kwargs.setdefault("files", []).append(
                text_to_file(content, filename="roleids.txt")
            )
            content = None

        return await self.send_quietly(destination, content, **kwargs)

    @staticmethod
    def build_components_v2_view(
        layout: Dict[str, Any], leading_content: Optional[str] = None
    ) -> discord.ui.LayoutView:
        items: List[Dict[str, Any]] = []
        if leading_content:
            # The folded-in plain output counts toward the 4000-char V2 text
            # cap, so trim it to whatever budget the layout's text leaves.
            used = sum(
                len(i["content"])
                for i in layout["items"]
                if i["type"] in ("text", "section")
            )
            remaining = 4000 - used
            if remaining <= 0:
                leading_content = None
            elif len(leading_content) > remaining:
                leading_content = leading_content[: max(0, remaining - 1)] + "…"
            if leading_content:
                items.append({"type": "text", "content": leading_content})
        items.extend(layout["items"])

        children: List[discord.ui.Item] = []
        for item in items:
            kind = item["type"]
            if kind == "text":
                children.append(discord.ui.TextDisplay(item["content"]))
            elif kind == "section":
                text = item.get("content") or "​"
                children.append(
                    discord.ui.Section(
                        text, accessory=discord.ui.Thumbnail(item["thumbnail"])
                    )
                )
            elif kind == "separator":
                spacing = (
                    discord.SeparatorSpacing.large
                    if item["large"]
                    else discord.SeparatorSpacing.small
                )
                children.append(
                    discord.ui.Separator(visible=item["visible"], spacing=spacing)
                )
            elif kind == "gallery":
                children.append(
                    discord.ui.MediaGallery(
                        *[discord.MediaGalleryItem(url) for url in item["urls"]]
                    )
                )

        if not children:
            children.append(discord.ui.TextDisplay("​"))

        view = discord.ui.LayoutView(timeout=None)
        accent = layout.get("accent_color")
        if layout.get("framed") or accent is not None:
            view.add_item(discord.ui.Container(*children, accent_colour=accent))
        else:
            for child in children:
                view.add_item(child)
        return view

    async def process_commands(
        self, messages: List[discord.Message], silent: bool, reply: bool, overrides: Dict[Any, Any]
    ) -> None:
        command_tasks: List[asyncio.Task[None]] = []
        for message in messages:
            command_task: asyncio.Task[None] = asyncio.create_task(
                self.process_command(message, silent, reply, overrides)
            )
            command_tasks.append(command_task)
            await asyncio.sleep(0.1)
        await asyncio.gather(*command_tasks)

    async def process_command(
        self,
        command_message: discord.Message,
        silent: bool,
        reply: bool,
        overrides: Dict[Any, Any],
    ) -> None:
        command_cls = SilentContext if silent else (ReplyContext if reply else commands.Context)
        ctx: Union[SilentContext, ReplyContext, commands.Context] = await self.bot.get_context(
            command_message, cls=command_cls
        )
        if not ctx.valid:
            return
        if overrides:
            ctx.command = self.handle_overrides(ctx.command, overrides)
        await self.bot.invoke(ctx)

    @classmethod
    def handle_overrides(
        cls, command: commands.Command, overrides: Dict[str, Any]
    ) -> commands.Command:
        overriden_command = copy(command)
        # overriden_command = command.copy() # does not work as it makes ctx a regular argument
        # overriden_command.cog = command.cog
        requires: commands.Requires = copy(command.requires)
        priv_level = requires.privilege_level
        if priv_level not in (
            commands.PrivilegeLevel.NONE,
            commands.PrivilegeLevel.BOT_OWNER,
            commands.PrivilegeLevel.GUILD_OWNER,
        ):
            if overrides["admin"] and priv_level is commands.PrivilegeLevel.ADMIN:
                requires.privilege_level = commands.PrivilegeLevel.NONE
            elif overrides["mod"] and priv_level is commands.PrivilegeLevel.MOD:
                requires.privilege_level = commands.PrivilegeLevel.NONE

        if overrides["permissions"] and requires.user_perms:
            requires.user_perms = discord.Permissions.none()
        overriden_command.requires = requires

        if all_commands := getattr(overriden_command, "all_commands", None):
            all_commands = all_commands.copy()
            for name, child in all_commands.copy().items():
                all_commands[name] = cls.handle_overrides(child, overrides)
            overriden_command.all_commands = all_commands
        return overriden_command

    async def _get_roles(self, ctx: commands.Context, mentions: List[str]) -> List[discord.Role]:
        tasks: List[Coroutine[Any, Any, Optional[discord.Role]]] = [
            await asyncio.to_thread(self._convert_roles_silently, ctx, argument)
            for argument in mentions
        ]
        converted: List[Optional[discord.Role]] = await asyncio.gather(*tasks)
        return [role for role in converted if role is not None]

    async def _convert_roles_silently(
        self, ctx: commands.Context, argument: str
    ) -> Optional[discord.Role]:
        with contextlib.suppress(commands.RoleNotFound):
            return await self.role_converter.convert(ctx, argument.strip("@"))
        return None

    async def validate_checks(self, ctx: commands.Context, actions: Dict[str, Any]) -> None:
        to_gather = []
        if requires := actions.get("requires"):
            to_gather.append(self.validate_requires(ctx, requires))
        if blacklist := actions.get("blacklist"):
            to_gather.append(self.validate_blacklist(ctx, blacklist))
        if to_gather:
            await asyncio.gather(*to_gather)

    async def validate_requires(self, ctx: commands.Context, requires: Dict[str, Any]) -> None:
        for argument in requires["items"]:
            role_or_channel = await self.role_or_channel_convert(ctx, argument)
            if not role_or_channel:
                continue
            if (
                isinstance(role_or_channel, discord.Role)
                and role_or_channel in ctx.author.roles
                or not isinstance(role_or_channel, discord.Role)
                and role_or_channel == ctx.channel
            ):
                return
        raise WhitelistCheckFailure(requires["response"])

    async def validate_blacklist(self, ctx: commands.Context, blacklist: Dict[str, Any]) -> None:
        for argument in blacklist["items"]:
            role_or_channel = await self.role_or_channel_convert(ctx, argument)
            if not role_or_channel:
                continue
            if (
                isinstance(role_or_channel, discord.Role)
                and role_or_channel in ctx.author.roles
                or not isinstance(role_or_channel, discord.Role)
                and role_or_channel == ctx.channel
            ):
                raise BlacklistCheckFailure(blacklist["response"])

    async def role_or_channel_convert(
        self, ctx: commands.Context, argument: str
    ) -> Optional[Union[discord.Role, discord.TextChannel]]:
        objects = await asyncio.gather(
            self.role_converter.convert(ctx, argument),
            self.channel_converter.convert(ctx, argument),
            return_exceptions=True,
        )
        objects = [obj for obj in objects if isinstance(obj, (discord.Role, discord.TextChannel))]
        return objects[0] if objects else None

    async def react_to_list(
        self, ctx: commands.Context, message: discord.Message, args: List[str]
    ) -> None:
        if not (message and args):
            return
        for arg in args:
            try:
                arg = await self.emoji_converter.convert(ctx, arg)
            except commands.BadArgument:
                pass
            try:
                await message.add_reaction(arg)
            except discord.HTTPException:
                pass

    @staticmethod
    async def delete_quietly(ctx: commands.Context) -> None:
        if ctx.channel.permissions_for(ctx.me).manage_messages:
            try:
                await ctx.message.delete()
            except discord.HTTPException:
                pass
