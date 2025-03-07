import os
from unittest.mock import Mock, patch

import pytest
from mcp_atlassian.jira import JiraFetcher

from tests.fixtures.jira_mocks import MOCK_JIRA_ISSUE_RESPONSE, MOCK_JIRA_JQL_RESPONSE


@pytest.fixture
def mock_cloud_env_vars():
    """Set up mock environment variables for cloud Jira."""
    with patch.dict(
        os.environ,
        {
            "JIRA_URL": "https://example.atlassian.net",
            "JIRA_AUTH_TYPE": "api_token",
            "JIRA_USERNAME": "test_user",
            "JIRA_API_TOKEN": "test_token",
        },
    ):
        yield


@pytest.fixture
def mock_enterprise_basic_env_vars():
    """Set up mock environment variables for enterprise Jira with basic auth."""
    with patch.dict(
        os.environ,
        {
            "JIRA_URL": "https://jira.enterprise.com",
            "JIRA_AUTH_TYPE": "basic",
            "JIRA_USERNAME": "test_user",
            "JIRA_PASSWORD": "test_password",
        },
    ):
        yield


@pytest.fixture
def mock_enterprise_pat_env_vars():
    """Set up mock environment variables for enterprise Jira with PAT."""
    with patch.dict(
        os.environ,
        {
            "JIRA_URL": "https://jira.enterprise.com",
            "JIRA_AUTH_TYPE": "pat",
            "JIRA_PAT": "test_pat",
        },
    ):
        yield


@pytest.fixture
def mock_jira_fetcher(mock_cloud_env_vars):
    """Create a JiraFetcher instance with mocked Jira client."""
    with patch("mcp_atlassian.jira.Jira") as mock_jira:
        # Configure the mock Jira client
        mock_jira_instance = Mock()
        mock_jira_instance.issue.return_value = MOCK_JIRA_ISSUE_RESPONSE
        mock_jira_instance.jql.return_value = MOCK_JIRA_JQL_RESPONSE
        mock_jira.return_value = mock_jira_instance

        fetcher = JiraFetcher()
        return fetcher


def test_jira_fetcher_cloud_initialization(mock_cloud_env_vars):
    """Test JiraFetcher initialization with cloud environment variables."""
    fetcher = JiraFetcher()
    assert fetcher.config.url == "https://example.atlassian.net"
    assert fetcher.config.auth_type.value == "api_token"
    assert fetcher.config.username == "test_user"
    assert fetcher.config.api_token == "test_token"
    assert fetcher.config.is_cloud is True


def test_jira_fetcher_enterprise_basic_initialization(mock_enterprise_basic_env_vars):
    """Test JiraFetcher initialization with enterprise basic auth."""
    fetcher = JiraFetcher()
    assert fetcher.config.url == "https://jira.enterprise.com"
    assert fetcher.config.auth_type.value == "basic"
    assert fetcher.config.username == "test_user"
    assert fetcher.config.password == "test_password"
    assert fetcher.config.is_cloud is False


def test_jira_fetcher_enterprise_pat_initialization(mock_enterprise_pat_env_vars):
    """Test JiraFetcher initialization with enterprise PAT."""
    fetcher = JiraFetcher()
    assert fetcher.config.url == "https://jira.enterprise.com"
    assert fetcher.config.auth_type.value == "pat"
    assert fetcher.config.pat == "test_pat"
    assert fetcher.config.is_cloud is False


def test_jira_fetcher_initialization_missing_url():
    """Test JiraFetcher initialization with missing URL."""
    with patch.dict(os.environ, {"JIRA_AUTH_TYPE": "api_token"}, clear=True):
        with pytest.raises(ValueError, match="JIRA_URL environment variable is required"):
            JiraFetcher()


def test_jira_fetcher_initialization_invalid_auth_type():
    """Test JiraFetcher initialization with invalid auth type."""
    with patch.dict(
        os.environ,
        {
            "JIRA_URL": "https://example.com",
            "JIRA_AUTH_TYPE": "invalid",
        },
        clear=True,
    ):
        with pytest.raises(ValueError, match="Invalid JIRA_AUTH_TYPE"):
            JiraFetcher()


