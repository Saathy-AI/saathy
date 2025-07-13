#!/usr/bin/env python3
"""Simple validation script for the settings management system."""

from src.saathy.config import get_settings


def test_singleton():
    """Test singleton pattern."""
    print("Testing singleton pattern...")
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2
    print("✅ Singleton test passed")


def main():
    """Run all validation tests."""
    print("🧪 Running settings validation tests...\n")

    try:
        test_singleton()

        print("\n🎉 All tests passed! Settings management system is working correctly.")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
