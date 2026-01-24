"""Diagram generation module using Graphviz."""

from collections import defaultdict
from pathlib import Path

from graphviz import Digraph

from ..config import (
    DIAGRAM_STYLES,
    FONT_NAME,
    FONT_NAME_BOLD,
    FONT_SIZE_EDGE,
    FONT_SIZE_NODE,
    FONT_SIZE_TITLE,
    GRAPH_ATTRS,
    LAYOUT_HORIZONTAL,
    MAX_METHODS_DISPLAY,
    SKIP_BASE_CLASSES,
)
from ..exceptions import DiagramBuildError, RenderError
from ..utils.logging import get_logger
from ..utils.paths import get_module_from_path
from .models import ClassInfo, CodebaseAnalysis

logger = get_logger(__name__)


class DiagramBuilder:
    """Builds UML and component diagrams using Graphviz."""

    def build_class_diagram(
        self, analysis: CodebaseAnalysis, layout: str = LAYOUT_HORIZONTAL
    ) -> Digraph:
        """Create a UML class diagram from codebase analysis.

        Args:
            analysis: CodebaseAnalysis containing classes and relationships
            layout: Layout direction (LR for horizontal, TB for vertical)

        Returns:
            Graphviz Digraph object

        Raises:
            DiagramBuildError: If diagram creation fails
        """
        try:
            dot = Digraph("UML_Class_Diagram", comment="UML Class Diagram")

            # Graph settings for better layout
            dot.attr(rankdir=layout, **GRAPH_ATTRS['class_diagram'])
            dot.attr("node", fontname=FONT_NAME, fontsize=FONT_SIZE_NODE, margin="0.2,0.1")
            dot.attr("edge", fontname=FONT_NAME, fontsize=FONT_SIZE_EDGE)
            dot.attr(
                label="UML Class Diagram",
                labelloc="t",
                fontsize=FONT_SIZE_TITLE,
                fontname=FONT_NAME_BOLD,
            )

            # Categorize classes by module and type
            enums = []
            classes_by_module = defaultdict(list)

            for class_name, class_info in analysis.all_classes.items():
                if class_info.is_enum:
                    enums.append(class_info)
                else:
                    # Group by module/package
                    module = get_module_from_path(class_info.file_path)
                    classes_by_module[module].append(class_info)

            # Create enum nodes (if any)
            if enums:
                with dot.subgraph(name="cluster_enums") as c:
                    c.attr(label="Enums", **DIAGRAM_STYLES['enum_cluster'])
                    for enum_info in enums:
                        self._create_enum_node(c, enum_info)

            # Create class nodes grouped by module
            for idx, (module, classes) in enumerate(sorted(classes_by_module.items())):
                # Only create subgraph if there are multiple modules
                if len(classes_by_module) > 1:
                    with dot.subgraph(name=f"cluster_{idx}") as c:
                        c.attr(label=module or "Main", **DIAGRAM_STYLES['module_cluster'])
                        for class_info in classes:
                            self._create_class_node(c, class_info)
                else:
                    # Single module - no need for clustering
                    for class_info in classes:
                        self._create_class_node(dot, class_info)

            # Collect all regular classes for relationship drawing
            all_regular_classes = []
            for classes in classes_by_module.values():
                all_regular_classes.extend(classes)

            # Add relationships
            self._add_class_relationships(dot, all_regular_classes, enums, analysis)

            return dot

        except Exception as e:
            raise DiagramBuildError(f"Failed to build class diagram: {e}") from e

    def _add_class_relationships(
        self,
        dot: Digraph,
        all_classes: list[ClassInfo],
        enums: list[ClassInfo],
        analysis: CodebaseAnalysis,
    ) -> None:
        """Add inheritance and composition relationships to the diagram.

        Args:
            dot: Graphviz diagram to add relationships to
            all_classes: List of all regular classes
            enums: List of all enum classes
            analysis: Complete codebase analysis
        """
        for class_info in all_classes:
            # Inheritance relationships
            for base_class in class_info.base_classes:
                # Skip common base classes that clutter the diagram
                if base_class in SKIP_BASE_CLASSES:
                    continue

                # If base class is in the codebase, draw the relationship
                if base_class in analysis.all_classes:
                    dot.edge(
                        class_info.name,
                        base_class,
                        arrowhead="onormal",
                        label="extends",
                    )
                # For external base classes, create a stub node and show the relationship
                else:
                    # Create external class node (shown in gray/italics)
                    dot.node(
                        base_class,
                        label=f"«external»\\n{base_class}",
                        **DIAGRAM_STYLES['external'],
                    )
                    dot.edge(
                        class_info.name,
                        base_class,
                        arrowhead="onormal",
                        label="extends",
                        style="dashed",
                    )

            # Enum usage (check if any attributes reference enums)
            for enum_info in enums:
                # Simple heuristic: if enum name appears in attributes, draw association
                for attr in class_info.attributes:
                    if enum_info.name in attr:
                        dot.edge(
                            class_info.name,
                            enum_info.name,
                            style="dotted",
                            arrowhead="vee",
                        )
                        break

    def build_component_diagram(self, analysis: CodebaseAnalysis) -> Digraph:
        """Create a component diagram from codebase analysis.

        Args:
            analysis: CodebaseAnalysis containing module dependencies

        Returns:
            Graphviz Digraph object

        Raises:
            DiagramBuildError: If diagram creation fails
        """
        try:
            dot = Digraph("Component_Diagram", comment="Component Architecture Diagram")

            # Graph settings
            dot.attr(rankdir="TB", **GRAPH_ATTRS['component_diagram'])
            dot.attr("node", fontname=FONT_NAME, fontsize="11", shape="component")
            dot.attr("edge", fontname=FONT_NAME, fontsize=FONT_SIZE_EDGE)
            dot.attr(
                label="Component Architecture Diagram",
                labelloc="t",
                fontsize=FONT_SIZE_TITLE,
                fontname=FONT_NAME_BOLD,
            )

            # Group files by top-level module
            modules = {}
            for file_analysis in analysis.files:
                module_parts = file_analysis.module_name.split(".")
                if module_parts:
                    top_level = module_parts[0]
                    if top_level not in modules:
                        modules[top_level] = []
                    modules[top_level].append(file_analysis)

            # Create component nodes grouped by module
            for module_name, files in modules.items():
                with dot.subgraph(name=f"cluster_{module_name}") as c:
                    c.attr(
                        label=f"{module_name.title()} Module",
                        **DIAGRAM_STYLES['component_cluster'],
                    )

                    for file_analysis in files:
                        component_name = file_analysis.module_name
                        # Count classes in this file
                        class_count = len(file_analysis.classes)
                        label = f"{Path(file_analysis.file_path).stem}\\n({class_count} classes)"
                        c.node(component_name, label, shape="component")

            # Add dependency edges
            for module_name, deps in analysis.module_dependencies.items():
                for dep in deps:
                    # Only draw edges for internal dependencies
                    if dep in modules and dep != module_name.split(".")[0]:
                        dot.edge(module_name, dep, label="imports")

            return dot

        except Exception as e:
            raise DiagramBuildError(f"Failed to build component diagram: {e}") from e

    def _create_class_node(
        self,
        graph: Digraph,
        class_info: ClassInfo,
    ) -> None:
        """Create a UML class node with attributes and methods.

        Args:
            graph: Graphviz diagram to add node to
            class_info: Class information to visualize
        """
        # Format attributes
        attr_section = (
            "\\l".join(class_info.attributes) + "\\l" if class_info.attributes else ""
        )

        # Format methods (limit to public methods for clarity)
        methods = [
            m for m in class_info.methods if not m.startswith("_") or m.startswith("__init__")
        ]
        method_section = (
            "\\l".join(methods[:MAX_METHODS_DISPLAY]) + "\\l" if methods else ""
        )  # Limit display

        # Create label with compartments
        if attr_section and method_section:
            label = f"{{{class_info.name}|{attr_section}|{method_section}}}"
        elif attr_section:
            label = f"{{{class_info.name}|{attr_section}}}"
        elif method_section:
            label = f"{{{class_info.name}||{method_section}}}"
        else:
            label = f"{{{class_info.name}}}"

        graph.node(class_info.name, label=label, **DIAGRAM_STYLES['class'])

    def _create_enum_node(
        self,
        graph: Digraph,
        enum_info: ClassInfo,
    ) -> None:
        """Create a UML enumeration node.

        Args:
            graph: Graphviz diagram to add node to
            enum_info: Enum class information to visualize
        """
        values_section = (
            "\\l".join(enum_info.enum_values) + "\\l" if enum_info.enum_values else ""
        )
        label = f"{{«enum»\\n{enum_info.name}|{values_section}}}"

        graph.node(enum_info.name, label=label, **DIAGRAM_STYLES['enum'])

    def render_and_save(
        self,
        graph: Digraph,
        output_dir: Path,
        base_name: str,
    ) -> tuple[str, str]:
        """Render and save diagram to both .dot and .png formats.

        Args:
            graph: Graphviz Digraph to render
            output_dir: Directory to save files
            base_name: Base name for output files (without extension)

        Returns:
            Tuple of (dot_path, png_path)

        Raises:
            RenderError: If rendering fails
        """
        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save .dot file
            dot_path = output_dir / f"{base_name}.dot"
            graph.save(str(dot_path))

            # Render .png file
            png_path = output_dir / f"{base_name}.png"
            graph.render(
                str(output_dir / base_name),
                format="png",
                cleanup=True,  # Remove intermediate files
            )

            logger.info(f"Saved diagram to {dot_path} and {png_path}")
            return str(dot_path), str(png_path)

        except Exception as e:
            raise RenderError(f"Failed to render diagram: {e}") from e
