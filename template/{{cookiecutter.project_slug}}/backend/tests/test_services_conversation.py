{%- if cookiecutter.use_postgresql and cookiecutter.use_sqlalchemy %}
"""Tests for ConversationService (PostgreSQL async variant)."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.services.conversation import ConversationService


class MockConversation:
    """Mock conversation for testing."""

    def __init__(
        self,
        id=None,
        title="Test Conversation",
{%- if cookiecutter.use_jwt %}
        user_id=None,
{%- endif %}
        is_archived=False,
    ):
        self.id = id or uuid4()
        self.title = title
{%- if cookiecutter.use_jwt %}
        self.user_id = user_id
{%- endif %}
        self.is_archived = is_archived


class MockMessage:
    """Mock message for testing."""

    def __init__(
        self,
        id=None,
        conversation_id=None,
        role="user",
        content="Hello",
        model_name=None,
        tokens_used=None,
    ):
        self.id = id or uuid4()
        self.conversation_id = conversation_id or uuid4()
        self.role = role
        self.content = content
        self.model_name = model_name
        self.tokens_used = tokens_used


class MockToolCall:
    """Mock tool call for testing."""

    def __init__(
        self,
        id=None,
        message_id=None,
        tool_name="test_tool",
        args=None,
        result=None,
        status="pending",
    ):
        self.id = id or uuid4()
        self.message_id = message_id or uuid4()
        self.tool_name = tool_name
        self.args = args or {}
        self.result = result
        self.status = status


class TestConversationServiceGetConversation:
    """Tests for get_conversation with ownership check."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> ConversationService:
        """Create ConversationService instance with mock db."""
        return ConversationService(mock_db)

    @pytest.mark.anyio
    async def test_get_conversation_returns_conversation(self, service: ConversationService):
        """get_conversation returns conversation when found."""
        conv_id = uuid4()
        mock_conv = MockConversation(id=conv_id)

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)

            result = await service.get_conversation(conv_id)

            assert result.id == conv_id
            mock_repo.get_conversation_by_id.assert_called_once_with(
                service.db, conv_id, include_messages=False
            )

    @pytest.mark.anyio
    async def test_get_conversation_not_found_raises(self, service: ConversationService):
        """get_conversation raises NotFoundError when not found."""
        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await service.get_conversation(uuid4())

    @pytest.mark.anyio
    async def test_get_conversation_with_messages(self, service: ConversationService):
        """get_conversation passes include_messages to repository."""
        conv_id = uuid4()
        mock_conv = MockConversation(id=conv_id)

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)

            result = await service.get_conversation(conv_id, include_messages=True)

            assert result.id == conv_id
            mock_repo.get_conversation_by_id.assert_called_once_with(
                service.db, conv_id, include_messages=True
            )

{%- if cookiecutter.use_jwt %}

    @pytest.mark.anyio
    async def test_get_conversation_wrong_user_raises(self, service: ConversationService):
        """get_conversation raises NotFoundError when user_id doesn't match and no share exists."""
        conv_id = uuid4()
        owner_id = uuid4()
        other_user_id = uuid4()
        mock_conv = MockConversation(id=conv_id, user_id=owner_id)

        with patch("app.services.conversation.conversation_repo") as mock_repo, \
             patch("app.services.conversation.conversation_share_repo") as mock_share_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)
            mock_share_repo.get_share = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await service.get_conversation(conv_id, user_id=other_user_id)

    @pytest.mark.anyio
    async def test_get_conversation_correct_user_succeeds(self, service: ConversationService):
        """get_conversation succeeds when user_id matches."""
        conv_id = uuid4()
        user_id = uuid4()
        mock_conv = MockConversation(id=conv_id, user_id=user_id)

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)

            result = await service.get_conversation(conv_id, user_id=user_id)

            assert result.id == conv_id

    @pytest.mark.anyio
    async def test_get_conversation_no_user_id_filter_succeeds(self, service: ConversationService):
        """get_conversation succeeds when no user_id filter is provided."""
        conv_id = uuid4()
        owner_id = uuid4()
        mock_conv = MockConversation(id=conv_id, user_id=owner_id)

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)

            result = await service.get_conversation(conv_id)

            assert result.id == conv_id

    @pytest.mark.anyio
    async def test_get_conversation_null_owner_allows_any_user(self, service: ConversationService):
        """get_conversation succeeds when conversation has no user_id set."""
        conv_id = uuid4()
        mock_conv = MockConversation(id=conv_id, user_id=None)

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)

            result = await service.get_conversation(conv_id, user_id=uuid4())

            assert result.id == conv_id
{%- endif %}


