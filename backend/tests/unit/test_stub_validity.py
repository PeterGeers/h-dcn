"""
Property-Based Test: Generated test stubs are valid and importable

Verifies that each of the 10 generated backend test stub files:
1. Parses without syntax errors (compiles)
2. Imports its corresponding handler module
3. Contains at least one function whose name starts with `test_`

**Validates: Requirements 4.3**
"""

import ast
import importlib
import importlib.util
import sys
import os

import pytest
from hypothesis import given, settings, note
from hypothesis import strategies as st


# --- Setup: ensure paths are correct ---
_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_tests_unit_dir = os.path.join(_backend_dir, "tests", "unit")
_layers_path = os.path.join(_backend_dir, "layers", "auth-layer", "python")

if _layers_path not in sys.path:
    sys.path.insert(0, _layers_path)


# --- The 10 generated test stub files ---
STUB_FILES = [
    "test_create_order.py",
    "test_update_member.py",
    "test_hdcn_cognito_admin.py",
    "test_get_member_self.py",
    "test_cognito_role_assignment.py",
    "test_generate_order_pdf.py",
    "test_create_member.py",
    "test_export_members.py",
    "test_admin_get_orders.py",
    "test_admin_record_payment.py",
]


# =============================================================================
# Property 5: Generated test stubs are valid and importable
# =============================================================================


class TestProperty5StubValidity:
    """
    # Feature: code-quality-fixes-2026-06, Property 5: Generated test stubs are valid

    **Validates: Requirements 4.3**

    For any generated backend test stub file, the file shall be valid Python
    that can be parsed without syntax errors, shall import the corresponding
    handler module, and shall contain at least one function whose name starts
    with `test_`.
    """

    @given(stub_file=st.sampled_from(STUB_FILES))
    @settings(max_examples=30)
    def test_stub_parses_without_syntax_errors(self, stub_file: str):
        """
        **Validates: Requirements 4.3**

        For any stub file, it shall be valid Python that compiles
        without syntax errors.
        """
        file_path = os.path.join(_tests_unit_dir, stub_file)
        assert os.path.exists(file_path), (
            f"Stub file does not exist: {file_path}"
        )

        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        # compile() raises SyntaxError if the source is invalid
        try:
            compile(source, file_path, "exec")
        except SyntaxError as e:
            pytest.fail(
                f"Stub file {stub_file} has syntax error: {e}"
            )

        note(f"Verified: {stub_file} compiles without syntax errors")

    @given(stub_file=st.sampled_from(STUB_FILES))
    @settings(max_examples=30)
    def test_stub_contains_test_functions(self, stub_file: str):
        """
        **Validates: Requirements 4.3**

        For any stub file, it shall contain at least one function
        whose name starts with `test_`.
        """
        file_path = os.path.join(_tests_unit_dir, stub_file)
        assert os.path.exists(file_path), (
            f"Stub file does not exist: {file_path}"
        )

        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)

        # Collect all test_ functions (top-level and in classes)
        test_functions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_"):
                    test_functions.append(node.name)

        assert len(test_functions) > 0, (
            f"Stub file {stub_file} contains no test_ functions"
        )
        note(f"Verified: {stub_file} has {len(test_functions)} test function(s): {test_functions}")

    @given(stub_file=st.sampled_from(STUB_FILES))
    @settings(max_examples=30)
    def test_stub_imports_handler(self, stub_file: str):
        """
        **Validates: Requirements 4.3**

        For any stub file, it shall import the corresponding handler module
        (i.e., contain an import statement referencing handler.<name>.app).
        """
        file_path = os.path.join(_tests_unit_dir, stub_file)
        assert os.path.exists(file_path), (
            f"Stub file does not exist: {file_path}"
        )

        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)

        # Derive expected handler name from stub filename
        # test_create_order.py -> create_order
        handler_name = stub_file.replace("test_", "", 1).replace(".py", "")

        # Check for import statements that reference the handler
        handler_imported = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and f"handler.{handler_name}" in node.module:
                    handler_imported = True
                    break
                # Also check for direct 'app' import with sys.path manipulation
                if node.module and handler_name in (node.module or ""):
                    handler_imported = True
                    break
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if f"handler.{handler_name}" in alias.name:
                        handler_imported = True
                        break

        assert handler_imported, (
            f"Stub file {stub_file} does not import from handler.{handler_name}"
        )
        note(f"Verified: {stub_file} imports handler.{handler_name}")

    @given(stub_file=st.sampled_from(STUB_FILES))
    @settings(max_examples=30)
    def test_stub_is_importable(self, stub_file: str):
        """
        **Validates: Requirements 4.3**

        For any stub file, verify it can be loaded as a module via
        importlib without raising ImportError or ModuleNotFoundError.
        """
        file_path = os.path.join(_tests_unit_dir, stub_file)
        assert os.path.exists(file_path), (
            f"Stub file does not exist: {file_path}"
        )

        module_name = f"test_stub_check_{stub_file.replace('.py', '')}"

        # Ensure handler path is on sys.path for import resolution
        handler_name = stub_file.replace("test_", "", 1).replace(".py", "")
        handler_dir = os.path.join(_backend_dir, "handler", handler_name)
        if os.path.isdir(handler_dir) and handler_dir not in sys.path:
            sys.path.insert(0, handler_dir)

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        assert spec is not None, (
            f"Could not create module spec for {stub_file}"
        )

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            pytest.fail(
                f"Stub file {stub_file} failed to import: {type(e).__name__}: {e}"
            )

        note(f"Verified: {stub_file} is importable as a module")
