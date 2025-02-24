"""Test the metrics skill."""

import json
import logging
from typing import cast
from pathlib import Path
from unittest.mock import patch

from aea.test_tools.test_skill import BaseSkillTestCase
from aea.protocols.dialogue.base import DialogueMessage

from packages.eightballer.protocols.http.message import HttpMessage
from packages.eightballer.skills.participate_in_abci_app import PUBLIC_ID
from packages.eightballer.skills.participate_in_abci_app.handlers import HttpHandler
from packages.eightballer.skills.participate_in_abci_app.dialogues import HttpDialogues


ROOT_DIR = Path(__file__).parent.parent.parent.parent.parent.parent


class TestHttpHandler(BaseSkillTestCase):
    """Test HttpHandler of http_echo."""

    path_to_skill = Path(ROOT_DIR, "packages", PUBLIC_ID.author, "skills", PUBLIC_ID.name)

    @classmethod
    def setup(cls):  # pylint: disable=W0221
        """Setup the test class."""
        super().setup_class()
        cls.http_handler = cast(HttpHandler, cls._skill.skill_context.handlers.metrics_handler)
        cls.logger = cls._skill.skill_context.logger

        cls.http_dialogues = cast(HttpDialogues, cls._skill.skill_context.http_dialogues)

        cls.get_method = "get"
        cls.post_method = "post"
        cls.url = "localhost:8000/metrics"
        cls.version = "some_version"
        cls.headers = "some_headers"
        cls.body = b"some_body"
        cls.sender = "fetchai/some_skill:0.1.0"
        cls.skill_id = str(cls._skill.skill_context.skill_id)

        cls.status_code = 100
        cls.status_text = "some_status_text"

        cls.content = b"some_content"
        cls.list_of_messages = (
            DialogueMessage(
                HttpMessage.Performative.REQUEST,
                {
                    "method": cls.get_method,
                    "url": cls.url,
                    "version": cls.version,
                    "headers": cls.headers,
                    "body": cls.body,
                },
            ),
        )

    def test_setup(self):
        """Test the setup method of the http_echo handler."""
        assert self.http_handler.setup() is None
        self.assert_quantity_in_outbox(0)

    def test_teardown(self):
        """Test the teardown method of the http_echo handler."""
        assert self.http_handler.teardown() is None
        self.assert_quantity_in_outbox(0)

    def test_handle_request_get(self):
        """Test the _handle_request method of the http_echo handler where method is get."""
        # setup
        incoming_message = cast(
            HttpMessage,
            self.build_incoming_message(
                message_type=HttpMessage,
                performative=HttpMessage.Performative.REQUEST,
                to=self.skill_id,
                sender=self.sender,
                method=self.get_method,
                url=self.url,
                version=self.version,
                headers=self.headers,
                body=self.body,
            ),
        )

        # operation
        with patch.object(self.logger, "log") as mock_logger:
            self.http_handler.handle(incoming_message)

        self.assert_quantity_in_outbox(1)

        mock_logger.assert_any_call(
            logging.INFO,
            f"received http request with method={incoming_message.method}, "
            + f"url={incoming_message.url} and body={incoming_message.body}",
        )

        message = self.get_message_from_outbox()
        has_attributes, error_str = self.message_has_attributes(
            actual_message=message,
            message_type=HttpMessage,
            performative=HttpMessage.Performative.RESPONSE,
            to=incoming_message.sender,
            sender=incoming_message.to,
            version=incoming_message.version,
            status_code=200,
            status_text="Success",
            headers=incoming_message.headers,
            body=json.dumps({}).encode("utf-8"),
        )
        assert has_attributes, error_str

        mock_logger.assert_any_call(
            logging.INFO,
            f"responding with: {message}",
        )

    @classmethod
    def teardown(cls, *args, **kwargs):  # noqa
        """Teardown the test class."""
        db_fn = Path("test.db")
        if db_fn.exists():
            db_fn.unlink()