class TestConversationServiceListConversations:
    """Tests for list_conversations."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> ConversationService:
        """Create ConversationService instance with mock db."""
        return ConversationService(mock_db)

    @pytest.mark.anyio
    async def test_list_conversations_returns_tuple(self, service: ConversationService):
        """list_conversations returns (items, total) tuple."""
        mock_convs = [MockConversation(), MockConversation()]

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversations_by_user = AsyncMock(return_value=mock_convs)
            mock_repo.count_conversations = AsyncMock(return_value=2)

            items, total = await service.list_conversations(skip=0, limit=50)

            assert len(items) == 2
            assert total == 2

    @pytest.mark.anyio
    async def test_list_conversations_with_pagination(self, service: ConversationService):
        """list_conversations passes skip and limit to repository."""
        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversations_by_user = AsyncMock(return_value=[])
            mock_repo.count_conversations = AsyncMock(return_value=0)

            await service.list_conversations(skip=10, limit=5)

            call_kwargs = mock_repo.get_conversations_by_user.call_args
            assert call_kwargs[1]["skip"] == 10
            assert call_kwargs[1]["limit"] == 5

    @pytest.mark.anyio
    async def test_list_conversations_include_archived(self, service: ConversationService):
        """list_conversations passes include_archived to repository."""
        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversations_by_user = AsyncMock(return_value=[])
            mock_repo.count_conversations = AsyncMock(return_value=0)

            await service.list_conversations(skip=0, limit=50, include_archived=True)

            call_kwargs = mock_repo.get_conversations_by_user.call_args
            assert call_kwargs[1]["include_archived"] is True


class TestConversationServiceCreate:
    """Tests for create_conversation."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> ConversationService:
        """Create ConversationService instance with mock db."""
        return ConversationService(mock_db)

    @pytest.mark.anyio
    async def test_create_conversation(self, service: ConversationService):
        """create_conversation creates and returns a conversation."""
        mock_data = MagicMock()
{%- if cookiecutter.use_jwt %}
        mock_data.user_id = uuid4()
{%- endif %}
        mock_data.title = "Test Conversation"
        mock_conv = MockConversation(title="Test Conversation")

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.create_conversation = AsyncMock(return_value=mock_conv)

            result = await service.create_conversation(mock_data)

            assert result.title == "Test Conversation"
            mock_repo.create_conversation.assert_called_once()


