#!/usr/bin/env python3
"""Local test script to verify diagram generation works."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from diagram_server.analyzer import CodeAnalyzer
from diagram_server.diagram_builder import DiagramBuilder


def main():
    """Test the diagram generation locally."""
    analyzer = CodeAnalyzer()
    builder = DiagramBuilder()

    # Analyze the test example
    test_file = Path(__file__).parent / "test_example.py"
    print(f"Analyzing {test_file}...")

    analysis = analyzer.analyze_directory(str(test_file))

    print(f"\nFound {len(analysis.all_classes)} classes:")
    for class_name, class_info in analysis.all_classes.items():
        print(f"  - {class_name}")
        if class_info.base_classes:
            print(f"    Extends: {', '.join(class_info.base_classes)}")
        if class_info.is_enum:
            print(f"    Enum values: {', '.join(class_info.enum_values)}")
        print(f"    Methods: {len(class_info.methods)}")
        print(f"    Attributes: {len(class_info.attributes)}")

    # Generate UML diagram
    print("\nGenerating UML class diagram...")
    uml_diagram = builder.build_class_diagram(analysis)

    # Generate component diagram
    print("Generating component diagram...")
    component_diagram = builder.build_component_diagram(analysis)

    # Create output directory
    output_dir = Path.cwd() / "arch" / "diagrams"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save diagrams
    print(f"\nSaving diagrams to {output_dir}...")
    dot_path1, png_path1 = builder.render_and_save(uml_diagram, output_dir, "class_diagram")
    dot_path2, png_path2 = builder.render_and_save(component_diagram, output_dir, "component_diagram")

    print("\nSuccess! Generated files:")
    print(f"  - {dot_path1}")
    print(f"  - {png_path1}")
    print(f"  - {dot_path2}")
    print(f"  - {png_path2}")


if __name__ == "__main__":
    main()
