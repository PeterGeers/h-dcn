"""Fix scan_product test files to use importlib.util instead of sys.path manipulation."""
import os
import re

BACKEND = r'c:\Users\peter\aws\h-dcn\backend'

# The _load_handler helper that we want all files to use
LOAD_HANDLER_FUNC = '''
def _load_handler():
    """Load the scan_product handler module by file path, bypassing sys.path."""
    if 'app' in sys.modules:
        del sys.modules['app']
    spec = importlib.util.spec_from_file_location('app', _handler_file)
    module = importlib.util.module_from_spec(spec)
    sys.modules['app'] = module
    spec.loader.exec_module(module)
    return module
'''

def fix_preservation():
    """Fix test_scan_product_preservation.py"""
    path = os.path.join(BACKEND, 'tests', 'unit', 'test_scan_product_preservation.py')
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add importlib.util import
    if 'import importlib.util' not in content:
        content = content.replace('import json\n', 'import json\nimport importlib.util\n', 1)

    # Replace _handler_path with _handler_file
    content = content.replace(
        "# Ensure handler is importable\n_handler_path = os.path.abspath(\n    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'scan_product')\n)\nif _handler_path not in sys.path:\n    sys.path.insert(0, _handler_path)",
        "# Path to the handler module (used for explicit import)\n_handler_file = os.path.abspath(\n    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'scan_product', 'app.py')\n)"
    )

    # Add _load_handler function after environment setup
    if '_load_handler' not in content:
        env_marker = "os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'\n"
        content = content.replace(env_marker, env_marker + LOAD_HANDLER_FUNC)

    # Replace all inline import blocks
    # Pattern 1: with cache clear before
    old_block = """        if 'app' in sys.modules:
            del sys.modules['app']

            handler_base = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', 'handler')
            )
            handler_base_n = os.path.normpath(handler_base) + os.sep
            sys.path[:] = [
                p for p in sys.path
                if not (os.path.normpath(p) + os.sep).startswith(handler_base_n)
                and os.path.normpath(p) != os.path.normpath(handler_base)
            ]
            sys.path.insert(0, _handler_path)

            import app as handler_module"""
    
    # Pattern 2: without preceding cache clear (just the handler_base block)
    old_block2 = """            handler_base = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', 'handler')
            )
            handler_base_n = os.path.normpath(handler_base) + os.sep
            sys.path[:] = [
                p for p in sys.path
                if not (os.path.normpath(p) + os.sep).startswith(handler_base_n)
                and os.path.normpath(p) != os.path.normpath(handler_base)
            ]
            sys.path.insert(0, _handler_path)

            import app as handler_module"""

    new_block = """            handler_module = _load_handler()"""

    # Try pattern 1 first
    count1 = content.count(old_block)
    content = content.replace(old_block, new_block)
    
    # Then pattern 2
    count2 = content.count(old_block2)
    content = content.replace(old_block2, new_block)

    # Also handle the case with 'if app in sys.modules' on separate line
    content = content.replace("        if 'app' in sys.modules:\n            del sys.modules['app']\n\n            handler_module = _load_handler()", "            handler_module = _load_handler()")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'test_scan_product_preservation.py: replaced {count1 + count2} inline imports')


def fix_property():
    """Fix test_property_scan_product.py"""
    path = os.path.join(BACKEND, 'tests', 'unit', 'test_property_scan_product.py')
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add importlib.util import
    if 'import importlib.util' not in content:
        content = content.replace('import json\n', 'import json\nimport importlib.util\n', 1)

    # Replace _handler_path with _handler_file
    content = content.replace(
        "# Ensure handler is importable\n_handler_path = os.path.abspath(\n    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'scan_product')\n)\nif _handler_path not in sys.path:\n    sys.path.insert(0, _handler_path)",
        "# Path to the handler module (used for explicit import)\n_handler_file = os.path.abspath(\n    os.path.join(os.path.dirname(__file__), '..', '..', 'handler', 'scan_product', 'app.py')\n)"
    )

    # Add _load_handler function after environment setup
    if '_load_handler' not in content:
        env_marker = "os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'\n"
        content = content.replace(env_marker, env_marker + LOAD_HANDLER_FUNC)

    # Replace inline import blocks
    old_block = """            handler_base = os.path.abspath(
                os.path.join(os.path.dirname(__file__), '..', '..', 'handler')
            )
            handler_base_n = os.path.normpath(handler_base) + os.sep
            sys.path[:] = [
                p for p in sys.path
                if not (os.path.normpath(p) + os.sep).startswith(handler_base_n)
                and os.path.normpath(p) != os.path.normpath(handler_base)
            ]
            sys.path.insert(0, _handler_path)

            import app as handler_module"""

    new_block = """            handler_module = _load_handler()"""

    count = content.count(old_block)
    content = content.replace(old_block, new_block)

    # Also handle 'if app in sys.modules' + inline pattern  
    content = content.replace("        if 'app' in sys.modules:\n            del sys.modules['app']\n\n            handler_module = _load_handler()", "            handler_module = _load_handler()")

    # Handle the # Ensure handler path is first comment variant
    old_comment_block = """            # Ensure handler path is first
            handler_module = _load_handler()"""
    content = content.replace(old_comment_block, "            handler_module = _load_handler()")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'test_property_scan_product.py: replaced {count} inline imports')


if __name__ == '__main__':
    fix_preservation()
    fix_property()
    print('Done!')