class TestConversationServiceUpdate:
    """Tests for update_conversation with ownership."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> ConversationService:
        """Create ConversationService instance with mock db."""
        return ConversationService(mock_db)

    @pytest.mark.anyio
    async def test_update_conversation_succeeds(self, service: ConversationService):
        """update_conversation updates and returns the conversation."""
        conv_id = uuid4()
        mock_conv = MockConversation(id=conv_id)
        updated_conv = MockConversation(id=conv_id, title="Updated Title")
        mock_update = MagicMock()
        mock_update.model_dump.return_value = {"title": "Updated Title"}

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)
            mock_repo.update_conversation = AsyncMock(return_value=updated_conv)

            result = await service.update_conversation(conv_id, mock_update)

            assert result.title == "Updated Title"
            mock_repo.update_conversation.assert_called_once()

    @pytest.mark.anyio
    async def test_update_nonexistent_conversation_raises(self, service: ConversationService):
        """update_conversation raises NotFoundError when conversation not found."""
        mock_update = MagicMock()
        mock_update.model_dump.return_value = {"title": "New Title"}

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await service.update_conversation(uuid4(), mock_update)

{%- if cookiecutter.use_jwt %}

    @pytest.mark.anyio
    async def test_update_checks_ownership(self, service: ConversationService):
        """update_conversation verifies user owns the conversation."""
        conv_id = uuid4()
        owner_id = uuid4()
        other_id = uuid4()
        mock_conv = MockConversation(id=conv_id, user_id=owner_id)
        mock_update = MagicMock()
        mock_update.model_dump.return_value = {"title": "New Title"}

        with patch("app.services.conversation.conversation_repo") as mock_repo, \
             patch("app.services.conversation.conversation_share_repo") as mock_share_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)
            mock_share_repo.get_share = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await service.update_conversation(conv_id, mock_update, user_id=other_id)
{%- endif %}


class TestConversationServiceArchive:
    """Tests for archive_conversation with ownership."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> ConversationService:
        """Create ConversationService instance with mock db."""
        return ConversationService(mock_db)

    @pytest.mark.anyio
    async def test_archive_conversation_succeeds(self, service: ConversationService):
        """archive_conversation archives and returns the conversation."""
        conv_id = uuid4()
        mock_conv = MockConversation(id=conv_id)
        archived_conv = MockConversation(id=conv_id, is_archived=True)

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)
            mock_repo.archive_conversation = AsyncMock(return_value=archived_conv)

            result = await service.archive_conversation(conv_id)

            assert result.is_archived is True
            mock_repo.archive_conversation.assert_called_once_with(service.db, conv_id)

    @pytest.mark.anyio
    async def test_archive_nonexistent_conversation_raises(self, service: ConversationService):
        """archive_conversation raises NotFoundError when conversation not found."""
        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await service.archive_conversation(uuid4())

    @pytest.mark.anyio
    async def test_archive_repo_returns_none_raises(self, service: ConversationService):
        """archive_conversation raises NotFoundError when repo returns None."""
        conv_id = uuid4()
        mock_conv = MockConversation(id=conv_id)

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)
            mock_repo.archive_conversation = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await service.archive_conversation(conv_id)

{%- if cookiecutter.use_jwt %}

    @pytest.mark.anyio
    async def test_archive_checks_ownership(self, service: ConversationService):
        """archive_conversation verifies user owns the conversation."""
        conv_id = uuid4()
        owner_id = uuid4()
        other_id = uuid4()
        mock_conv = MockConversation(id=conv_id, user_id=owner_id)

        with patch("app.services.conversation.conversation_repo") as mock_repo, \
             patch("app.services.conversation.conversation_share_repo") as mock_share_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)
            mock_share_repo.get_share = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await service.archive_conversation(conv_id, user_id=other_id)
{%- endif %}


class TestConversationServiceDelete:
    """Tests for delete_conversation with ownership."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> ConversationService:
        """Create ConversationService instance with mock db."""
        return ConversationService(mock_db)

    @pytest.mark.anyio
    async def test_delete_own_conversation_succeeds(self, service: ConversationService):
        """delete_conversation succeeds for conversation owner."""
        conv_id = uuid4()
        mock_conv = MockConversation(id=conv_id)

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)
            mock_repo.delete_conversation = AsyncMock(return_value=True)

            result = await service.delete_conversation(conv_id)

            assert result is True
            mock_repo.delete_conversation.assert_called_once_with(service.db, conv_id)

    @pytest.mark.anyio
    async def test_delete_nonexistent_conversation_raises(self, service: ConversationService):
        """delete_conversation raises NotFoundError when conversation not found."""
        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await service.delete_conversation(uuid4())

    @pytest.mark.anyio
    async def test_delete_repo_returns_false_raises(self, service: ConversationService):
        """delete_conversation raises NotFoundError when repo returns False."""
        conv_id = uuid4()
        mock_conv = MockConversation(id=conv_id)

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)
            mock_repo.delete_conversation = AsyncMock(return_value=False)

            with pytest.raises(NotFoundError):
                await service.delete_conversation(conv_id)

{%- if cookiecutter.use_jwt %}

    @pytest.mark.anyio
    async def test_delete_checks_ownership(self, service: ConversationService):
        """delete_conversation verifies user owns the conversation."""
        conv_id = uuid4()
        owner_id = uuid4()
        other_id = uuid4()
        mock_conv = MockConversation(id=conv_id, user_id=owner_id)

        with patch("app.services.conversation.conversation_repo") as mock_repo, \
             patch("app.services.conversation.conversation_share_repo") as mock_share_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)
            mock_share_repo.get_share = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await service.delete_conversation(conv_id, user_id=other_id)
{%- endif %}


class TestConversationServiceGetMessage:
    """Tests for get_message."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> ConversationService:
        """Create ConversationService instance with mock db."""
        return ConversationService(mock_db)

    @pytest.mark.anyio
    async def test_get_message_returns_message(self, service: ConversationService):
        """get_message returns message when found."""
        msg_id = uuid4()
        mock_msg = MockMessage(id=msg_id)

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_message_by_id = AsyncMock(return_value=mock_msg)

            result = await service.get_message(msg_id)

            assert result.id == msg_id
            mock_repo.get_message_by_id.assert_called_once_with(service.db, msg_id)

    @pytest.mark.anyio
    async def test_get_message_not_found_raises(self, service: ConversationService):
        """get_message raises NotFoundError when not found."""
        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_message_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await service.get_message(uuid4())


