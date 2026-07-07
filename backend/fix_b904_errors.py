#!/usr/bin/env python3
"""
Script to fix B904 exception chaining errors automatically.

B904: Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None`
to distinguish them from errors in exception handling.
"""

import re
from pathlib import Path


def fix_b904_errors(file_path: Path) -> bool:
    """Fix B904 errors in a single file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False

    original_content = content

    # Pattern to match except blocks with raise statements
    # Look for pattern: except <exception> as <var>: ... raise <new_exception>
    patterns = [
        # Pattern 1: except Exception as e: ... raise SomeException(f"...{e}...")
        (
            r"(\s+except\s+\w+(?:\s+as\s+(\w+)):.*?)\n(\s+)raise\s+(\w+)\((.*?)\)",
            r"\1\n\3raise \4(\5) from \2",
        ),
        # Pattern 2: More specific for our codebase - handles multiline raises
        (
            r"(\s+except\s+(?:\w+(?:\.\w+)*|\(\w+(?:,\s*\w+)*\))\s+as\s+(\w+):\s*\n(?:.*?\n)*?)(\s+)raise\s+(\w+)\(([^)]*)\)(?!\s+from)",
            lambda m: f"{m.group(1)}{m.group(3)}raise {m.group(4)}({m.group(5)}) from {m.group(2)}",
        ),
    ]

    # Apply fixes
    for pattern, replacement in patterns:
        if callable(replacement):
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
        else:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)

    # Handle specific cases for our codebase
    # Fix the basic pattern: except Exception as e: ... raise DomainException(...)
    content = re.sub(
        r"(\s+except\s+Exception\s+as\s+(\w+):(?:.*?\n)*?)(\s+)raise\s+(\w+Exception)\(([^)]+)\)(?!\s+from)",
        r"\1\3raise \4(\5) from \2",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )

    # Fix IntegrityError pattern
    content = re.sub(
        r"(\s+except\s+IntegrityError\s+as\s+(\w+):(?:.*?\n)*?)(\s+)raise\s+(\w+Exception)\(([^)]+)\)(?!\s+from)",
        r"\1\3raise \4(\5) from \2",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )

    # Fix specific error types without 'from err'
    error_patterns = [
        "CustomerEmailExistsError",
        "MerchantNameExistsError",
        "ConflictError",
        "DomainException",
        "RepositoryError",
    ]

    for error_type in error_patterns:
        # Pattern for: except SomeError: raise OtherError(...)
        content = re.sub(
            rf"(\s+except\s+\w+\s+as\s+(\w+):(?:.*?\n)*?)(\s+)raise\s+{error_type}\(([^)]+)\)(?!\s+from)",
            rf"\1\3raise {error_type}(\4) from \2",
            content,
            flags=re.MULTILINE | re.DOTALL,
        )

        # Pattern for: except SomeError: ... raise OtherError(...)
        content = re.sub(
            rf"(\s+except\s+\w+(?:Error)?:(?:.*?\n)*?)(\s+)raise\s+{error_type}\(([^)]+)\)(?!\s+from)",
            rf"\1\2raise {error_type}(\3) from None",
            content,
            flags=re.MULTILINE | re.DOTALL,
        )

    # Save if changed
    if content != original_content:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Fixed B904 errors in {file_path}")
            return True
        except Exception as e:
            print(f"Error writing {file_path}: {e}")
            return False

    return False


def main():
    """Fix B904 errors in all Python files."""
    backend_dir = Path(".")
    python_files = list(backend_dir.rglob("*.py"))

    fixed_count = 0
    for py_file in python_files:
        if fix_b904_errors(py_file):
            fixed_count += 1

    print(f"Fixed B904 errors in {fixed_count} files")


if __name__ == "__main__":
    main()
