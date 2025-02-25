# ------------------------------------------------------------------------------
#
#   Copyright 2025 eightballer
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""Telegram Wrapper connection and channel."""

import signal
import asyncio
import logging
import platform
from abc import abstractmethod
from typing import Any, cast
from asyncio.events import AbstractEventLoop
from collections.abc import Callable

from telegram import Update
from aea.common import Address
from telegram.ext import (
    ContextTypes,
    MessageHandler,
    ApplicationBuilder as BaseApplicationBuilder,
    filters,
)
from aea.mail.base import Message, Envelope
from aea.connections.base import Connection, ConnectionStates
from aea.configurations.base import PublicId
from telegram.ext._application import (
    DEFAULT_NONE,  # noqa
    List,
    ODVInput,
    Sequence,
    Coroutine,
    Application as BaseApplication,  # noqa
    TelegramError,
)
from aea.protocols.dialogue.base import Dialogue

from packages.eightballer.protocols.chatroom.message import ChatroomMessage as TelegramMessage
from packages.eightballer.protocols.chatroom.dialogues import (
    ChatroomDialogue as TelegramDialogue,
    BaseChatroomDialogues as BaseTelegramDialogues,
)


CONNECTION_ID = PublicId.from_str("eightballer/telegram_wrapper:0.1.0")


_default_logger = logging.getLogger("aea.packages.eightballer.connections.telegram_wrapper")


class Application(BaseApplication):
    """Override the application."""

    _init_future = None
    loop: asyncio.AbstractEventLoop = None

    async def connect(self, loop: AbstractEventLoop) -> None:
        """Perform the connection."""
        self.loop = loop
        self.init_future = self.loop.create_task(self.initialize())

        await self.init_future
        self.post_init_future = self.loop.create_task(self.post_init(self)) if self.post_init else None

        if self.post_init_future:
            await self.post_init_future.done()

    def __run(
        self,
        updater_coroutine: Coroutine,
        stop_signals: Sequence[int] = None,
        close_loop: bool = True,
    ) -> None:
        # Create a new event loop explicitly
        del close_loop

        # Handle default stop signals if they are not provided
        if stop_signals is None and platform.system() != "Windows":
            stop_signals = [signal.SIGINT, signal.SIGTERM, signal.SIGABRT]
        # Handle stop signals, adding signal handlers
        if stop_signals:
            for sig in stop_signals:
                self.loop.add_signal_handler(sig, self._raise_system_exit)

        self.loop: asyncio.AbstractEventLoop
        # Create Futures manually for each step in your coroutine pipeline
        self.updater_future = self.loop.create_task(updater_coroutine)
        self.start_future = self.loop.create_task(self.start())

    def disconnect(self) -> None:
        """Disconnect the wrapper."""

        self.updater_coroutine.close()
        # Stop the loop and run shutdown procedures
        # Ensure that stopping and shutting down is handled gracefully
        stop_future = self.loop.create_task(self.stop()) if self.running else None
        post_stop_future = self.loop.create_task(self.post_stop(self)) if self.post_stop else None
        shutdown_future = self.loop.create_task(self.shutdown())
        post_shutdown_future = self.loop.create_task(self.post_shutdown(self)) if self.post_shutdown else None

        # Wait for all shutdown tasks to complete
        if stop_future:
            self.loop.run_until_complete(stop_future)
        if post_stop_future:
            self.loop.run_until_complete(post_stop_future)
        self.loop.run_until_complete(shutdown_future)
        if post_shutdown_future:
            self.loop.run_until_complete(post_shutdown_future)

    def run_polling(
        self,
        poll_interval: float = 0.0,
        timeout: int = 10,
        bootstrap_retries: int = -1,
        read_timeout: float = 2,
        write_timeout: ODVInput[float] = DEFAULT_NONE,
        connect_timeout: ODVInput[float] = DEFAULT_NONE,
        pool_timeout: ODVInput[float] = DEFAULT_NONE,
        allowed_updates: List[str] = None,
        drop_pending_updates: bool | None = None,
        close_loop: bool = True,
        stop_signals: ODVInput[Sequence[int]] = DEFAULT_NONE,
    ) -> None:
        """Convenience method that takes care of initializing and starting the app,
        polling updates from Telegram using :meth:`telegram.ext.Updater.start_polling` and
        a graceful shutdown of the app on exit.

        The app will shut down when :exc:`KeyboardInterrupt` or :exc:`SystemExit` is raised.
        On unix, the app will also shut down on receiving the signals specified by
        :paramref:`stop_signals`.

        The order of execution by `run_polling` is roughly as follows:

        - :meth:`initialize`
        - :meth:`post_init`
        - :meth:`telegram.ext.Updater.start_polling`
        - :meth:`start`
        - Run the application until the users stops it
        - :meth:`telegram.ext.Updater.stop`
        - :meth:`stop`
        - :meth:`post_stop`
        - :meth:`shutdown`
        - :meth:`post_shutdown`

        .. include:: inclusions/application_run_tip.rst

        .. seealso::
            :meth:`initialize`, :meth:`start`, :meth:`stop`, :meth:`shutdown`
            :meth:`telegram.ext.Updater.start_polling`, :meth:`telegram.ext.Updater.stop`,
            :meth:`run_webhook`

        Args:
        ----
            poll_interval (:obj:`float`, optional): Time to wait between polling updates from
                Telegram in seconds. Default is ``0.0``.
            timeout (:obj:`float`, optional): Passed to
                :paramref:`telegram.Bot.get_updates.timeout`. Default is ``10`` seconds.
            bootstrap_retries (:obj:`int`, optional): Whether the bootstrapping phase of the
                :class:`telegram.ext.Updater` will retry on failures on the Telegram server.

                * < 0 - retry indefinitely (default)
                *   0 - no retries
                * > 0 - retry up to X times

            read_timeout (:obj:`float`, optional): Value to pass to
                :paramref:`telegram.Bot.get_updates.read_timeout`. Defaults to ``2``.
            write_timeout (:obj:`float` | :obj:`None`, optional): Value to pass to
                :paramref:`telegram.Bot.get_updates.write_timeout`. Defaults to
                :attr:`~telegram.request.BaseRequest.DEFAULT_NONE`.
            connect_timeout (:obj:`float` | :obj:`None`, optional): Value to pass to
                :paramref:`telegram.Bot.get_updates.connect_timeout`. Defaults to
                :attr:`~telegram.request.BaseRequest.DEFAULT_NONE`.
            pool_timeout (:obj:`float` | :obj:`None`, optional): Value to pass to
                :paramref:`telegram.Bot.get_updates.pool_timeout`. Defaults to
                :attr:`~telegram.request.BaseRequest.DEFAULT_NONE`.
            drop_pending_updates (:obj:`bool`, optional): Whether to clean any pending updates on
                Telegram servers before actually starting to poll. Default is :obj:`False`.
            allowed_updates (List[:obj:`str`], optional): Passed to
                :meth:`telegram.Bot.get_updates`.
            close_loop (:obj:`bool`, optional): If :obj:`True`, the current event loop will be
                closed upon shutdown. Defaults to :obj:`True`.

                .. seealso::
                    :meth:`asyncio.loop.close`
            stop_signals (Sequence[:obj:`int`] | :obj:`None`, optional): Signals that will shut
                down the app. Pass :obj:`None` to not use stop signals.
                Defaults to :data:`signal.SIGINT`, :data:`signal.SIGTERM` and
                :data:`signal.SIGABRT` on non Windows platforms.

        Caution:
        -------
                    Not every :class:`asyncio.AbstractEventLoop` implements
                    :meth:`asyncio.loop.add_signal_handler`. Most notably, the standard event loop
                    on Windows, :class:`asyncio.ProactorEventLoop`, does not implement this method.
                    If this method is not available, stop signals can not be set.

        Raises:
        ------
            :exc:`RuntimeError`: If the Application does not have an :class:`telegram.ext.Updater`.

        """
        if not self.updater:
            msg = "Application.run_polling is only available if the application has an Updater."
            raise RuntimeError(msg)

        def error_callback(exc: TelegramError) -> None:
            self.create_task(self.process_error(error=exc, update=None))

        return self.__run(
            updater_coroutine=self.updater.start_polling(
                poll_interval=poll_interval,
                timeout=timeout,
                bootstrap_retries=bootstrap_retries,
                read_timeout=read_timeout,
                write_timeout=write_timeout,
                connect_timeout=connect_timeout,
                pool_timeout=pool_timeout,
                allowed_updates=allowed_updates,
                drop_pending_updates=drop_pending_updates,
                error_callback=error_callback,  # if there is an error in fetching updates
            ),
            close_loop=close_loop,
            stop_signals=stop_signals,
        )


class ApplicationBuilder(BaseApplicationBuilder):
    """Override the application builder."""


class TelegramDialogues(BaseTelegramDialogues):
    """The dialogues class keeps track of all telegram_wrapper dialogues."""

    def __init__(self, self_address: Address, **kwargs) -> None:
        """Initialize dialogues."""
        del kwargs

        def role_from_first_message(  # pylint: disable=unused-argument
            message: Message, receiver_address: Address
        ) -> Dialogue.Role:
            """Infer the role of the agent from an incoming/outgoing first message."""
            assert message, receiver_address
            return TelegramDialogue.Role.AGENT

        BaseTelegramDialogues.__init__(
            self,
            self_address=self_address,
            role_from_first_message=role_from_first_message,
        )


class BaseAsyncChannel:
    """BaseAsyncChannel."""

    def __init__(
        self,
        agent_address: Address,
        connection_id: PublicId,
        message_type: Message,
    ):
        """Initialize the BaseAsyncChannel channel."""

        self.agent_address = agent_address
        self.connection_id = connection_id
        self.message_type = message_type

        self.is_stopped = True
        self._connection = None
        self._tasks: set[asyncio.Task] = set()
        self._in_queue: asyncio.Queue | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self.logger = _default_logger

    @property
    @abstractmethod
    def performative_handlers(self) -> dict[Message.Performative, Callable[[Message, Dialogue], Message]]:
        """Performative to message handler mapping."""

    @abstractmethod
    async def connect(self, loop: AbstractEventLoop) -> None:
        """Connect channel using loop."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect channel."""

    async def send(self, envelope: Envelope) -> None:
        """Send an envelope with a protocol message.

        It sends the envelope, waits for and receives the result.
        The result is translated into a response envelope.
        Finally, the response envelope is sent to the in-queue.

        """

        if not (self._loop and self._connection):
            msg = "{self.__class__.__name__} not connected, call connect first!"
            raise ConnectionError(msg)

        if not isinstance(envelope.message, self.message_type):
            msg = f"Message not of type {self.message_type}"
            raise TypeError(msg)

        message = envelope.message

        if message.performative not in self.performative_handlers:
            log_msg = "Message with unexpected performative `{message.performative}` received."
            self.logger.error(log_msg)
            return

        handler = self.performative_handlers[message.performative]

        dialogue = cast(Dialogue, self._dialogues.update(message))
        if dialogue is None:
            self.logger.warning(f"Could not create dialogue for message={message}")
            return

        response_message = handler(message, dialogue)
        self.logger.info(f"returning message: {response_message}")

        response_envelope = Envelope(
            to=str(envelope.sender),
            sender=str(self.connection_id),
            message=response_message,
            protocol_specification_id=self.message_type.protocol_specification_id,
        )

        await self._in_queue.put(response_envelope)

    async def get_message(self) -> Envelope | None:
        """Check the in-queue for envelopes."""

        if self.is_stopped:
            return None
        try:
            return self._in_queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def _cancel_tasks(self) -> None:
        """Cancel all requests tasks pending."""

        for task in list(self._tasks):
            if task.done():  # pragma: nocover
                continue
            task.cancel()

        for task in list(self._tasks):
            try:
                await task
            except KeyboardInterrupt:
                raise
            except BaseException:  # noqa
                pass  # nosec