class TestConversationServiceListMessages:
    """Tests for list_messages."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> ConversationService:
        """Create ConversationService instance with mock db."""
        return ConversationService(mock_db)

    @pytest.mark.anyio
    async def test_list_messages_returns_tuple(self, service: ConversationService):
        """list_messages returns (items, total) tuple."""
        conv_id = uuid4()
        mock_conv = MockConversation(id=conv_id)
        mock_messages = [MockMessage(), MockMessage()]

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)
            mock_repo.get_messages_by_conversation = AsyncMock(return_value=mock_messages)
            mock_repo.count_messages = AsyncMock(return_value=2)

            items, total = await service.list_messages(conv_id)

            assert len(items) == 2
            assert total == 2

    @pytest.mark.anyio
    async def test_list_messages_verifies_conversation_exists(self, service: ConversationService):
        """list_messages raises NotFoundError when conversation not found."""
        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await service.list_messages(uuid4())

    @pytest.mark.anyio
    async def test_list_messages_with_pagination(self, service: ConversationService):
        """list_messages passes skip and limit to repository."""
        conv_id = uuid4()
        mock_conv = MockConversation(id=conv_id)

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)
            mock_repo.get_messages_by_conversation = AsyncMock(return_value=[])
            mock_repo.count_messages = AsyncMock(return_value=0)

            await service.list_messages(conv_id, skip=5, limit=10)

            call_kwargs = mock_repo.get_messages_by_conversation.call_args
            assert call_kwargs[1]["skip"] == 5
            assert call_kwargs[1]["limit"] == 10

    @pytest.mark.anyio
    async def test_list_messages_with_tool_calls(self, service: ConversationService):
        """list_messages passes include_tool_calls to repository."""
        conv_id = uuid4()
        mock_conv = MockConversation(id=conv_id)

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)
            mock_repo.get_messages_by_conversation = AsyncMock(return_value=[])
            mock_repo.count_messages = AsyncMock(return_value=0)

            await service.list_messages(conv_id, include_tool_calls=True)

            call_kwargs = mock_repo.get_messages_by_conversation.call_args
            assert call_kwargs[1]["include_tool_calls"] is True


class TestConversationServiceAddMessage:
    """Tests for add_message."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> ConversationService:
        """Create ConversationService instance with mock db."""
        return ConversationService(mock_db)

    @pytest.mark.anyio
    async def test_add_message_succeeds(self, service: ConversationService):
        """add_message creates and returns a message."""
        conv_id = uuid4()
        mock_conv = MockConversation(id=conv_id)
        mock_msg = MockMessage(conversation_id=conv_id, role="user", content="Hello")
        mock_data = MagicMock()
        mock_data.role = "user"
        mock_data.content = "Hello"
        mock_data.model_name = None
        mock_data.tokens_used = None

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)
            mock_repo.create_message = AsyncMock(return_value=mock_msg)

            result = await service.add_message(conv_id, mock_data)

            assert result.content == "Hello"
            assert result.role == "user"
            mock_repo.create_message.assert_called_once()

    @pytest.mark.anyio
    async def test_add_message_verifies_conversation_exists(self, service: ConversationService):
        """add_message raises NotFoundError when conversation not found."""
        mock_data = MagicMock()

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_conversation_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await service.add_message(uuid4(), mock_data)


