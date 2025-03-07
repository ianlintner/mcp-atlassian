from dataclasses import dataclass


@dataclass
class ConfluenceConfig:
    """Confluence API configuration."""

    url: str  # Base URL for Confluence
    username: str  # Email or username
    api_token: str  # API token used as password

    @property
    def is_cloud(self) -> bool:
        """Check if this is a cloud instance."""
        return "atlassian.net" in self.url


from enum import Enum
from typing import Optional


class JiraAuthType(Enum):
    """Supported Jira authentication methods."""
    BASIC = "basic"  # Username + Password
    API_TOKEN = "api_token"  # Cloud API Token
    PAT = "pat"  # Personal Access Token


@dataclass
class JiraConfig:
    """Jira API configuration."""

    url: str  # Base URL for Jira
    auth_type: JiraAuthType  # Authentication method to use
    username: Optional[str] = None  # Email or username (for BASIC and API_TOKEN)
    password: Optional[str] = None  # Password (for BASIC auth)
    api_token: Optional[str] = None  # API token (for cloud)
    pat: Optional[str] = None  # Personal Access Token (for enterprise)

    @property
    def is_cloud(self) -> bool:
        """Check if this is a cloud instance."""
        return "atlassian.net" in self.url

    def validate(self) -> None:
        """Validate the configuration based on auth type."""
        if not self.url:
            raise ValueError("Jira URL is required")

        if self.auth_type == JiraAuthType.BASIC:
            if not self.username or not self.password:
                raise ValueError("Username and password are required for basic authentication")
        elif self.auth_type == JiraAuthType.API_TOKEN:
            if not self.username or not self.api_token:
                raise ValueError("Username and API token are required for API token authentication")
        elif self.auth_type == JiraAuthType.PAT:
            if not self.pat:
                raise ValueError("Personal Access Token (PAT) is required for PAT authentication")