class TelegramWrapperAsyncChannel(BaseAsyncChannel):  # pylint: disable=too-many-instance-attributes
    """A channel handling incomming communication from the Telegram Wrapper connection."""

    def __init__(
        self,
        agent_address: Address,
        connection_id: PublicId,
        **kwargs,
    ):
        """Initialize the Telegram Wrapper channel."""

        super().__init__(agent_address, connection_id, message_type=TelegramMessage)

        for key, value in kwargs.items():
            setattr(self, key, value)

        self._dialogues = TelegramDialogues(str(TelegramWrapperConnection.connection_id))
        self.logger.debug("Initialised the Telegram Wrapper channel")

    async def connect(self, loop: AbstractEventLoop) -> None:
        """Connect channel using loop."""

        if self.is_stopped:
            self._loop = loop
            self._in_queue = asyncio.Queue()
            self.is_stopped = False
            try:
                application_builder = Application.builder().token(self.token)
                application_builder._application_class = Application  # noqa

                app = application_builder.build()
                self._connection = app

                await self._connection.connect(loop)

                async def _handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
                    """Echo the user message."""
                    del context
                    response_envelope = self._from_tg_to_aea(update)
                    await self._in_queue.put(response_envelope)
                    # to allow the thing to work in reverse await update.message.reply_text(update.message.text)

                app.add_handler(MessageHandler(filters.TEXT, _handle))
                app.run_polling()
                self.logger.info("Telegram Wrapper has connected.")
            except Exception as e:
                self.is_stopped = True
                self._in_queue = None
                msg = f"Failed to start Telegram Wrapper: {e}"
                raise ConnectionError(msg) from e

    def _from_tg_to_aea(self, update: Update) -> TelegramMessage:
        """Convert a telegram update to a TelegramMessage object."""

        msg = TelegramMessage(
            performative=TelegramMessage.Performative.MESSAGE,
            chat_id=str(update.message.chat_id),
            id=update.message.message_id,
            text=update.message.text,
            from_user=str(update.message.from_user.id),
            timestamp=int(update.message.date.timestamp()),
        )
        return Envelope(
            to=str(self.target_skill_id),
            sender=str(self.connection_id),
            message=msg,
            protocol_specification_id=self.message_type.protocol_specification_id,
        )

    async def disconnect(self) -> None:
        """Disconnect channel."""

        if self.is_stopped:
            return

        await self._cancel_tasks()
        msg = "TelegramWrapperAsyncChannel.disconnect"
        raise NotImplementedError(msg)
        self.is_stopped = True
        self.logger.info("Telegram Wrapper has shutdown.")

    @property
    def performative_handlers(
        self,
    ) -> dict[TelegramMessage.Performative, Callable[[TelegramMessage, TelegramDialogue], TelegramMessage]]:
        """Map performative to handlers."""
        return {
            TelegramMessage.Performative.SEND_MESSAGE: self.send_message,
            TelegramMessage.Performative.RECEIVE_MESSAGE: self.receive_message,
        }

    def send_message(self, message: TelegramMessage, dialogue: TelegramDialogue) -> TelegramMessage:
        """Handle TelegramMessage with SEND_MESSAGE Perfomative."""
        del message

        dialogue.reply(
            performative=TelegramMessage.Performative.MESSAGE_SENT,
            id=...,
            status=...,
        )

        return dialogue.reply(
            performative=TelegramMessage.Performative.ERROR,
            error_code=...,
            error_msg=...,
            error_data=...,
        )

    def receive_message(self, message: TelegramMessage, dialogue: TelegramDialogue) -> TelegramMessage:
        """Handle TelegramMessage with RECEIVE_MESSAGE Perfomative."""
        del message

        dialogue.reply(
            performative=TelegramMessage.Performative.NEW_MESSAGE,
            chat_id=...,
            id=...,
            text=...,
            from_user=...,
            timestamp=...,
        )

        return dialogue.reply(
            performative=TelegramMessage.Performative.ERROR,
            error_code=...,
            error_msg=...,
            error_data=...,
        )