def test_jira_fetcher_initialization_missing_auth_credentials():
    """Test JiraFetcher initialization with missing auth credentials."""
    # Test API token auth without credentials
    with patch.dict(
        os.environ,
        {
            "JIRA_URL": "https://example.com",
            "JIRA_AUTH_TYPE": "api_token",
        },
        clear=True,
    ):
        with pytest.raises(ValueError, match="JIRA_USERNAME and JIRA_API_TOKEN are required"):
            JiraFetcher()

    # Test basic auth without credentials
    with patch.dict(
        os.environ,
        {
            "JIRA_URL": "https://example.com",
            "JIRA_AUTH_TYPE": "basic",
        },
        clear=True,
    ):
        with pytest.raises(ValueError, match="JIRA_USERNAME and JIRA_PASSWORD are required"):
            JiraFetcher()

    # Test PAT auth without token
    with patch.dict(
        os.environ,
        {
            "JIRA_URL": "https://example.com",
            "JIRA_AUTH_TYPE": "pat",
        },
        clear=True,
    ):
        with pytest.raises(ValueError, match="JIRA_PAT is required"):
            JiraFetcher()


def test_parse_date():
    """Test date parsing with various formats."""
    fetcher = JiraFetcher()

    # Test various date formats
    assert fetcher._parse_date("2024-01-01T10:00:00.000+0000") == "2024-01-01"
    assert fetcher._parse_date("2024-01-01T10:00:00.000-0000") == "2024-01-01"
    assert fetcher._parse_date("2024-01-01T10:00:00.000+0900") == "2024-01-01"
    assert fetcher._parse_date("2024-01-01T10:00:00.000Z") == "2024-01-01"

    # Test empty input
    assert fetcher._parse_date("") == ""

    # Test invalid date
    assert fetcher._parse_date("invalid-date") == "invalid-date"


def test_get_issue(mock_jira_fetcher):
    """Test getting a single issue."""
    document = mock_jira_fetcher.get_issue("PROJ-123")

    # Verify document content
    assert "Issue: PROJ-123" in document.page_content
    assert "Title: Test Issue Summary" in document.page_content
    assert "Type: Task" in document.page_content
    assert "Status: In Progress" in document.page_content

    # Verify metadata
    assert document.metadata["key"] == "PROJ-123"
    assert document.metadata["title"] == "Test Issue Summary"
    assert document.metadata["type"] == "Task"
    assert document.metadata["status"] == "In Progress"
    assert document.metadata["priority"] == "Medium"
    assert document.metadata["created_date"] == "2024-01-01"
    assert document.metadata["link"] == "https://example.atlassian.net/browse/PROJ-123"


def test_get_issue_with_comments(mock_jira_fetcher):
    """Test getting an issue with comments."""
    # Configure mock to return comments
    mock_jira_fetcher.jira.issue_get_comments.return_value = {
        "comments": [
            {
                "id": "1",
                "body": "This is a test comment",
                "created": "2024-01-01T10:00:00.000+0000",
                "updated": "2024-01-01T10:00:00.000+0000",
                "author": {"displayName": "Comment User"},
            }
        ]
    }

    document = mock_jira_fetcher.get_issue("PROJ-123", comment_limit=1)

    # Verify comments are included in content
    assert "2024-01-01 - Comment User: This is a test comment" in document.page_content


def test_search_issues(mock_jira_fetcher):
    """Test searching for issues using JQL."""
    documents = mock_jira_fetcher.search_issues("project = PROJ")

    assert len(documents) == 1  # Our mock response has 1 issue

    # Verify the first document
    doc = documents[0]
    assert doc.metadata["key"] == "PROJ-123"
    assert doc.metadata["title"] == "Test Issue Summary"

    # Verify JQL call parameters
    mock_jira_fetcher.jira.jql.assert_called_once_with("project = PROJ", fields="*all", start=0, limit=50, expand=None)


def test_get_project_issues(mock_jira_fetcher):
    """Test getting all issues for a project."""
    documents = mock_jira_fetcher.get_project_issues("PROJ")

    assert len(documents) == 1  # Our mock response has 1 issue

    # Verify JQL query
    mock_jira_fetcher.jira.jql.assert_called_once_with(
        "project = PROJ ORDER BY created DESC",
        fields="*all",
        start=0,
        limit=50,
        expand=None,
    )


