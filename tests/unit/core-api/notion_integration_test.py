"""Integration tests for enhanced Notion connector API endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from fastapi.testclient import TestClient

from saathy.api import app
from saathy.config import SecretStr, Settings
from saathy.connectors.base import ConnectorStatus
from saathy.connectors.notion_connector import NotionConnector


class TestNotionConnectorIntegration:
    """Test Notion connector API integration."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    @pytest.fixture
    def mock_notion_connector(self):
        """Create mock Notion connector."""
        connector = MagicMock(spec=NotionConnector)

        # Mock the status property to allow setting its value
        mock_status_enum = MagicMock(spec=ConnectorStatus)
        mock_status_enum.value = ConnectorStatus.ACTIVE.value
        type(connector).status = PropertyMock(return_value=mock_status_enum)

        connector.databases = ["db1", "db2"]
        connector.pages = ["page1", "page2"]
        connector.poll_interval = 300
        connector._start_time = datetime.now(timezone.utc)
        connector._last_sync = {
            "db1": datetime.now(timezone.utc),
            "page1": datetime.now(timezone.utc),
        }
        connector._processed_items = {"item1", "item2", "item3"}
        connector.client = AsyncMock()

        # Mock _extract_title method to return titles from the mock responses
        connector._extract_title = MagicMock(
            side_effect=lambda title_array: title_array[0]["plain_text"]
            if title_array and len(title_array) > 0
            else "Untitled"
        )

        # Mock get_status to return a dictionary as expected by the endpoint
        connector.get_status.return_value = {
            "name": "notion",
            "status": ConnectorStatus.ACTIVE.value,
            "config": {},  # Simplified for test
        }

        return connector

    @patch("saathy.api.app_state")
    def test_notion_status_endpoint(
        self, mock_app_state, client, mock_notion_connector
    ):
        """Test the enhanced Notion status endpoint."""
        mock_app_state.get.return_value = mock_notion_connector

        response = client.get("/connectors/notion/status")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "active"
        assert data["name"] == "notion"
        assert "uptime" in data
        assert data["total_pages_processed"] == 3
        assert data["databases_monitored"] == ["db1", "db2"]
        assert data["pages_monitored"] == ["page1", "page2"]
        assert "sync_statistics" in data
        assert "configuration" in data
        assert data["configuration"]["poll_interval"] == 300
        assert data["configuration"]["databases_count"] == 2
        assert data["configuration"]["pages_count"] == 2

    @patch("saathy.api.app_state")
    def test_notion_start_endpoint(self, mock_app_state, client, mock_notion_connector):
        """Test the Notion start endpoint."""
        mock_app_state.get.return_value = mock_notion_connector

        # Set the mock status value for the test scenario
        mock_notion_connector.status.value = ConnectorStatus.INACTIVE.value

        response = client.post("/connectors/notion/start")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Notion connector started successfully."
        mock_notion_connector.start.assert_called_once()

    @patch("saathy.api.app_state")
    def test_notion_stop_endpoint(self, mock_app_state, client, mock_notion_connector):
        """Test the Notion stop endpoint."""
        mock_app_state.get.return_value = mock_notion_connector

        # Set the mock status value for the test scenario
        mock_notion_connector.status.value = ConnectorStatus.ACTIVE.value

        response = client.post("/connectors/notion/stop")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Notion connector stopped successfully."
        mock_notion_connector.stop.assert_called_once()

    @patch("saathy.api.app_state")
    def test_notion_sync_database(self, mock_app_state, client, mock_notion_connector):
        """Test syncing a specific database."""
        mock_app_state.get.return_value = mock_notion_connector

        response = client.post("/connectors/notion/sync?database_id=db1&full_sync=true")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Database db1 synced successfully."
        assert data["sync_type"] == "full"
        assert data["resource_type"] == "database"
        assert data["resource_id"] == "db1"
        mock_notion_connector._sync_database.assert_called_once_with(
            "db1", full_sync=True
        )

    @patch("saathy.api.app_state")
    def test_notion_sync_page(self, mock_app_state, client, mock_notion_connector):
        """Test syncing a specific page."""
        mock_app_state.get.return_value = mock_notion_connector

        response = client.post("/connectors/notion/sync?page_id=page1&full_sync=false")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Page page1 synced successfully."
        assert data["sync_type"] == "incremental"
        assert data["resource_type"] == "page"
        assert data["resource_id"] == "page1"
        mock_notion_connector._sync_page.assert_called_once_with(
            "page1", full_sync=False
        )

    @patch("saathy.api.app_state")
    def test_notion_sync_all(self, mock_app_state, client, mock_notion_connector):
        """Test full sync of all resources."""
        mock_app_state.get.return_value = mock_notion_connector

        response = client.post("/connectors/notion/sync?full_sync=true")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Full Notion sync completed successfully."
        assert data["sync_type"] == "full"
        assert data["resource_type"] == "all"
        assert data["databases_synced"] == 2
        assert data["pages_synced"] == 2
        mock_notion_connector._initial_sync.assert_called_once()

    @patch("saathy.api.app_state")
    def test_list_notion_databases(self, mock_app_state, client, mock_notion_connector):
        """Test listing Notion databases."""
        mock_app_state.get.return_value = mock_notion_connector

        # Mock search response
        mock_search_response = {
            "results": [
                {
                    "id": "db1",
                    "title": [{"plain_text": "Test Database 1"}],
                    "url": "https://notion.so/db1",
                    "created_time": "2023-01-01T00:00:00Z",
                    "last_edited_time": "2023-01-02T00:00:00Z",
                    "object": "database",
                },
                {
                    "id": "db2",
                    "title": [{"plain_text": "Test Database 2"}],
                    "url": "https://notion.so/db2",
                    "created_time": "2023-01-01T00:00:00Z",
                    "last_edited_time": "2023-01-02T00:00:00Z",
                    "object": "database",
                },
            ]
        }
        mock_notion_connector.client.search.return_value = mock_search_response

        response = client.get("/connectors/notion/databases")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert data["monitored_count"] == 2
        assert len(data["databases"]) == 2
        assert data["databases"][0]["id"] == "db1"
        assert data["databases"][0]["title"] == "Test Database 1"
        assert data["databases"][0]["is_monitored"] is True

    @patch("saathy.api.app_state")
    def test_search_notion_content(self, mock_app_state, client, mock_notion_connector):
        """Test searching Notion content."""
        mock_app_state.get.return_value = mock_notion_connector

        # Mock search response
        mock_search_response = {
            "results": [
                {
                    "id": "page1",
                    "object": "page",
                    "properties": {"title": {"title": [{"plain_text": "Test Page"}]}},
                    "url": "https://notion.so/page1",
                    "last_edited_time": "2023-01-02T00:00:00Z",
                },
                {
                    "id": "db1",
                    "object": "database",
                    "title": [{"plain_text": "Test Database"}],
                    "url": "https://notion.so/db1",
                    "last_edited_time": "2023-01-02T00:00:00Z",
                },
            ]
        }
        mock_notion_connector.client.search.return_value = mock_search_response

        response = client.get("/connectors/notion/search?query=test&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test"
        assert data["total_count"] == 2
        assert len(data["results"]) == 2
        assert data["results"][0]["type"] == "page"
        assert data["results"][0]["title"] == "Test Page"
        assert data["results"][1]["type"] == "database"
        assert data["results"][1]["title"] == "Test Database"

    @patch("saathy.api.app_state")
    def test_notion_connector_unavailable(self, mock_app_state, client):
        """Test endpoints when Notion connector is unavailable."""
        mock_app_state.get.return_value = None

        # Test status endpoint
        response = client.get("/connectors/notion/status")
        assert response.status_code == 503

        # Test start endpoint
        response = client.post("/connectors/notion/start")
        assert response.status_code == 503

        # Test stop endpoint
        response = client.post("/connectors/notion/stop")
        assert response.status_code == 503

        # Test sync endpoint
        response = client.post("/connectors/notion/sync")
        assert response.status_code == 503

        # Test databases endpoint
        response = client.get("/connectors/notion/databases")
        assert response.status_code == 503

        # Test search endpoint
        response = client.get("/connectors/notion/search?query=test")
        assert response.status_code == 503

    @patch("saathy.api.app_state")
    def test_notion_connector_error_handling(
        self, mock_app_state, client, mock_notion_connector
    ):
        """Test error handling in Notion endpoints."""
        mock_app_state.get.return_value = mock_notion_connector

        # Test start endpoint error - use AsyncMock for async methods
        # Set status to inactive so start method is called
        mock_notion_connector.status.value = "inactive"
        mock_notion_connector.start = AsyncMock(side_effect=Exception("Start failed"))
        response = client.post("/connectors/notion/start")
        assert response.status_code == 500
        assert "Failed to start Notion connector" in response.json()["detail"]

        # Reset mock and test stop endpoint error
        # Set status to active so stop method is called
        mock_notion_connector.status.value = "active"
        mock_notion_connector.start = AsyncMock()
        mock_notion_connector.stop = AsyncMock(side_effect=Exception("Stop failed"))
        response = client.post("/connectors/notion/stop")
        assert response.status_code == 500
        assert "Failed to stop Notion connector" in response.json()["detail"]

        # Reset mock and test sync endpoint error
        mock_notion_connector.stop = AsyncMock()
        mock_notion_connector._sync_database = AsyncMock(
            side_effect=Exception("Sync failed")
        )
        response = client.post("/connectors/notion/sync?database_id=db1")
        assert response.status_code == 500
        assert "Failed to sync Notion content" in response.json()["detail"]

        # Reset mock and test search endpoint error
        mock_notion_connector._sync_database = AsyncMock()
        mock_notion_connector.client.search = AsyncMock(
            side_effect=Exception("Search failed")
        )
        response = client.get("/connectors/notion/search?query=test")
        assert response.status_code == 500
        assert "Search failed" in response.json()["detail"]

    @patch("saathy.api.get_settings")
    def test_get_notion_config_function(self, mock_get_settings):
        """Test the get_notion_config helper function."""
        from saathy.api import get_notion_config

        # Test with empty settings
        settings_empty = Settings()
        settings_empty.notion_token = None
        mock_get_settings.return_value = settings_empty
        config = get_notion_config(settings_empty)
        assert config == {}

        # Test with valid settings
        settings_valid = Settings()
        settings_valid.notion_token = SecretStr("test_token")
        settings_valid.notion_databases = "db1,db2"
        settings_valid.notion_pages = "page1,page2"
        settings_valid.notion_poll_interval = 600

        mock_get_settings.return_value = settings_valid
        config = get_notion_config(settings_valid)
        assert config["token"] == "test_token"
        assert config["databases"] == ["db1", "db2"]
        assert config["pages"] == ["page1", "page2"]
        assert config["poll_interval"] == 600