class TelegramWrapperConnection(Connection):
    """Proxy to the functionality of a Telegram Wrapper connection."""

    connection_id = CONNECTION_ID

    def __init__(self, **kwargs: Any) -> None:
        """Initialize a Telegram Wrapper connection."""

        keys = ["target_skill_id", "token"]
        config = kwargs["configuration"].config
        custom_kwargs = {key: config.pop(key) for key in keys}
        super().__init__(**kwargs)

        self.channel = TelegramWrapperAsyncChannel(
            self.address,
            connection_id=self.connection_id,
            **custom_kwargs,
        )

    async def connect(self) -> None:
        """Connect to a Telegram Wrapper."""

        if self.is_connected:  # pragma: nocover
            return

        with self._connect_context():
            self.channel.logger = self.logger
            await self.channel.connect(self.loop)

    async def disconnect(self) -> None:
        """Disconnect from a Telegram Wrapper."""

        if self.is_disconnected:
            return  # pragma: nocover
        self.state = ConnectionStates.disconnecting
        await self.channel.disconnect()
        self.state = ConnectionStates.disconnected

    async def send(self, envelope: Envelope) -> None:
        """Send an envelope."""

        self._ensure_connected()
        return await self.channel.send(envelope)

    async def receive(self, *args: Any, **kwargs: Any) -> Envelope | None:
        """Receive an envelope. Blocking."""
        del args, kwargs

        self._ensure_connected()
        try:
            return await self.channel.get_message()
        except Exception as e:  # noqa
            self.logger.info(f"Exception on receive {e}")
            return None
