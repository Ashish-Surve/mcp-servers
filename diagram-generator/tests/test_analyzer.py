"""Tests for code analyzer."""

import pytest
from pathlib import Path

from diagram_server.core.analyzer import CodeAnalyzer
from diagram_server.exceptions import InvalidPathError


class TestCodeAnalyzer:
    """Tests for CodeAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create a CodeAnalyzer instance."""
        return CodeAnalyzer()

    def test_analyze_file(self, analyzer, test_example_file):
        """Test analyzing a single Python file."""
        result = analyzer.analyze_python_file(str(test_example_file))

        assert result.file_path == str(test_example_file)
        assert len(result.classes) > 0
        assert result.module_name != ""

    def test_analyze_directory(self, analyzer, fixtures_dir):
        """Test analyzing a directory."""
        result = analyzer.analyze_directory(str(fixtures_dir))

        assert len(result.files) > 0
        assert len(result.all_classes) > 0

    def test_invalid_path(self, analyzer):
        """Test that invalid path raises error."""
        with pytest.raises(InvalidPathError):
            analyzer.analyze_directory("/nonexistent/path")

    def test_class_info_extraction(self, analyzer, test_example_file):
        """Test that class info is properly extracted."""
        result = analyzer.analyze_python_file(str(test_example_file))

        # Check that we found classes
        assert len(result.classes) > 0

        # Check that classes have methods and attributes
        for cls in result.classes:
            assert cls.name != ""
            # At least some classes should have methods or attributes
            if cls.name in ["Task", "Project", "TaskService"]:
                assert len(cls.methods) > 0 or len(cls.attributes) > 0