def test_error_handling(mock_jira_fetcher):
    """Test error handling in get_issue and search_issues."""
    # Mock Jira client to raise an exception
    mock_jira_fetcher.jira.issue.side_effect = Exception("API Error")

    # Test get_issue error handling
    with pytest.raises(Exception, match="API Error"):
        mock_jira_fetcher.get_issue("PROJ-123")

    # Test search_issues error handling
    mock_jira_fetcher.jira.jql.side_effect = Exception("API Error")
    with pytest.raises(Exception, match="API Error"):
        mock_jira_fetcher.search_issues("project = PROJ")


def test_clean_text(mock_jira_fetcher):
    """Test text cleaning with various inputs."""
    # Test empty text
    assert mock_jira_fetcher._clean_text("") == ""
    assert mock_jira_fetcher._clean_text(None) == ""

    # Test actual text (assuming TextPreprocessor is working)
    with patch.object(mock_jira_fetcher.preprocessor, "clean_jira_text") as mock_clean:
        mock_clean.return_value = "cleaned text"
        assert mock_jira_fetcher._clean_text("some text") == "cleaned text"
        mock_clean.assert_called_once_with("some text")


def test_create_issue(mock_jira_fetcher):
    """Test creating a new issue."""
    # Mock the create_issue response
    mock_jira_fetcher.jira.issue_create.return_value = {"key": "PROJ-123"}
    mock_jira_fetcher.jira.issue.return_value = MOCK_JIRA_ISSUE_RESPONSE

    # Create issue
    document = mock_jira_fetcher.create_issue(
        project_key="PROJ",
        summary="Test Issue",
        issue_type="Task",
        description="Test Description",
    )

    # Verify create_issue was called with correct parameters
    mock_jira_fetcher.jira.issue_create.assert_called_once_with(
        fields={
            "project": {"key": "PROJ"},
            "summary": "Test Issue",
            "issuetype": {"name": "Task"},
            "description": "Test Description",
        }
    )

    # Verify the returned document
    assert document.metadata["key"] == "PROJ-123"
    assert document.metadata["title"] == "Test Issue Summary"
    assert "Type: Task" in document.page_content


def test_create_issue_error(mock_jira_fetcher):
    """Test error handling when creating an issue."""
    mock_jira_fetcher.jira.issue_create.side_effect = Exception("API Error")

    with pytest.raises(Exception, match="API Error"):
        mock_jira_fetcher.create_issue(project_key="PROJ", summary="Test Issue", issue_type="Task")


def test_update_issue(mock_jira_fetcher):
    """Test updating an existing issue."""
    # Mock the update response
    mock_jira_fetcher.jira.issue_update.return_value = None
    mock_jira_fetcher.jira.issue.return_value = MOCK_JIRA_ISSUE_RESPONSE

    # Test data
    fields = {"summary": "Updated Title", "description": "Updated Description"}

    # Update issue
    document = mock_jira_fetcher.update_issue("PROJ-123", fields)

    # Verify update_issue was called with correct parameters
    mock_jira_fetcher.jira.issue_update.assert_called_once_with("PROJ-123", fields=fields)

    # Verify the returned document
    assert document.metadata["key"] == "PROJ-123"
    assert "Title: Test Issue Summary" in document.page_content


def test_update_issue_error(mock_jira_fetcher):
    """Test error handling when updating an issue."""
    mock_jira_fetcher.jira.issue_update.side_effect = Exception("API Error")

    with pytest.raises(Exception, match="API Error"):
        mock_jira_fetcher.update_issue("PROJ-123", {"summary": "Test"})


def test_delete_issue(mock_jira_fetcher):
    """Test deleting an issue."""
    mock_jira_fetcher.jira.delete_issue.return_value = None

    result = mock_jira_fetcher.delete_issue("PROJ-123")
    mock_jira_fetcher.jira.delete_issue.assert_called_once_with("PROJ-123")

    assert result is True


def test_delete_issue_error(mock_jira_fetcher):
    """Test error handling when deleting an issue."""
    mock_jira_fetcher.jira.delete_issue.side_effect = Exception("API Error")

    with pytest.raises(Exception, match="API Error"):
        mock_jira_fetcher.delete_issue("PROJ-123")

    mock_jira_fetcher.jira.delete_issue.assert_called_once_with("PROJ-123")
