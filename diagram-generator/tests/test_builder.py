"""Tests for diagram builder."""

import pytest
from pathlib import Path
import tempfile

from diagram_server.core.analyzer import CodeAnalyzer
from diagram_server.core.builder import DiagramBuilder
from diagram_server.core.models import CodebaseAnalysis, ClassInfo


class TestDiagramBuilder:
    """Tests for DiagramBuilder class."""

    @pytest.fixture
    def builder(self):
        """Create a DiagramBuilder instance."""
        return DiagramBuilder()

    @pytest.fixture
    def analyzer(self):
        """Create a CodeAnalyzer instance."""
        return CodeAnalyzer()

    @pytest.fixture
    def sample_analysis(self, analyzer, test_example_file):
        """Create a sample codebase analysis."""
        return analyzer.analyze_python_file(str(test_example_file))

    def test_build_class_diagram(self, builder, analyzer, fixtures_dir):
        """Test building a class diagram."""
        analysis = analyzer.analyze_directory(str(fixtures_dir))
        diagram = builder.build_class_diagram(analysis)

        assert diagram is not None
        assert "UML_Class_Diagram" in str(diagram)

    def test_build_component_diagram(self, builder, analyzer, fixtures_dir):
        """Test building a component diagram."""
        analysis = analyzer.analyze_directory(str(fixtures_dir))
        diagram = builder.build_component_diagram(analysis)

        assert diagram is not None
        assert "Component_Diagram" in str(diagram)

    def test_render_and_save(self, builder, analyzer, fixtures_dir):
        """Test rendering and saving diagram."""
        analysis = analyzer.analyze_directory(str(fixtures_dir))
        diagram = builder.build_class_diagram(analysis)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            dot_path, png_path = builder.render_and_save(diagram, output_dir, "test_diagram")

            assert Path(dot_path).exists()
            assert Path(png_path).exists()
            assert dot_path.endswith(".dot")
            assert png_path.endswith(".png")
