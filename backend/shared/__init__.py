# Shared utilities for Lambda handlers
# Extend path to include auth layer modules (presmeet_validation, etc.)
# This allows both backend/shared/ and layers/auth-layer/python/shared/ to coexist
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)