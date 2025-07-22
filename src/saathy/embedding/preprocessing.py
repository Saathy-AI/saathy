"""Content preprocessing for embedding generation."""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PreprocessingResult:
    """Result of content preprocessing."""

    content: str
    metadata: Dict[str, Any]
    content_type: str
    language: Optional[str] = None
    quality_score: float = 1.0
    preprocessing_steps: List[str] = field(default_factory=list)


class ContentPreprocessor(ABC):
    """Base class for content preprocessing."""

    @abstractmethod
    def preprocess(
        self, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> PreprocessingResult:
        """Preprocess content for embedding."""
        pass

    @abstractmethod
    def get_content_type(self) -> str:
        """Get the content type this preprocessor handles."""
        pass


class TextPreprocessor(ContentPreprocessor):
    """General text preprocessing."""

    def __init__(self):
        self.quality_threshold = 0.3

    def get_content_type(self) -> str:
        return "text"

    def preprocess(
        self, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> PreprocessingResult:
        """Preprocess general text content."""
        steps = []
        original_content = content

        # Clean whitespace
        content = self._clean_whitespace(content)
        steps.append("whitespace_cleaning")

        # Remove excessive newlines
        content = self._normalize_newlines(content)
        steps.append("newline_normalization")

        # Basic text cleaning
        content = self._clean_text(content)
        steps.append("text_cleaning")

        # Detect language (basic implementation)
        language = self._detect_language(content)

        # Calculate quality score
        quality_score = self._calculate_quality_score(original_content, content)

        return PreprocessingResult(
            content=content,
            metadata=metadata or {},
            content_type="text",
            language=language,
            quality_score=quality_score,
            preprocessing_steps=steps,
        )

    def _clean_whitespace(self, text: str) -> str:
        """Clean excessive whitespace."""
        # Replace multiple spaces with single space
        text = re.sub(r"\s+", " ", text)
        # Remove leading/trailing whitespace
        return text.strip()

    def _normalize_newlines(self, text: str) -> str:
        """Normalize newlines and remove excessive ones."""
        # Replace multiple newlines with single newline
        text = re.sub(r"\n\s*\n", "\n\n", text)
        return text

    def _clean_text(self, text: str) -> str:
        """Basic text cleaning."""
        # Remove control characters except newlines and tabs
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
        return text

    def _detect_language(self, text: str) -> Optional[str]:
        """Basic language detection."""
        # Simple heuristic based on common words
        english_words = {
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
        }
        words = set(text.lower().split())
        english_count = len(words.intersection(english_words))

        if english_count > 0:
            return "en"
        return None

    def _calculate_quality_score(self, original: str, processed: str) -> float:
        """Calculate content quality score."""
        if not original or not processed:
            return 0.0

        # Length ratio
        length_ratio = len(processed) / len(original) if original else 0

        # Character diversity
        char_diversity = len(set(processed)) / len(processed) if processed else 0

        # Word count
        word_count = len(processed.split())

        # Combined score
        score = (
            length_ratio * 0.4 + char_diversity * 0.3 + min(word_count / 100, 1.0) * 0.3
        )
        return max(0.0, min(1.0, score))


class CodePreprocessor(ContentPreprocessor):
    """Code-specific preprocessing."""

    def __init__(self):
        self.supported_languages = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".cpp": "cpp",
            ".c": "c",
            ".cs": "csharp",
            ".go": "go",
            ".rs": "rust",
            ".php": "php",
            ".rb": "ruby",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
        }

    def get_content_type(self) -> str:
        return "code"

    def preprocess(
        self, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> PreprocessingResult:
        """Preprocess code content."""
        steps = []
        original_content = content

        # Detect language from metadata or content
        language = self._detect_language(content, metadata)

        # Remove comments
        content = self._remove_comments(content, language)
        steps.append("comment_removal")

        # Normalize whitespace
        content = self._normalize_whitespace(content)
        steps.append("whitespace_normalization")

        # Extract function signatures
        functions = self._extract_functions(content, language)
        steps.append("function_extraction")

        # Clean code structure
        content = self._clean_code_structure(content)
        steps.append("structure_cleaning")

        # Calculate quality score
        quality_score = self._calculate_code_quality(
            original_content, content, functions
        )

        # Update metadata
        updated_metadata = metadata or {}
        updated_metadata.update(
            {
                "language": language,
                "function_count": len(functions),
                "functions": functions,
            }
        )

        return PreprocessingResult(
            content=content,
            metadata=updated_metadata,
            content_type="code",
            language=language,
            quality_score=quality_score,
            preprocessing_steps=steps,
        )

    def _detect_language(self, content: str, metadata: Optional[Dict[str, Any]]) -> str:
        """Detect programming language."""
        if metadata and "file_extension" in metadata:
            ext = metadata["file_extension"].lower()
            return self.supported_languages.get(ext, "unknown")

        # Try to detect from content patterns
        if "def " in content and "import " in content:
            return "python"
        elif "function " in content and "var " in content:
            return "javascript"
        elif "public class" in content and "public static void main" in content:
            return "java"
        elif "#include" in content and "int main" in content:
            return "c"
        else:
            return "unknown"

    def _remove_comments(self, content: str, language: str) -> str:
        """Remove comments based on language."""
        if language == "python":
            # Remove single-line comments
            content = re.sub(r"#.*$", "", content, flags=re.MULTILINE)
            # Remove multi-line comments (docstrings)
            content = re.sub(r'""".*?"""', "", content, flags=re.DOTALL)
            content = re.sub(r"'''.*?'''", "", content, flags=re.DOTALL)
        elif language in ["javascript", "typescript", "java", "cpp", "c", "csharp"]:
            # Remove single-line comments
            content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)
            # Remove multi-line comments
            content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

        return content

    def _normalize_whitespace(self, content: str) -> str:
        """Normalize whitespace in code."""
        # Replace multiple spaces with single space
        content = re.sub(r" +", " ", content)
        # Normalize newlines
        content = re.sub(r"\n\s*\n", "\n", content)
        return content.strip()

    def _extract_functions(self, content: str, language: str) -> List[str]:
        """Extract function signatures."""
        functions = []

        if language == "python":
            # Extract function definitions
            pattern = r"def\s+(\w+)\s*\([^)]*\)\s*:"
            functions = re.findall(pattern, content)
        elif language in ["javascript", "typescript"]:
            # Extract function declarations
            patterns = [
                r"function\s+(\w+)\s*\(",
                r"(\w+)\s*[:=]\s*function\s*\(",
                r"(\w+)\s*[:=]\s*\([^)]*\)\s*=>",
            ]
            for pattern in patterns:
                functions.extend(re.findall(pattern, content))
        elif language in ["java", "cpp", "c", "csharp"]:
            # Extract method declarations
            pattern = r"(\w+)\s+\w+\s*\([^)]*\)\s*\{"
            functions = re.findall(pattern, content)

        return list(set(functions))  # Remove duplicates

    def _clean_code_structure(self, content: str) -> str:
        """Clean code structure while preserving logic."""
        # Remove empty lines
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        return "\n".join(lines)

    def _calculate_code_quality(
        self, original: str, processed: str, functions: List[str]
    ) -> float:
        """Calculate code quality score."""
        if not original or not processed:
            return 0.0

        # Function density
        function_density = len(functions) / max(len(processed.split()), 1)

        # Code complexity (simple heuristic)
        complexity = len(re.findall(r"[{}()\[\]]", processed))

        # Length preservation
        length_ratio = len(processed) / len(original) if original else 0

        # Combined score
        score = (
            min(function_density * 10, 1.0) * 0.4
            + min(complexity / 100, 1.0) * 0.3
            + length_ratio * 0.3
        )

        return max(0.0, min(1.0, score))


class MeetingPreprocessor(ContentPreprocessor):
    """Meeting transcript preprocessing."""

    def get_content_type(self) -> str:
        return "meeting"

    def preprocess(
        self, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> PreprocessingResult:
        """Preprocess meeting transcripts."""
        steps = []
        original_content = content

        # Extract speaker information
        speakers = self._extract_speakers(content)
        steps.append("speaker_extraction")

        # Preserve timestamps
        timestamps = self._extract_timestamps(content)
        steps.append("timestamp_extraction")

        # Clean transcript
        content = self._clean_transcript(content)
        steps.append("transcript_cleaning")

        # Extract key topics
        topics = self._extract_topics(content)
        steps.append("topic_extraction")

        # Calculate quality score
        quality_score = self._calculate_meeting_quality(
            original_content, content, speakers
        )

        # Update metadata
        updated_metadata = metadata or {}
        updated_metadata.update(
            {
                "speakers": speakers,
                "timestamps": timestamps,
                "topics": topics,
                "participant_count": len(speakers),
            }
        )

        return PreprocessingResult(
            content=content,
            metadata=updated_metadata,
            content_type="meeting",
            language="en",  # Assuming English for now
            quality_score=quality_score,
            preprocessing_steps=steps,
        )

    def _extract_speakers(self, content: str) -> List[str]:
        """Extract unique speakers from transcript."""
        # Common patterns for speaker identification
        patterns = [
            r"^(\w+):",  # Speaker: format
            r"^\[(\w+)\]",  # [Speaker] format
            r"^(\w+)\s*\(",  # Speaker (format
        ]

        speakers = set()
        for line in content.split("\n"):
            for pattern in patterns:
                match = re.match(pattern, line.strip())
                if match:
                    speakers.add(match.group(1))
                    break

        return list(speakers)

    def _extract_timestamps(self, content: str) -> List[str]:
        """Extract timestamps from transcript."""
        # Common timestamp patterns
        patterns = [
            r"\[(\d{2}:\d{2}:\d{2})\]",  # [HH:MM:SS]
            r"(\d{2}:\d{2}:\d{2})",  # HH:MM:SS
            r"\[(\d{2}:\d{2})\]",  # [MM:SS]
        ]

        timestamps = []
        for pattern in patterns:
            timestamps.extend(re.findall(pattern, content))

        return timestamps

    def _clean_transcript(self, content: str) -> str:
        """Clean meeting transcript."""
        # Remove speaker prefixes
        content = re.sub(r"^\w+:\s*", "", content, flags=re.MULTILINE)
        content = re.sub(r"^\[\w+\]\s*", "", content, flags=re.MULTILINE)

        # Remove timestamps
        content = re.sub(r"\[\d{2}:\d{2}:\d{2}\]", "", content)
        content = re.sub(r"\d{2}:\d{2}:\d{2}", "", content)

        # Clean whitespace
        content = re.sub(r"\s+", " ", content)
        return content.strip()

    def _extract_topics(self, content: str) -> List[str]:
        """Extract key topics from meeting content."""
        # Simple keyword extraction
        keywords = [
            "agenda",
            "discussion",
            "decision",
            "action",
            "review",
            "planning",
            "strategy",
            "budget",
            "timeline",
            "milestone",
        ]

        topics = []
        for keyword in keywords:
            if keyword.lower() in content.lower():
                topics.append(keyword)

        return topics

    def _calculate_meeting_quality(
        self, original: str, processed: str, speakers: List[str]
    ) -> float:
        """Calculate meeting transcript quality."""
        if not original or not processed:
            return 0.0

        # Speaker diversity
        speaker_score = min(len(speakers) / 5, 1.0)  # Normalize to 5 speakers

        # Content length
        length_score = min(len(processed.split()) / 500, 1.0)  # Normalize to 500 words

        # Combined score
        score = speaker_score * 0.6 + length_score * 0.4
        return max(0.0, min(1.0, score))


class ImagePreprocessor(ContentPreprocessor):
    """Image content preprocessing (OCR and context extraction)."""

    def __init__(self):
        self.ocr_available = self._check_ocr_availability()

    def get_content_type(self) -> str:
        return "image"

    def preprocess(
        self, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> PreprocessingResult:
        """Preprocess image content (extract text via OCR)."""
        steps = []

        # Extract text from image if OCR is available
        if self.ocr_available and metadata and "image_path" in metadata:
            extracted_text = self._extract_text_from_image(metadata["image_path"])
            steps.append("ocr_text_extraction")
        else:
            extracted_text = content  # Use provided text content

        # Clean extracted text
        cleaned_text = self._clean_extracted_text(extracted_text)
        steps.append("text_cleaning")

        # Extract visual context
        visual_context = self._extract_visual_context(metadata)
        steps.append("visual_context_extraction")

        # Combine text and visual context
        final_content = f"{cleaned_text}\n{visual_context}".strip()

        # Calculate quality score
        quality_score = self._calculate_image_quality(extracted_text, visual_context)

        # Update metadata
        updated_metadata = metadata or {}
        updated_metadata.update(
            {
                "ocr_used": self.ocr_available,
                "visual_context": visual_context,
                "text_extracted": bool(extracted_text.strip()),
            }
        )

        return PreprocessingResult(
            content=final_content,
            metadata=updated_metadata,
            content_type="image",
            language="en",  # Assuming English for OCR
            quality_score=quality_score,
            preprocessing_steps=steps,
        )

    def _check_ocr_availability(self) -> bool:
        """Check if OCR libraries are available."""
        try:
            import pytesseract
            from PIL import Image

            return True
        except ImportError:
            logger.warning(
                "OCR libraries not available. Install pytesseract and Pillow for image text extraction."
            )
            return False

    def _extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image using OCR."""
        try:
            import pytesseract
            from PIL import Image

            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""

    def _clean_extracted_text(self, text: str) -> str:
        """Clean OCR-extracted text."""
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove common OCR artifacts
        text = re.sub(r"[^\w\s\.\,\!\?\:\;\-\(\)]", "", text)

        return text.strip()

    def _extract_visual_context(self, metadata: Optional[Dict[str, Any]]) -> str:
        """Extract visual context from image metadata."""
        if not metadata:
            return ""

        context_parts = []

        # Image dimensions
        if "width" in metadata and "height" in metadata:
            context_parts.append(
                f"Image dimensions: {metadata['width']}x{metadata['height']}"
            )

        # File format
        if "format" in metadata:
            context_parts.append(f"Format: {metadata['format']}")

        # Color information
        if "colors" in metadata:
            context_parts.append(f"Colors: {metadata['colors']}")

        return " | ".join(context_parts)

    def _calculate_image_quality(
        self, extracted_text: str, visual_context: str
    ) -> float:
        """Calculate image content quality."""
        # Text extraction success
        text_score = min(len(extracted_text.split()) / 50, 1.0)  # Normalize to 50 words

        # Visual context availability
        context_score = 1.0 if visual_context else 0.5

        # Combined score
        score = text_score * 0.7 + context_score * 0.3
        return max(0.0, min(1.0, score))


class PreprocessingPipeline:
    """Pipeline for content preprocessing."""

    def __init__(self):
        self.preprocessors = {
            "text": TextPreprocessor(),
            "code": CodePreprocessor(),
            "meeting": MeetingPreprocessor(),
            "image": ImagePreprocessor(),
        }

    def preprocess(
        self, content: str, content_type: str, metadata: Optional[Dict[str, Any]] = None
    ) -> PreprocessingResult:
        """Preprocess content using the appropriate preprocessor."""
        preprocessor = self.preprocessors.get(content_type)
        if not preprocessor:
            # Fallback to text preprocessor
            preprocessor = self.preprocessors["text"]
            logger.warning(
                f"No preprocessor found for content type '{content_type}', using text preprocessor"
            )

        return preprocessor.preprocess(content, metadata)

    def get_supported_types(self) -> List[str]:
        """Get list of supported content types."""
        return list(self.preprocessors.keys())

    def add_preprocessor(
        self, content_type: str, preprocessor: ContentPreprocessor
    ) -> None:
        """Add a custom preprocessor."""
        self.preprocessors[content_type] = preprocessor
        logger.info(f"Added custom preprocessor for content type: {content_type}")