class TestConversationServiceDeleteMessage:
    """Tests for delete_message."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> ConversationService:
        """Create ConversationService instance with mock db."""
        return ConversationService(mock_db)

    @pytest.mark.anyio
    async def test_delete_message_succeeds(self, service: ConversationService):
        """delete_message returns True when message is deleted."""
        msg_id = uuid4()

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.delete_message = AsyncMock(return_value=True)

            result = await service.delete_message(msg_id)

            assert result is True
            mock_repo.delete_message.assert_called_once_with(service.db, msg_id)

    @pytest.mark.anyio
    async def test_delete_message_not_found_raises(self, service: ConversationService):
        """delete_message raises NotFoundError when message not found."""
        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.delete_message = AsyncMock(return_value=False)

            with pytest.raises(NotFoundError):
                await service.delete_message(uuid4())


class TestConversationServiceToolCalls:
    """Tests for tool call methods."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> ConversationService:
        """Create ConversationService instance with mock db."""
        return ConversationService(mock_db)

    @pytest.mark.anyio
    async def test_get_tool_call_returns_tool_call(self, service: ConversationService):
        """get_tool_call returns tool call when found."""
        tc_id = uuid4()
        mock_tc = MockToolCall(id=tc_id)

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_tool_call_by_id = AsyncMock(return_value=mock_tc)

            result = await service.get_tool_call(tc_id)

            assert result.id == tc_id

    @pytest.mark.anyio
    async def test_get_tool_call_not_found_raises(self, service: ConversationService):
        """get_tool_call raises NotFoundError when not found."""
        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_tool_call_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await service.get_tool_call(uuid4())

    @pytest.mark.anyio
    async def test_list_tool_calls_returns_list(self, service: ConversationService):
        """list_tool_calls returns list of tool calls for a message."""
        msg_id = uuid4()
        mock_msg = MockMessage(id=msg_id)
        mock_tool_calls = [MockToolCall(), MockToolCall()]

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_message_by_id = AsyncMock(return_value=mock_msg)
            mock_repo.get_tool_calls_by_message = AsyncMock(return_value=mock_tool_calls)

            result = await service.list_tool_calls(msg_id)

            assert len(result) == 2

    @pytest.mark.anyio
    async def test_list_tool_calls_verifies_message_exists(self, service: ConversationService):
        """list_tool_calls raises NotFoundError when message not found."""
        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_message_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await service.list_tool_calls(uuid4())

    @pytest.mark.anyio
    async def test_start_tool_call_succeeds(self, service: ConversationService):
        """start_tool_call records and returns a new tool call."""
        msg_id = uuid4()
        mock_msg = MockMessage(id=msg_id)
        mock_tc = MockToolCall(message_id=msg_id, tool_name="search")
        mock_data = MagicMock()
        mock_data.tool_call_id = str(uuid4())
        mock_data.tool_name = "search"
        mock_data.args = {"query": "test"}
        mock_data.started_at = None

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_message_by_id = AsyncMock(return_value=mock_msg)
            mock_repo.create_tool_call = AsyncMock(return_value=mock_tc)

            result = await service.start_tool_call(msg_id, mock_data)

            assert result.tool_name == "search"
            mock_repo.create_tool_call.assert_called_once()

    @pytest.mark.anyio
    async def test_start_tool_call_verifies_message_exists(self, service: ConversationService):
        """start_tool_call raises NotFoundError when message not found."""
        mock_data = MagicMock()

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_message_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await service.start_tool_call(uuid4(), mock_data)

    @pytest.mark.anyio
    async def test_complete_tool_call_succeeds(self, service: ConversationService):
        """complete_tool_call marks tool call as completed."""
        tc_id = uuid4()
        mock_tc = MockToolCall(id=tc_id, status="pending")
        completed_tc = MockToolCall(id=tc_id, status="completed", result="success")
        mock_data = MagicMock()
        mock_data.result = "success"
        mock_data.completed_at = None
        mock_data.success = True

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_tool_call_by_id = AsyncMock(return_value=mock_tc)
            mock_repo.complete_tool_call = AsyncMock(return_value=completed_tc)

            result = await service.complete_tool_call(tc_id, mock_data)

            assert result.status == "completed"
            assert result.result == "success"
            mock_repo.complete_tool_call.assert_called_once()

    @pytest.mark.anyio
    async def test_complete_tool_call_not_found_raises(self, service: ConversationService):
        """complete_tool_call raises NotFoundError when tool call not found."""
        mock_data = MagicMock()

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            mock_repo.get_tool_call_by_id = AsyncMock(return_value=None)

            with pytest.raises(NotFoundError):
                await service.complete_tool_call(uuid4(), mock_data)


