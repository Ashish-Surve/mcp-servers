"""Integration tests for diagram generation."""

import pytest
from pathlib import Path
import tempfile

from diagram_server.server.tools import DiagramTools


class TestIntegration:
    """Integration tests for the full diagram generation pipeline."""

    @pytest.fixture
    def tools(self):
        """Create a DiagramTools instance."""
        return DiagramTools()

    def test_uml_generation_flow(self, tools, fixtures_dir):
        """Test the complete UML diagram generation flow."""
        result = tools.generate_uml_diagram(str(fixtures_dir))

        assert "successfully" in result
        assert "classes" in result
        assert "files" in result.lower()

    def test_component_generation_flow(self, tools, fixtures_dir):
        """Test the complete component diagram generation flow."""
        result = tools.generate_component_diagram(str(fixtures_dir))

        assert "successfully" in result
        assert "modules" in result.lower()

    def test_analyze_codebase_flow(self, tools, fixtures_dir):
        """Test the codebase structure analysis flow."""
        import json

        result = tools.analyze_codebase_structure(str(fixtures_dir))

        # Should return valid JSON
        data = json.loads(result)
        assert "summary" in data
        assert "classes" in data
        assert "files" in data

    def test_render_custom_diagram(self, tools):
        """Test rendering a custom DOT diagram."""
        dot_content = '''
        digraph TestDiagram {
            A -> B;
            B -> C;
        }
        '''

        with tempfile.TemporaryDirectory() as tmpdir:
            result = tools.render_diagram_from_dot(dot_content, tmpdir, "test")

            assert "successfully" in result
            assert Path(tmpdir) / "test.dot"
            assert Path(tmpdir) / "test.png"
