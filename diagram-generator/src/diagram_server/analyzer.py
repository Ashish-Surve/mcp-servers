"""Code analysis module using tree-sitter for parsing Python code."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

# Use stderr for logging (stdout is reserved for MCP JSON-RPC)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ClassInfo:
    """Information about a Python class."""

    name: str
    base_classes: list[str] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    is_enum: bool = False
    enum_values: list[str] = field(default_factory=list)
    docstring: Optional[str] = None
    file_path: str = ""


@dataclass
class ImportInfo:
    """Information about imports in a file."""

    module: str
    names: list[str] = field(default_factory=list)
    is_from_import: bool = False


@dataclass
class FileAnalysis:
    """Analysis results for a single Python file."""

    file_path: str
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)
    module_name: str = ""


@dataclass
class CodebaseAnalysis:
    """Analysis results for an entire codebase."""

    files: list[FileAnalysis] = field(default_factory=list)
    all_classes: dict[str, ClassInfo] = field(default_factory=dict)
    module_dependencies: dict[str, set[str]] = field(default_factory=dict)


class CodeAnalyzer:
    """Analyzes Python code using tree-sitter."""

    def __init__(self):
        """Initialize the tree-sitter parser for Python."""
        self.parser = Parser(Language(tspython.language()))

    def analyze_directory(self, dirpath: str) -> CodebaseAnalysis:
        """
        Recursively analyze all Python files in a directory.

        Args:
            dirpath: Path to the directory to analyze

        Returns:
            CodebaseAnalysis containing all discovered classes and relationships
        """
        path = Path(dirpath)
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {dirpath}")

        analysis = CodebaseAnalysis()

        # Handle both files and directories
        if path.is_file() and path.suffix == ".py":
            python_files = [path]
        else:
            python_files = list(path.rglob("*.py"))

        logger.info(f"Found {len(python_files)} Python files to analyze")

        for py_file in python_files:
            try:
                file_analysis = self.analyze_python_file(str(py_file))
                analysis.files.append(file_analysis)

                # Build global class registry
                for cls in file_analysis.classes:
                    analysis.all_classes[cls.name] = cls

                # Track module dependencies
                if file_analysis.module_name:
                    deps = set()
                    for imp in file_analysis.imports:
                        deps.add(imp.module.split(".")[0])
                    analysis.module_dependencies[file_analysis.module_name] = deps

            except Exception as e:
                logger.warning(f"Failed to parse {py_file}: {e}")
                continue

        logger.info(f"Analyzed {len(analysis.files)} files, found {len(analysis.all_classes)} classes")
        return analysis

    def analyze_python_file(self, filepath: str) -> FileAnalysis:
        """
        Parse a Python file and extract classes, methods, and imports.

        Args:
            filepath: Path to the Python file

        Returns:
            FileAnalysis containing extracted information
        """
        with open(filepath, "rb") as f:
            source_code = f.read()

        tree = self.parser.parse(source_code)
        root_node = tree.root_node

        analysis = FileAnalysis(file_path=filepath)
        analysis.module_name = self._get_module_name(filepath)

        # Extract classes
        for node in self._find_nodes_by_type(root_node, "class_definition"):
            class_info = self._extract_class_info(node, source_code)
            if class_info:
                class_info.file_path = filepath
                analysis.classes.append(class_info)

        # Extract imports
        for node in self._find_nodes_by_type(root_node, "import_statement"):
            import_info = self._extract_import_info(node, source_code)
            if import_info:
                analysis.imports.append(import_info)

        for node in self._find_nodes_by_type(root_node, "import_from_statement"):
            import_info = self._extract_import_info(node, source_code, is_from=True)
            if import_info:
                analysis.imports.append(import_info)

        return analysis

    def _get_module_name(self, filepath: str) -> str:
        """Extract module name from file path."""
        path = Path(filepath)
        # Remove .py extension and convert to module notation
        parts = path.with_suffix("").parts
        # Find index of 'src' or use all parts
        try:
            src_idx = parts.index("src") + 1
            return ".".join(parts[src_idx:])
        except ValueError:
            return path.stem

    def _find_nodes_by_type(self, node, node_type: str):
        """Recursively find all nodes of a given type."""
        if node.type == node_type:
            yield node

        for child in node.children:
            yield from self._find_nodes_by_type(child, node_type)

    def _extract_class_info(self, node, source_code: bytes) -> Optional[ClassInfo]:
        """Extract information from a class definition node."""
        # Get class name
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        class_name = source_code[name_node.start_byte : name_node.end_byte].decode("utf-8")

        class_info = ClassInfo(name=class_name)

        # Extract base classes
        bases_node = node.child_by_field_name("superclasses")
        if bases_node:
            for arg_node in self._find_nodes_by_type(bases_node, "identifier"):
                base_name = source_code[arg_node.start_byte : arg_node.end_byte].decode("utf-8")
                class_info.base_classes.append(base_name)

            # Check if it's an Enum
            if "Enum" in class_info.base_classes:
                class_info.is_enum = True

        # Extract class body
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                if child.type == "function_definition":
                    method_info = self._extract_method_info(child, source_code)
                    if method_info:
                        class_info.methods.append(method_info)

                        # Extract attributes from __init__
                        if method_info.startswith("__init__"):
                            attrs = self._extract_init_attributes(child, source_code)
                            class_info.attributes.extend(attrs)

                elif child.type == "expression_statement":
                    # Class-level assignments (including Enum values)
                    attr = self._extract_assignment(child, source_code)
                    if attr:
                        if class_info.is_enum:
                            class_info.enum_values.append(attr)
                        else:
                            class_info.attributes.append(attr)

                elif child.type == "expression_statement" and child.children:
                    # String literal (docstring)
                    if child.children[0].type == "string":
                        docstring = source_code[child.start_byte : child.end_byte].decode("utf-8")
                        class_info.docstring = docstring.strip('"\'')

        return class_info

    def _extract_method_info(self, node, source_code: bytes) -> Optional[str]:
        """Extract method name and parameters."""
        name_node = node.child_by_field_name("name")
        if not name_node:
            return None

        method_name = source_code[name_node.start_byte : name_node.end_byte].decode("utf-8")

        # Get parameters
        params_node = node.child_by_field_name("parameters")
        if params_node:
            params_str = source_code[params_node.start_byte : params_node.end_byte].decode("utf-8")
            return f"{method_name}{params_str}"

        return f"{method_name}()"

    def _extract_init_attributes(self, node, source_code: bytes) -> list[str]:
        """Extract self.attribute assignments from __init__ method."""
        attributes = []
        body_node = node.child_by_field_name("body")
        if not body_node:
            return attributes

        for child in body_node.children:
            if child.type == "expression_statement":
                # Look for self.attr = value patterns
                for assign_node in self._find_nodes_by_type(child, "assignment"):
                    left_node = assign_node.child_by_field_name("left")
                    if left_node and left_node.type == "attribute":
                        obj_node = left_node.child_by_field_name("object")
                        attr_node = left_node.child_by_field_name("attribute")

                        if obj_node and attr_node:
                            obj_name = source_code[obj_node.start_byte : obj_node.end_byte].decode("utf-8")
                            attr_name = source_code[attr_node.start_byte : attr_node.end_byte].decode("utf-8")

                            if obj_name == "self":
                                # Try to get type annotation
                                type_annotation = self._get_type_annotation(assign_node, source_code)
                                if type_annotation:
                                    attributes.append(f"{attr_name}: {type_annotation}")
                                else:
                                    attributes.append(attr_name)

        return attributes

    def _get_type_annotation(self, node, source_code: bytes) -> Optional[str]:
        """Try to extract type annotation from assignment."""
        # This is a simplified version - tree-sitter can extract more detailed type info
        right_node = node.child_by_field_name("right")
        if right_node:
            # Check for typed expressions
            for type_node in self._find_nodes_by_type(right_node, "type"):
                return source_code[type_node.start_byte : type_node.end_byte].decode("utf-8")
        return None

    def _extract_assignment(self, node, source_code: bytes) -> Optional[str]:
        """Extract variable name from assignment statement."""
        for assign_node in self._find_nodes_by_type(node, "assignment"):
            left_node = assign_node.child_by_field_name("left")
            if left_node and left_node.type == "identifier":
                var_name = source_code[left_node.start_byte : left_node.end_byte].decode("utf-8")
                return var_name
        return None

    def _extract_import_info(self, node, source_code: bytes, is_from: bool = False) -> Optional[ImportInfo]:
        """Extract import information."""
        if is_from:
            # from module import name1, name2
            module_node = node.child_by_field_name("module_name")
            if not module_node:
                return None

            module_name = source_code[module_node.start_byte : module_node.end_byte].decode("utf-8")
            import_info = ImportInfo(module=module_name, is_from_import=True)

            # Extract imported names
            for name_node in self._find_nodes_by_type(node, "dotted_name"):
                if name_node.parent == node:  # Direct child
                    name = source_code[name_node.start_byte : name_node.end_byte].decode("utf-8")
                    import_info.names.append(name)

            return import_info
        else:
            # import module
            for dotted_name_node in self._find_nodes_by_type(node, "dotted_name"):
                module_name = source_code[dotted_name_node.start_byte : dotted_name_node.end_byte].decode("utf-8")
                return ImportInfo(module=module_name, is_from_import=False)

        return None
