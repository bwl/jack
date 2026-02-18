from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .agent import Agent, _tool_label
from .commit_queue import CommitQueue
from .config import Config
from .forest import ForestCLI
from .forest_api import ForestAPI
from .github import GitHubCLI
from .memory import ChatMemory
from .router import Router
from .tools import IdeaCLI, NovelCLI
from . import formatting

logger = logging.getLogger(__name__)


def _build_keyboard(buttons: list[tuple[str, str]]) -> InlineKeyboardMarkup | None:
    if not buttons:
        return None
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=data)] for label, data in buttons]
    )


class JackBot:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.memory = ChatMemory()

        if config.mode == "api":
            self.forest = ForestAPI(
                base_url=config.forest_url,
                api_key=config.forest_api_key,
            )
            self.ideas = None
            self.novels = None
        else:
            self.forest = ForestCLI(bin=config.forest_bin)
            self.ideas = IdeaCLI()
            self.novels = NovelCLI()

        # GitHub CLI (optional — needs gh installed and authed)
        self.github: GitHubCLI | None = None
        if config.github_repos:
            self.github = GitHubCLI()
            logger.info("GitHub tools enabled (repos=%s)", config.github_repos)

        # Commit queue (optional — needs GitHub + repos)
        self.commit_queue: CommitQueue | None = None
        if self.github and config.github_repos:
            from pathlib import Path
            full_repos = [
                r if "/" in r else f"{config.github_owner}/{r}"
                for r in config.github_repos
            ]
            self.commit_queue = CommitQueue(
                github=self.github,
                repos=full_repos,
                state_path=Path(config.commit_queue_path),
                poll_interval=config.commit_queue_interval,
            )
            logger.info(
                "Commit queue enabled (repos=%s, interval=%ds)",
                config.github_repos, config.commit_queue_interval,
            )

        # LLM agent (optional — needs API key)
        self.agent: Agent | None = None
        self._http_client: httpx.AsyncClient | None = None
        if config.openrouter_api_key:
            self._http_client = httpx.AsyncClient()
            self.agent = Agent(
                client=self._http_client,
                api_key=config.openrouter_api_key,
                model=config.openrouter_model,
                base_url=config.openrouter_base_url,
            )
            logger.info("Agent enabled (model=%s)", config.openrouter_model)

        self.router = Router(
            self.forest, self.ideas, self.novels,
            agent=self.agent, github=self.github,
            commit_queue=self.commit_queue,
        )

    def _is_authorized(self, update: Update) -> bool:
        user = update.effective_user
        return user is not None and user.id in self.config.allowed_users

    async def _search_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /search and /s — sends results with inline read buttons."""
        if not self._is_authorized(update):
            return

        assert update.message is not None
        await update.message.chat.send_action(ChatAction.TYPING)

        args = update.message.text.split(maxsplit=1)[1] if " " in update.message.text else ""
        if not args:
            await update.message.reply_text("Usage: /search <query>")
            return

        try:
            data = await self.forest.search(args)
            text = formatting.format_search(data)
            keyboard = _build_keyboard(formatting.search_buttons(data))
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except Exception as e:
            await update.message.reply_text(formatting.format_error(str(e)), parse_mode=ParseMode.HTML)

    async def _command_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._is_authorized(update):
            return

        assert update.message is not None
        await update.message.chat.send_action(ChatAction.TYPING)

        command = update.message.text.split()[0].lstrip("/").split("@")[0]
        args = update.message.text.split(maxsplit=1)[1] if " " in update.message.text else ""

        reply = await self.router.handle_command(command, args)
        await update.message.reply_text(reply, parse_mode=ParseMode.HTML)

    async def _text_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Free text → agent (if available) or search with inline buttons."""
        if not self._is_authorized(update):
            return

        assert update.message is not None and update.message.text is not None
        chat = update.message.chat
        chat_id = chat.id
        user_text = update.message.text

        # Record user message in memory
        self.memory.add(chat_id, "user", user_text)

        # Extract reply-to context for conversation threading
        reply_context: str | None = None
        reply_msg = update.message.reply_to_message
        if reply_msg is not None and reply_msg.text:
            reply_context = reply_msg.text

        if self.agent is not None:
            # Status message: edited in-place as tool calls happen
            status_msg = None

            async def _on_tool_call(step: int, name: str, args: dict) -> None:
                nonlocal status_msg
                label = _tool_label(name, args)
                text = f"Step {step}: {label}"
                if status_msg is None:
                    status_msg = await chat.send_message(text)
                else:
                    try:
                        await status_msg.edit_text(text)
                    except Exception:
                        pass  # Telegram may reject if text unchanged

            # Build context: conversation memory + reply-to
            memory_context = self.memory.format_for_prompt(chat_id)

            # Typing keepalive: re-send every 4s so Telegram doesn't drop the indicator
            typing_task = asyncio.create_task(self._typing_keepalive(chat))
            try:
                reply = await self.router.handle_text(
                    user_text,
                    on_tool_call=_on_tool_call,
                    reply_context=reply_context,
                    memory_context=memory_context,
                )
            finally:
                typing_task.cancel()

            # Record assistant response in memory
            self.memory.add(chat_id, "assistant", reply)

            # Clean up status message
            if status_msg is not None:
                try:
                    await status_msg.delete()
                except Exception:
                    pass

            try:
                await update.message.reply_text(reply, parse_mode=ParseMode.HTML)
            except Exception:
                # HTML parse failure (bad LLM output) — strip tags and retry as plain text
                logger.warning("HTML parse failed, stripping tags")
                plain = re.sub(r"<[^>]+>", "", reply)
                await update.message.reply_text(plain)
            return

        # No agent — plain search with inline buttons
        await chat.send_action(ChatAction.TYPING)
        try:
            data = await self.forest.search(user_text)
            text = formatting.format_search(data)
            keyboard = _build_keyboard(formatting.search_buttons(data))
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except Exception as e:
            await update.message.reply_text(formatting.format_error(str(e)), parse_mode=ParseMode.HTML)

    async def _forward_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Auto-capture forwarded messages as Forest notes."""
        if not self._is_authorized(update):
            return

        assert update.message is not None
        msg = update.message
        text = msg.text or msg.caption or ""
        if not text.strip():
            return

        await msg.chat.send_action(ChatAction.TYPING)

        # Build attribution from forward metadata
        origin = msg.forward_origin
        attribution = "Forwarded message"
        if origin is not None:
            origin_type = getattr(origin, "type", None)
            if origin_type == "user":
                sender = getattr(origin, "sender_user", None)
                if sender:
                    name = sender.full_name or sender.username or str(sender.id)
                    attribution = f"Forwarded from {name}"
            elif origin_type == "channel":
                chan = getattr(origin, "chat", None)
                if chan:
                    attribution = f"Forwarded from channel: {chan.title or chan.username}"
            elif origin_type == "hidden_user":
                sender_name = getattr(origin, "sender_user_name", "someone")
                attribution = f"Forwarded from {sender_name}"

        # Truncate for title
        title_text = text[:60].replace("\n", " ")
        if len(text) > 60:
            title_text += "..."

        try:
            data = await self.forest.capture(
                title=f"Fwd: {title_text}",
                body=f"{attribution}\n\n{text}",
                tags="topic:forwarded",
            )
            reply = formatting.format_capture(data)
        except Exception as e:
            reply = formatting.format_error(str(e))

        await msg.reply_text(reply, parse_mode=ParseMode.HTML)

    @staticmethod
    async def _typing_keepalive(chat: Any) -> None:
        """Send TYPING action every 4 seconds until cancelled."""
        try:
            while True:
                await chat.send_action(ChatAction.TYPING)
                await asyncio.sleep(4)
        except asyncio.CancelledError:
            pass

    async def _callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline button presses (e.g. read:abcd1234, edges:abcd1234)."""
        if not self._is_authorized(update):
            return

        query = update.callback_query
        assert query is not None
        await query.answer()

        data = query.data or ""
        if data.startswith("read:"):
            ref = data[5:]
            try:
                result = await self.forest.read(ref)
                text = formatting.format_read(result)
                # Add graph navigation buttons
                buttons = formatting.read_nav_buttons(result)
                keyboard = _build_keyboard(buttons)
            except Exception as e:
                text = formatting.format_error(str(e))
                keyboard = None
            await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

        elif data.startswith("edges:"):
            ref = data[6:]
            try:
                result = await self.forest.edges(ref=ref)
                text = formatting.format_edges(result, ref)
                buttons = formatting.edge_buttons(result)
                keyboard = _build_keyboard(buttons)
            except Exception as e:
                text = formatting.format_error(str(e))
                keyboard = None
            await query.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

    @staticmethod
    async def _poll_commits(context: ContextTypes.DEFAULT_TYPE) -> None:
        """Job callback: poll commit queue in the background."""
        queue: CommitQueue | None = context.bot_data.get("commit_queue")
        if queue is None:
            return
        try:
            await queue.poll()
            pending = len(queue.get_pending())
            if pending:
                logger.info("Commit queue: %d pending commits", pending)
        except Exception:
            logger.warning("Commit queue poll failed", exc_info=True)

    async def _shutdown(self, app: Application) -> None:
        """Clean up async resources on shutdown."""
        if self._http_client is not None:
            await self._http_client.aclose()
            logger.info("HTTP client closed")
        if isinstance(self.forest, ForestAPI):
            await self.forest.close()
            logger.info("Forest API client closed")

    def run(self) -> None:
        app = Application.builder().token(self.config.telegram_token).build()

        # Search gets its own handler for inline buttons
        for cmd in ("search", "s"):
            app.add_handler(CommandHandler(cmd, self._search_handler))

        # Forest commands (always available)
        forest_commands = ("read", "r", "capture", "c", "stats", "start", "help")

        # Portfolio/novel commands (only in CLI mode)
        tool_commands = (
            "ideas", "idea", "projects", "project", "portfolio",
            "novels", "novel",
        )

        all_commands = list(forest_commands)
        if self.config.mode == "cli":
            all_commands.extend(tool_commands)

        for cmd in all_commands:
            app.add_handler(CommandHandler(cmd, self._command_handler))

        app.add_handler(CallbackQueryHandler(self._callback_handler))

        # Forwarded messages get auto-captured (must be before general text handler)
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.FORWARDED,
            self._forward_handler,
        ))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._text_handler))

        # Register commit queue polling job
        if self.commit_queue is not None and app.job_queue is not None:
            app.bot_data["commit_queue"] = self.commit_queue
            app.job_queue.run_repeating(
                self._poll_commits,
                interval=self.commit_queue.poll_interval,
                first=10,  # first poll 10s after startup
            )
            logger.info("Commit queue polling registered (every %ds)", self.commit_queue.poll_interval)

        # Register shutdown callback for cleanup
        app.post_shutdown = self._shutdown

        mode_label = f"mode={self.config.mode}"
        logger.info(f"Jack bot starting ({mode_label}, long polling)...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
