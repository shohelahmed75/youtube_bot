"""
bot.py — Stryker Bot core loop orchestrator.

Ties together all modules (chat, commands, welcome, polls)
into a continuous message processing loop with:
  - Auto-detection of live broadcasts
  - Stream owner detection
  - History seeding for the welcome tracker
  - Graceful error handling and shutdown
"""

import time
import logging

from stryker.core.chat import (
    get_active_broadcast,
    get_live_chat_id,
    get_stream_owner_channel,
    send_message,
)
from stryker.core.chat_reader import LiveChatReader
from stryker.features.commands import CommandRouter
from stryker.features.welcome import WelcomeTracker
from stryker.features.polls import parse_poll_command, create_poll
from stryker.core.config import BOT_PREFIX, VIDEO_ID, CHANNEL_ID

logger = logging.getLogger("stryker")


class StrykerBot:
    """
    Main bot class that orchestrates the live chat monitoring loop.
    """

    def __init__(self, youtube, video_id=None):
        """
        Args:
            youtube: Authenticated YouTube API service object.
            video_id: The YouTube video ID of the live stream.
                      If empty/None, the bot will auto-detect.
        """
        self.youtube = youtube
        self.video_id = video_id or VIDEO_ID or None
        self.stream_title = None
        self.chat_id = None
        self.running = False

        # Sub-systems (initialized after we have a chat_id)
        self.command_router = CommandRouter()
        self.welcome_tracker = None  # Created after chat_id is known
        self._chat_reader = None     # Quota-free chat reader

        # Track if this is the first fetch (for history seeding)
        self._initial_fetch = True

    def start(self):
        """
        Start the bot's main loop.

        Flow:
          1. Auto-detect or validate the live stream
          2. Get the live chat ID
          3. Detect bot channel + stream owner
          4. Initialize welcome tracker (loads persisted data)
          5. Seed welcome tracker from chat history
          6. Start polling loop
        """
        # ── Step 1: Resolve video ID ─────────────────────────────────────
        if not self.video_id:
            logger.info("🔍 No video_id set, auto-detecting active broadcast...")
            try:
                channel_id = CHANNEL_ID or None
                self.video_id, self.stream_title = get_active_broadcast(
                    self.youtube, channel_id=channel_id
                )
            except ValueError as e:
                logger.error(f"❌ {e}")
                return
        else:
            logger.info(f"🔍 Using configured video: {self.video_id}")

        # ── Step 2: Get the live chat ID ─────────────────────────────────
        self.chat_id = get_live_chat_id(self.youtube, self.video_id)

        # ── Step 3: Detect bot channel + stream owner ────────────────────
        bot_channel_id = self._detect_bot_channel()
        owner_channel_id = get_stream_owner_channel(self.youtube, self.video_id)

        # ── Step 4: Initialize welcome tracker (with persistence) ────────
        self.welcome_tracker = WelcomeTracker(chat_id=self.chat_id)
        if bot_channel_id:
            self.welcome_tracker.set_bot_channel_id(bot_channel_id)
        if owner_channel_id:
            self.welcome_tracker.set_owner_channel_id(owner_channel_id)

        # ── Step 5: Connect the quota-free chat reader ────────────────────
        self._chat_reader = LiveChatReader(self.video_id)
        try:
            self._chat_reader.connect()
        except ConnectionError as e:
            logger.error(f"❌ {e}")
            return

        # ── Step 6: Start the polling loop ───────────────────────────────
        self.running = True
        logger.info("🚀 Stryker Bot is now live! Monitoring chat...")
        logger.info(f"   Commands: {self.command_router.trigger_count} triggers")
        logger.info(f"   Prefix: '{BOT_PREFIX}'")
        logger.info(f"   Tracked viewers: {self.welcome_tracker.welcomed_count}")
        logger.info("   ⚡ Quota-free chat reading enabled")
        logger.info("   Press Ctrl+C to stop.\n")

        self._poll_loop()

    def _poll_loop(self):
        """
        Main polling loop. Reads messages via the quota-free
        internal API, processes them, then waits for the
        recommended polling interval.
        """
        while self.running:
            try:
                messages, interval = self._chat_reader.poll()

                if self._initial_fetch:
                    # Seed welcome tracker from historical messages
                    # so we don't re-welcome people who already chatted
                    self.welcome_tracker.seed_from_history(messages)
                    self._initial_fetch = False
                else:
                    for msg in messages:
                        self._process_message(msg)

                # Wait for the recommended polling interval
                time.sleep(interval)

            except KeyboardInterrupt:
                self.stop()
                break
            except Exception as e:
                logger.error(f"❌ Unexpected error in poll loop: {e}")
                logger.info("   Retrying in 10 seconds...")
                time.sleep(10)

    def _process_message(self, msg):
        """
        Process a single chat message through the pipeline:
          1. Welcome new viewers
          2. Match slash commands (with cooldown)
          3. Handle poll commands
          4. Handle reload command

        Args:
            msg: Normalized message dict from chat.fetch_messages().
        """
        channel_id = msg["channel_id"]
        display_name = msg["display_name"]
        text = msg["message"]
        is_owner = msg["is_owner"]
        is_mod = msg["is_moderator"]

        # Log the message (INFO level — clean, no raw dicts)
        role = "👑" if is_owner else ("🛡️" if is_mod else "👤")
        logger.info(f"{role} {display_name}: {text}")

        # ── Step 1: Welcome first-time chatters ──────────────────────────
        if self.welcome_tracker.is_new(channel_id):
            welcome_msg = self.welcome_tracker.get_welcome_message(display_name)
            send_message(self.youtube, self.chat_id, welcome_msg)
            logger.info(
                f"👋 Welcomed: {display_name} "
                f"(total: {self.welcome_tracker.welcomed_count})"
            )

        # ── Step 2: Check for slash commands (with cooldown) ─────────────
        reply = self.command_router.match(text)
        if reply:
            send_message(self.youtube, self.chat_id, reply)
            return

        # ── Step 3: Check for poll command (owner/mod only) ──────────────
        text_lower = text.strip().lower()
        if text_lower.startswith(f"{BOT_PREFIX}poll"):
            if is_owner or is_mod:
                question, options = parse_poll_command(text)
                if question and options:
                    create_poll(self.youtube, self.chat_id, question, options)
                else:
                    send_message(
                        self.youtube, self.chat_id,
                        '❌ Usage: /poll "Question?" "Option 1" "Option 2"'
                    )
            else:
                send_message(
                    self.youtube, self.chat_id,
                    "⚠️ Only the stream owner or moderators can create polls."
                )
            return

        # ── Step 4: Check for reload command (owner only) ────────────────
        if text_lower == f"{BOT_PREFIX}reload" and is_owner:
            self.command_router.reload()
            send_message(
                self.youtube, self.chat_id,
                f"✅ Commands reloaded! ({self.command_router.trigger_count} triggers)"
            )
            return

    def stop(self):
        """Graceful shutdown."""
        self.running = False
        logger.info("\n🛑 Stryker Bot shutting down...")
        if self._chat_reader:
            self._chat_reader.close()
        if self.welcome_tracker:
            logger.info(
                f"   Tracked {self.welcome_tracker.welcomed_count} viewer(s) this session."
            )
        logger.info("   Goodbye! 👋\n")

    def _detect_bot_channel(self):
        """
        Detect the bot's own channel ID to prevent self-welcoming.
        Uses the channels.list API with 'mine=True'.

        Returns:
            The bot's channel ID, or None if detection failed.
        """
        try:
            response = self.youtube.channels().list(
                part="id",
                mine=True,
            ).execute()

            items = response.get("items", [])
            if items:
                bot_channel_id = items[0]["id"]
                logger.info(f"🤖 Bot channel: {bot_channel_id[:15]}...")
                return bot_channel_id
        except Exception as e:
            logger.warning(f"⚠️  Could not detect bot channel: {e}")

        return None
