"""MCP tool implementations for diagram generation."""

import json
from pathlib import Path

from ..config import DEFAULT_OUTPUT_DIR, LAYOUT_HORIZONTAL
from ..core.analyzer import CodeAnalyzer
from ..core.builder import DiagramBuilder
from ..exceptions import NoClassesFoundError, NoPythonFilesFoundError
from ..utils.logging import get_logger
from ..utils.paths import get_project_root, resolve_project_path

logger = get_logger(__name__)


class DiagramTools:
    """MCP tools for diagram generation."""

    def __init__(self) -> None:
        """Initialize analyzer and builder instances."""
        self.analyzer = CodeAnalyzer()
        self.builder = DiagramBuilder()

    def generate_uml_diagram(self, path: str, layout: str = LAYOUT_HORIZONTAL) -> str:
        """Generate UML class diagram from Python codebase.

        Analyzes Python files to extract classes, methods, attributes, inheritance,
        and relationships. Creates arch/diagrams/ directory and saves both
        class_diagram.dot and class_diagram.png.

        Args:
            path: Absolute path to codebase directory or file to analyze
            layout: Diagram layout direction - "LR" (left-right, horizontal) or "TB" (top-bottom, vertical)

        Returns:
            Message with paths to generated diagram files
        """
        try:
            logger.info(f"Analyzing codebase at: {path}")

            # Analyze the codebase
            analysis = self.analyzer.analyze_directory(path)

            if not analysis.all_classes:
                raise NoClassesFoundError(
                    f"No classes found in {path}. Make sure the path contains Python files with class definitions."
                )

            # Build the diagram
            diagram = self.builder.build_class_diagram(analysis, layout=layout)

            # Create output directory in the analyzed project's directory
            project_path = resolve_project_path(path)
            project_root = get_project_root(project_path)
            output_dir = project_root / DEFAULT_OUTPUT_DIR

            # Save diagram
            dot_path, png_path = self.builder.render_and_save(diagram, output_dir, "class_diagram")

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

        except (NoClassesFoundError, FileNotFoundError) as e:
            error_msg = f"Error: {e}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Failed to generate UML diagram: {e}"
            logger.error(error_msg, exc_info=True)
            return error_msg

    def generate_component_diagram(self, path: str) -> str:
        """Generate component/architecture diagram from Python codebase.

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
            analysis = self.analyzer.analyze_directory(path)

            if not analysis.files:
                raise NoPythonFilesFoundError(f"No Python files found in {path}.")

            # Build the diagram
            diagram = self.builder.build_component_diagram(analysis)

            # Create output directory in the analyzed project's directory
            project_path = resolve_project_path(path)
            project_root = get_project_root(project_path)
            output_dir = project_root / DEFAULT_OUTPUT_DIR

            # Save diagram
            dot_path, png_path = self.builder.render_and_save(
                diagram, output_dir, "component_diagram"
            )

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

        except (NoPythonFilesFoundError, FileNotFoundError) as e:
            error_msg = f"Error: {e}"
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Failed to generate component diagram: {e}"
            logger.error(error_msg, exc_info=True)
            return error_msg

    def analyze_codebase_structure(self, path: str) -> str:
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
        try:
            logger.info(f"Analyzing codebase structure at: {path}")

            # Analyze the codebase
            analysis = self.analyzer.analyze_directory(path)

            if not analysis.all_classes and not analysis.files:
                return json.dumps(
                    {"error": f"No Python files found in {path}", "files_found": 0, "classes_found": 0}
                )

            # Convert to JSON-serializable format
            structure = {
                "summary": {
                    "total_files": len(analysis.files),
                    "total_classes": len(analysis.all_classes),
                    "modules": list(analysis.module_dependencies.keys()),
                },
                "classes": {},
                "files": [],
                "dependencies": {},
            }

            # Add class information
            for class_name, class_info in analysis.all_classes.items():
                structure["classes"][class_name] = {
                    "name": class_info.name,
                    "file_path": class_info.file_path,
                    "base_classes": class_info.base_classes,
                    "attributes": class_info.attributes,
                    "methods": class_info.methods,
                    "is_enum": class_info.is_enum,
                    "enum_values": class_info.enum_values if class_info.is_enum else [],
                    "docstring": class_info.docstring,
                }

            # Add file information
            for file_analysis in analysis.files:
                structure["files"].append(
                    {
                        "path": file_analysis.file_path,
                        "module_name": file_analysis.module_name,
                        "classes": [cls.name for cls in file_analysis.classes],
                        "imports": [
                            {
                                "module": imp.module,
                                "names": imp.names,
                                "is_from_import": imp.is_from_import,
                            }
                            for imp in file_analysis.imports
                        ],
                    }
                )

            # Add module dependencies
            for module, deps in analysis.module_dependencies.items():
                structure["dependencies"][module] = list(deps)

            logger.info(
                f"Structure analysis complete: {len(analysis.all_classes)} classes in {len(analysis.files)} files"
            )
            return json.dumps(structure, indent=2)

        except FileNotFoundError as e:
            error_msg = f"Error: {e}"
            logger.error(error_msg)
            return json.dumps({"error": error_msg})
        except Exception as e:
            error_msg = f"Failed to analyze codebase structure: {e}"
            logger.error(error_msg, exc_info=True)
            return json.dumps({"error": error_msg})

    def render_diagram_from_dot(
        self, dot_content: str, output_path: str, filename: str = "custom_diagram"
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
        try:
            from graphviz import Source

            logger.info(f"Rendering custom diagram to: {output_path}/{filename}")

            # Create output directory
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Create diagram from DOT content
            dot = Source(dot_content)

            # Save DOT file
            dot_path = output_dir / f"{filename}.dot"
            with open(dot_path, "w") as f:
                f.write(dot_content)

            # Render to PNG
            png_path = output_dir / f"{filename}.png"
            dot.render(filename=str(output_dir / filename), format="png", cleanup=True)

            result = f"""Custom diagram rendered successfully!

Output files:
- {dot_path}
- {png_path}

The diagram has been generated from the provided DOT specification."""

            logger.info("Custom diagram rendering completed")
            return result

        except Exception as e:
            error_msg = f"Failed to render diagram: {e}"
            logger.error(error_msg, exc_info=True)
            return error_msg
