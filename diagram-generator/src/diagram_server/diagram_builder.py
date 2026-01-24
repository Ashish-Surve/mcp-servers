"""Diagram generation module using Graphviz."""

import logging
from pathlib import Path

from graphviz import Digraph

from .analyzer import ClassInfo, CodebaseAnalysis

logger = logging.getLogger(__name__)


class DiagramBuilder:
    """Builds UML and component diagrams using Graphviz."""

    def build_class_diagram(self, analysis: CodebaseAnalysis) -> Digraph:
        """
        Create a UML class diagram from codebase analysis.

        Args:
            analysis: CodebaseAnalysis containing classes and relationships

        Returns:
            Graphviz Digraph object
        """
        dot = Digraph("UML_Class_Diagram", comment="UML Class Diagram")

        # Graph settings
        dot.attr(rankdir="TB", splines="spline", nodesep="0.5", ranksep="1.0")
        dot.attr("node", fontname="Helvetica", fontsize="10")
        dot.attr("edge", fontname="Helvetica", fontsize="9")
        dot.attr(
            label="UML Class Diagram",
            labelloc="t",
            fontsize="16",
            fontname="Helvetica-Bold",
        )

        # Categorize classes
        enums = []
        regular_classes = []

        for class_name, class_info in analysis.all_classes.items():
            if class_info.is_enum:
                enums.append(class_info)
            else:
                regular_classes.append(class_info)

        # Create enum nodes
        if enums:
            with dot.subgraph(name="cluster_enums") as c:
                c.attr(label="Enumerations", style="dashed", color="green")
                for enum_info in enums:
                    self._create_enum_node(c, enum_info)

        # Create regular class nodes
        if regular_classes:
            with dot.subgraph(name="cluster_classes") as c:
                c.attr(label="Classes", style="dashed", color="blue")
                for class_info in regular_classes:
                    self._create_class_node(c, class_info)

        # Add relationships
        for class_info in regular_classes:
            # Inheritance relationships
            for base_class in class_info.base_classes:
                if base_class in analysis.all_classes and base_class != "Enum":
                    dot.edge(
                        class_info.name,
                        base_class,
                        arrowhead="onormal",
                        label="extends",
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

        return dot

    def build_component_diagram(self, analysis: CodebaseAnalysis) -> Digraph:
        """
        Create a component diagram from codebase analysis.

        Args:
            analysis: CodebaseAnalysis containing module dependencies

        Returns:
            Graphviz Digraph object
        """
        dot = Digraph("Component_Diagram", comment="Component Architecture Diagram")

        # Graph settings
        dot.attr(rankdir="TB", splines="spline", nodesep="0.8", ranksep="1.2")
        dot.attr("node", fontname="Helvetica", fontsize="11", shape="component")
        dot.attr("edge", fontname="Helvetica", fontsize="9")
        dot.attr(
            label="Component Architecture Diagram",
            labelloc="t",
            fontsize="16",
            fontname="Helvetica-Bold",
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
                    style="filled",
                    fillcolor="#E6F3FF",
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

    def _create_class_node(
        self,
        graph: Digraph,
        class_info: ClassInfo,
        fillcolor: str = "#FEFECE",
    ):
        """Create a UML class node with attributes and methods."""
        # Build the label using HTML-like syntax for record shape
        stereotype = ""

        # Format attributes
        attr_section = "\\l".join(class_info.attributes) + "\\l" if class_info.attributes else ""

        # Format methods (limit to public methods for clarity)
        methods = [m for m in class_info.methods if not m.startswith("_") or m.startswith("__init__")]
        method_section = "\\l".join(methods[:10]) + "\\l" if methods else ""  # Limit to 10 methods

        # Create label with compartments
        if attr_section and method_section:
            label = f"{{{stereotype}{class_info.name}|{attr_section}|{method_section}}}"
        elif attr_section:
            label = f"{{{stereotype}{class_info.name}|{attr_section}}}"
        elif method_section:
            label = f"{{{stereotype}{class_info.name}||{method_section}}}"
        else:
            label = f"{{{stereotype}{class_info.name}}}"

        graph.node(
            class_info.name,
            label=label,
            shape="record",
            style="filled",
            fillcolor=fillcolor,
        )

    def _create_enum_node(
        self,
        graph: Digraph,
        enum_info: ClassInfo,
        fillcolor: str = "#DDFFDD",
    ):
        """Create a UML enumeration node."""
        values_section = "\\l".join(enum_info.enum_values) + "\\l" if enum_info.enum_values else ""
        label = f"{{«enum»\\n{enum_info.name}|{values_section}}}"

        graph.node(
            enum_info.name,
            label=label,
            shape="record",
            style="filled",
            fillcolor=fillcolor,
        )

    def render_and_save(
        self,
        graph: Digraph,
        output_dir: Path,
        base_name: str,
    ) -> tuple[str, str]:
        """
        Render and save diagram to both .dot and .png formats.

        Args:
            graph: Graphviz Digraph to render
            output_dir: Directory to save files
            base_name: Base name for output files (without extension)

        Returns:
            Tuple of (dot_path, png_path)
        """
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
