"""Tests for the settings management system."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from saathy.config import get_settings


class TestSettings:
    """Test cases for the Settings class."""

    def test_invalid_url_validation(self) -> None:
        """Test that invalid URLs raise validation errors."""
        with patch.dict(os.environ, {"QDRANT_URL": "invalid-url"}):
            with pytest.raises(ValidationError):
                get_settings()

    def test_invalid_port_validation(self) -> None:
        """Test that invalid port numbers raise validation errors."""
        with patch.dict(os.environ, {"PORT": "not-a-number"}):
            with pytest.raises(ValidationError):
                get_settings()

    def test_boolean_parsing(self) -> None:
        """Test that boolean values are parsed correctly."""
        with patch.dict(os.environ, {"DEBUG": "false", "ENABLE_TRACING": "true"}):
            settings = get_settings()
            assert settings.debug is False
            assert settings.enable_tracing is True

    def test_get_settings_equality(self) -> None:
        """Test that get_settings returns an equivalent instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 == settings2
        assert settings1 is not settings2

    def test_case_insensitive_environment_variables(self) -> None:
        """Test that environment variables are case insensitive."""
        with patch.dict(os.environ, {"app_name": "LowercaseApp"}):
            settings = get_settings()
            assert settings.app_name == "LowercaseApp"
