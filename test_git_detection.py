#!/usr/bin/env python3
"""Test git commit detection."""

import sys

sys.path.insert(0, 'src')

from saathy.chunking.core.models import ContentType
from saathy.chunking.utils.content_detector import ContentTypeDetector


def test_git_detection():
    detector = ContentTypeDetector()

    # Test git commit content
    git_content = "commit abc123\nAuthor: John Doe"
    detected = detector.detect_content_type(git_content)

    print(f"Git content: {git_content}")
    print(f"Detected type: {detected}")
    print(f"Expected: {ContentType.GIT_COMMIT.value}")
    print(f"Match: {detected == ContentType.GIT_COMMIT.value}")

    # Test meeting content
    meeting_content = "Alice: Hello\nBob: Hi"
    detected = detector.detect_content_type(meeting_content)

    print(f"\nMeeting content: {meeting_content}")
    print(f"Detected type: {detected}")
    print(f"Expected: {ContentType.MEETING.value}")
    print(f"Match: {detected == ContentType.MEETING.value}")

if __name__ == "__main__":
    test_git_detection()
