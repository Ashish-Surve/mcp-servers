"""MCP server for diagram generation."""

import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .analyzer import CodeAnalyzer
from .diagram_builder import DiagramBuilder

# Configure logging to stderr only
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("diagram-generator")

# Initialize analyzer and builder
analyzer = CodeAnalyzer()
builder = DiagramBuilder()


@mcp.tool()
def generate_uml_diagram(path: str) -> str:
    """
    Generate UML class diagram from Python codebase.

    Analyzes Python files to extract classes, methods, attributes, inheritance,
    and relationships. Creates arch/diagrams/ directory and saves both
    class_diagram.dot and class_diagram.png.

    Args:
        path: Absolute path to codebase directory or file to analyze

    Returns:
        Message with paths to generated diagram files
    """
    try:
        logger.info(f"Analyzing codebase at: {path}")

        # Analyze the codebase
        analysis = analyzer.analyze_directory(path)

        if not analysis.all_classes:
            return f"No classes found in {path}. Make sure the path contains Python files with class definitions."

        # Build the diagram
        diagram = builder.build_class_diagram(analysis)

        # Create output directory
        output_dir = Path.cwd() / "arch" / "diagrams"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save diagram
        dot_path, png_path = builder.render_and_save(diagram, output_dir, "class_diagram")

        result = f"""UML class diagram generated successfully!

Found:
- {len(analysis.all_classes)} classes
- {len(analysis.files)} Python files analyzed

Output files:
- {dot_path}
- {png_path}

The diagram includes:
- Class definitions with attributes and methods
- Inheritance relationships
- Enum types
"""
        logger.info("UML diagram generation completed")
        return result

    except FileNotFoundError as e:
        error_msg = f"Error: {e}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Failed to generate UML diagram: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg


@mcp.tool()
def generate_component_diagram(path: str) -> str:
    """
    Generate component/architecture diagram from Python codebase.

    Analyzes directory structure and imports to identify components and their
    dependencies. Creates arch/diagrams/ directory and saves both
    component_diagram.dot and component_diagram.png.

    Args:
        path: Absolute path to codebase directory to analyze

    Returns:
        Message with paths to generated diagram files
    """
    try:
        logger.info(f"Analyzing codebase structure at: {path}")

        # Analyze the codebase
        analysis = analyzer.analyze_directory(path)

        if not analysis.files:
            return f"No Python files found in {path}."

        # Build the diagram
        diagram = builder.build_component_diagram(analysis)

        # Create output directory
        output_dir = Path.cwd() / "arch" / "diagrams"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save diagram
        dot_path, png_path = builder.render_and_save(diagram, output_dir, "component_diagram")

        # Count unique modules
        modules = set()
        for file_analysis in analysis.files:
            module_parts = file_analysis.module_name.split(".")
            if module_parts:
                modules.add(module_parts[0])

        result = f"""Component diagram generated successfully!

Found:
- {len(modules)} top-level modules
- {len(analysis.files)} Python files analyzed
- {len(analysis.module_dependencies)} module dependencies

Output files:
- {dot_path}
- {png_path}

The diagram shows:
- Component organization by module
- Import dependencies between modules
"""
        logger.info("Component diagram generation completed")
        return result

    except FileNotFoundError as e:
        error_msg = f"Error: {e}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Failed to generate component diagram: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg


def main():
    """Run the MCP server."""
    logger.info("Starting diagram-generator MCP server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
