#!/usr/bin/env python3
"""Test script to verify production setup configuration."""

import os
import sys
import tempfile
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from saathy.config import Settings


def test_secret_loading():
    """Test that secrets can be loaded from files."""
    print("Testing secret loading from files...")

    # Create temporary secret files
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test-qdrant-key")
        qdrant_file = f.name

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("test-openai-key")
        openai_file = f.name

    try:
        # Set environment variables
        os.environ["QDRANT_API_KEY_FILE"] = qdrant_file
        os.environ["OPENAI_API_KEY_FILE"] = openai_file

        # Create settings instance
        settings = Settings()

        # Test secret loading
        qdrant_key = settings.qdrant_api_key_str
        openai_key = settings.openai_api_key_str

        assert (
            qdrant_key == "test-qdrant-key"
        ), f"Expected 'test-qdrant-key', got '{qdrant_key}'"
        assert (
            openai_key == "test-openai-key"
        ), f"Expected 'test-openai-key', got '{openai_key}'"

        print("✅ Secret loading from files works correctly")

    finally:
        # Clean up
        os.unlink(qdrant_file)
        os.unlink(openai_file)
        os.environ.pop("QDRANT_API_KEY_FILE", None)
        os.environ.pop("OPENAI_API_KEY_FILE", None)


def test_environment_variables():
    """Test that environment variables are loaded correctly."""
    print("Testing environment variable loading...")

    # Set test environment variables
    os.environ["ENVIRONMENT"] = "production"
    os.environ["DEBUG"] = "false"
    os.environ["LOG_LEVEL"] = "INFO"
    os.environ["QDRANT_URL"] = "http://qdrant:6333"

    try:
        settings = Settings()

        assert settings.environment == "production"
        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert str(settings.qdrant_url) == "http://qdrant:6333"
        assert settings.is_production is True

        print("✅ Environment variable loading works correctly")

    finally:
        # Clean up
        for key in ["ENVIRONMENT", "DEBUG", "LOG_LEVEL", "QDRANT_URL"]:
            os.environ.pop(key, None)


def test_default_values():
    """Test that default values are set correctly."""
    print("Testing default values...")

    settings = Settings()

    assert settings.app_name == "Saathy"
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.log_level == "INFO"
    assert settings.is_development is True

    print("✅ Default values are set correctly")


if __name__ == "__main__":
    print("Running production setup tests...")

    try:
        test_default_values()
        test_environment_variables()
        test_secret_loading()

        print("\n🎉 All tests passed! Production setup is configured correctly.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
