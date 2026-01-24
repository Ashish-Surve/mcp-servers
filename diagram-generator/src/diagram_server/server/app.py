"""MCP server application for diagram generation."""

from mcp.server.fastmcp import FastMCP

from ..utils.logging import get_logger, setup_logging
from .tools import DiagramTools

# Configure logging
setup_logging()
logger = get_logger(__name__)

# Initialize MCP server
mcp = FastMCP("diagram-generator")

# Initialize tools
tools = DiagramTools()


@mcp.tool()
def generate_uml_diagram(path: str, layout: str = "LR") -> str:
    """Generate UML class diagram from Python codebase.

    Analyzes Python files to extract classes, methods, attributes, inheritance,
    and relationships. Creates arch/diagrams/ directory and saves both
    class_diagram.dot and class_diagram.png.

    Args:
        path: Absolute path to codebase directory or file to analyze
        layout: Diagram layout direction - "LR" (left-right, horizontal) or "TB" (top-bottom, vertical). Default: "LR"

    Returns:
        Message with paths to generated diagram files
    """
    return tools.generate_uml_diagram(path, layout)


@mcp.tool()
def generate_component_diagram(path: str) -> str:
    """Generate component/architecture diagram from Python codebase.

    Analyzes directory structure and imports to identify components and their
    dependencies. Creates arch/diagrams/ directory and saves both
    component_diagram.dot and component_diagram.png.

    Args:
        path: Absolute path to codebase directory to analyze

    Returns:
        Message with paths to generated diagram files
    """
    return tools.generate_component_diagram(path)


@mcp.tool()
def analyze_codebase_structure(path: str) -> str:
    """Analyze Python codebase structure and return as JSON for LLM processing.

    This tool extracts the raw structure (classes, methods, dependencies) and returns
    it as structured data. The LLM can then interpret this data, identify patterns,
    and decide what relationships matter for visualization.

    Use this when you want intelligent, context-aware diagram generation where the
    LLM decides what to show and how to organize it.

    Args:
        path: Absolute path to codebase directory to analyze

    Returns:
        JSON string containing codebase structure with classes, methods, attributes,
        inheritance, imports, and file organization
    """
    return tools.analyze_codebase_structure(path)


@mcp.tool()
def render_diagram_from_dot(
    dot_content: str, output_path: str, filename: str = "custom_diagram"
) -> str:
    """Render a Graphviz diagram from DOT language specification.

    This tool allows the LLM to generate custom diagrams by providing the DOT language
    specification directly. The LLM can create any type of diagram (UML, architecture,
    flow charts, etc.) and this tool will render it.

    Args:
        dot_content: Complete DOT language specification for the diagram
        output_path: Directory where diagram files should be saved
        filename: Base name for output files (without extension)

    Returns:
        Message with paths to generated diagram files
    """
    return tools.render_diagram_from_dot(dot_content, output_path, filename)


@mcp.prompt()
def create_intelligent_diagram():
    """Guide for using LLM-driven diagram generation.

    This prompt helps the LLM create intelligent, context-aware diagrams by:
    1. Analyzing the codebase structure
    2. Identifying key patterns and relationships
    3. Generating appropriate DOT specifications
    4. Rendering beautiful, informative diagrams
    """
    return {
        "messages": [
            {
                "role": "user",
                "content": """I want to create an intelligent diagram of a codebase. Please help me by:

1. **Analyze the Structure**: Use `analyze_codebase_structure(path)` to get the complete codebase structure as JSON.

2. **Understand the Architecture**: Review the structure and identify:
   - Key architectural patterns (MVC, layered, microservices, etc.)
   - Main component groups (models, controllers, services, utilities, etc.)
   - Important relationships (inheritance, composition, dependencies)
   - Design patterns being used

3. **Decide What to Show**: Based on the analysis, determine:
   - What level of detail is appropriate (high-level vs detailed)
   - Which classes/modules are central vs peripheral
   - How to group related components
   - What relationships matter most

4. **Generate DOT Specification**: Create a Graphviz DOT language specification that:
   - Uses appropriate layout (LR for horizontal, TB for vertical)
   - Groups related components in clusters/subgraphs
   - Uses different styles for different component types
   - Shows key relationships with appropriate arrows
   - Includes meaningful labels and colors

5. **Render the Diagram**: Use `render_diagram_from_dot(dot_content, output_path, filename)` to create the final diagram.

Example DOT structure:
```dot
digraph Architecture {
    rankdir=LR;
    node [shape=box];

    subgraph cluster_models {
        label="Data Models";
        style=filled;
        color=lightblue;
        User; Product; Order;
    }

    subgraph cluster_services {
        label="Business Logic";
        style=filled;
        color=lightgreen;
        UserService; OrderService;
    }

    UserService -> User [label="uses"];
    OrderService -> Order [label="manages"];
}
```

Ask the user for the project path to begin!""",
            }
        ]
    }


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting diagram-generator MCP server")
    mcp.run(transport="stdio")