class TestConversationServiceLinkFiles:
    """Tests for link_files_to_message."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> ConversationService:
        """Create ConversationService instance with mock db."""
        return ConversationService(mock_db)

    @pytest.mark.anyio
    async def test_link_files_empty_list_returns_early(self, service: ConversationService):
        """link_files_to_message returns immediately for empty file list."""
        await service.link_files_to_message(uuid4(), [])

        # Should not call db.execute for empty list
        service.db.execute.assert_not_called()

    @pytest.mark.anyio
    async def test_link_files_calls_db(self, service: ConversationService):
        """link_files_to_message executes update and flushes."""
        msg_id = uuid4()
        file_ids = [str(uuid4()), str(uuid4())]

        with patch("app.db.models.chat_file.ChatFile") as mock_chat_file, \
             patch("sqlalchemy.update") as mock_sa_update:
            mock_chat_file.id.in_ = MagicMock()
            mock_sa_update.return_value.where.return_value.values.return_value = "stmt"

            await service.link_files_to_message(msg_id, file_ids)

            service.db.execute.assert_called_once()
            service.db.flush.assert_called_once()


class TestConversationServiceExportAll:
    """Tests for export_all."""

    @pytest.fixture
    def mock_db(self) -> AsyncMock:
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db: AsyncMock) -> ConversationService:
        """Create ConversationService instance with mock db."""
        return ConversationService(mock_db)

    @pytest.mark.anyio
    async def test_export_all_empty(self, service: ConversationService):
        """export_all returns empty list when no conversations exist."""
        with patch("app.services.conversation.conversation_repo") as mock_repo:
            # export_chunk returns [] → loop exits immediately
            mock_repo.export_chunk = AsyncMock(return_value=[])

            result = await service.export_all()

            assert result == []
            mock_repo.export_chunk.assert_called_once()

    @pytest.mark.anyio
    async def test_export_all_with_conversations(self, service: ConversationService):
        """export_all returns formatted conversation data."""
        conv_id = uuid4()
        msg_id = uuid4()
        mock_conv = MagicMock()
        mock_conv.id = conv_id
        mock_conv.title = "Test"
        mock_conv.created_at = None
        mock_conv.updated_at = None
        mock_conv.is_archived = False

        mock_msg = MagicMock()
        mock_msg.id = msg_id
        mock_msg.role = "user"
        mock_msg.content = "Hello"
        mock_msg.created_at = None
        mock_msg.tool_calls = []
        mock_msg.model_name = None
        mock_msg.tokens_used = None

        with patch("app.services.conversation.conversation_repo") as mock_repo:
            # First call returns one conversation (< EXPORT_CHUNK_SIZE → loop exits after one pass)
            mock_repo.export_chunk = AsyncMock(return_value=[mock_conv])
            # get_conversation used inside list_messages
            mock_repo.get_conversation_by_id = AsyncMock(return_value=mock_conv)
            mock_repo.get_messages_by_conversation = AsyncMock(return_value=[mock_msg])
            mock_repo.count_messages = AsyncMock(return_value=1)
{%- if cookiecutter.use_jwt %}
            # message_rating_repo is lazily imported inside export_all, so patch the module
            with patch("app.repositories.message_rating_repo") as mock_rating_repo:
                mock_rating_repo.get_ratings_with_users_for_messages = AsyncMock(return_value=[])
                result = await service.export_all()
{%- else %}
            result = await service.export_all()
{%- endif %}

            assert len(result) == 1
            assert result[0]["id"] == str(conv_id)
            assert result[0]["title"] == "Test"
            assert len(result[0]["messages"]) == 1
            assert result[0]["messages"][0]["role"] == "user"
            assert result[0]["messages"][0]["content"] == "Hello"
{%- endif %}
