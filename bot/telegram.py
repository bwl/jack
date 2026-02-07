from __future__ import annotations

import asyncio
import logging

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

from .agent import Agent
from .config import Config
from .forest import ForestCLI
from .forest_api import ForestAPI
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

        # LLM agent (optional — needs API key)
        self.agent: Agent | None = None
        if config.openrouter_api_key:
            self._http_client = httpx.AsyncClient()
            self.agent = Agent(
                client=self._http_client,
                api_key=config.openrouter_api_key,
                model=config.openrouter_model,
                base_url=config.openrouter_base_url,
            )
            logger.info("Agent enabled (model=%s)", config.openrouter_model)

        self.router = Router(self.forest, self.ideas, self.novels, agent=self.agent)

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

        if self.agent is not None:
            # Typing keepalive: re-send every 4s so Telegram doesn't drop the indicator
            typing_task = asyncio.create_task(self._typing_keepalive(chat))
            try:
                reply = await self.router.handle_text(update.message.text)
            finally:
                typing_task.cancel()

            try:
                await update.message.reply_text(reply, parse_mode=ParseMode.HTML)
            except Exception:
                # HTML parse failure (bad LLM output) — retry without parse_mode
                logger.warning("HTML parse failed, retrying as plain text")
                await update.message.reply_text(reply)
            return

        # No agent — plain search with inline buttons
        await chat.send_action(ChatAction.TYPING)
        try:
            data = await self.forest.search(update.message.text)
            text = formatting.format_search(data)
            keyboard = _build_keyboard(formatting.search_buttons(data))
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
        except Exception as e:
            await update.message.reply_text(formatting.format_error(str(e)), parse_mode=ParseMode.HTML)

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
        """Handle inline button presses (e.g. read:abcd1234)."""
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
            except Exception as e:
                text = formatting.format_error(str(e))
            await query.message.reply_text(text, parse_mode=ParseMode.HTML)

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
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._text_handler))

        mode_label = f"mode={self.config.mode}"
        logger.info(f"Jack bot starting ({mode_label}, long polling)...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
