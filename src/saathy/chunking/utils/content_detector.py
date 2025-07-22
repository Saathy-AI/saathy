"""Content type detection utilities."""

import re
from typing import Optional

from ..core.interfaces import ContentTypeDetector as ContentTypeDetectorInterface
from ..core.models import ContentType


class ContentTypeDetector(ContentTypeDetectorInterface):
    """Detects content type for automatic chunker selection."""
    
    def __init__(self):
        self.type_patterns = {
            ContentType.CODE: [
                r'def\s+\w+\s*\(',  # Python functions
                r'function\s+\w+\s*\(',  # JavaScript functions
                r'class\s+\w+',  # Classes
                r'import\s+',  # Imports
                r'public\s+class',  # Java classes
                r'#include',  # C/C++ includes
                r'package\s+',  # Java packages
            ],
            ContentType.DOCUMENT: [
                r'^#{1,6}\s+',  # Markdown headers
                r'^[A-Z][A-Z\s]+\n[-=]+\n',  # Underlined headers
                r'^\d+\.\s+',  # Numbered sections
                r'^Abstract\s*:',  # Academic papers
                r'^Introduction\s*:',  # Document sections
            ],
            ContentType.MEETING: [
                r'^\w+:\s*',  # Speaker format
                r'^\[(\w+)\]\s*',  # Bracket speaker format
                r'\[\d{2}:\d{2}:\d{2}\]',  # Timestamps
                r'Meeting\s+Transcript',  # Meeting indicators
                r'Participants:',  # Meeting metadata
            ],
            ContentType.GIT_COMMIT: [
                r'^commit\s+[a-f0-9]{40}',  # Git commit hash
                r'^Author:\s+',  # Git author
                r'^Date:\s+',  # Git date
                r'^diff\s+--git',  # Git diff
                r'^---\s+a/',  # Git diff markers
                r'^+++\s+b/',  # Git diff markers
            ],
            ContentType.SLACK_MESSAGE: [
                r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}',  # Slack timestamps
                r'<@[A-Z0-9]+>',  # Slack mentions
                r':[a-z_]+:',  # Slack emojis
                r'thread_ts:',  # Slack thread indicators
            ],
            ContentType.EMAIL: [
                r'^From:\s+',  # Email headers
                r'^To:\s+',  # Email headers
                r'^Subject:\s+',  # Email headers
                r'^Date:\s+',  # Email date
                r'^Reply-To:\s+',  # Email reply-to
                r'^Content-Type:\s+',  # Email content type
            ]
        }
    
    def detect_content_type(self, content: str, file_extension: Optional[str] = None) -> str:
        """Detect content type based on patterns and file extension."""
        # Check file extension first
        if file_extension:
            extension_type = self._get_type_from_extension(file_extension)
            if extension_type != ContentType.UNKNOWN:
                return extension_type.value
        
        # Check content patterns
        content_lower = content.lower()
        scores = {content_type: 0 for content_type in ContentType}
        
        for content_type, patterns in self.type_patterns.items():
            for pattern in patterns:
                if pattern in content_lower or any(re.search(pattern, content, re.MULTILINE)):
                    scores[content_type] += 1
        
        # Return type with highest score
        best_type = max(scores.items(), key=lambda x: x[1])
        return best_type[0].value if best_type[1] > 0 else ContentType.TEXT.value
    
    def _get_type_from_extension(self, extension: str) -> ContentType:
        """Get content type from file extension."""
        extension = extension.lower().lstrip('.')
        
        code_extensions = {
            'py', 'js', 'ts', 'java', 'cpp', 'c', 'h', 'hpp', 'cs', 'php',
            'rb', 'go', 'rs', 'swift', 'kt', 'scala', 'r', 'm', 'mm'
        }
        
        document_extensions = {
            'md', 'txt', 'rst', 'tex', 'doc', 'docx', 'pdf', 'rtf'
        }
        
        if extension in code_extensions:
            return ContentType.CODE
        elif extension in document_extensions:
            return ContentType.DOCUMENT
        else:
            return ContentType.UNKNOWN 