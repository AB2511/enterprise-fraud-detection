#!/usr/bin/env python3
"""
Script to fix remaining B904 exception chaining errors.
"""

import re
from pathlib import Path


def fix_multiline_raises(content: str) -> str:
    """Fix multiline raise statements that span multiple lines."""

    # Pattern for multiline raises: except Exception as e: ... raise DomainException(\n    f"message: {e}", "CODE"\n)
    # This pattern handles the specific formatting in our codebase
    pattern = r'(\s+except\s+\w+(?:\s+as\s+(\w+)):(?:[^\n]*\n)*?)(\s+)raise\s+(\w+Exception)\(\s*\n\s*f"([^"]+)"\s*,\s*"([^"]+)"\s*\n\s*\)(?!\s+from)'

    def replace_func(match):
        except_clause = match.group(1)
        exception_var = match.group(2) if match.group(2) else "e"
        indent = match.group(3)
        exception_type = match.group(4)
        message = match.group(5)
        code = match.group(6)

        return f'{except_clause}{indent}raise {exception_type}(f"{message}", "{code}") from {exception_var}'

    content = re.sub(pattern, replace_func, content, flags=re.MULTILINE | re.DOTALL)

    # Also fix single-line raises that weren't caught before
    pattern2 = r"(\s+except\s+(\w+)\s+as\s+(\w+):(?:[^\n]*\n)*?)(\s+)raise\s+(\w+Exception)\(([^)]+)\)(?!\s+from)"

    def replace_func2(match):
        except_clause = match.group(1)
        exception_var = match.group(3)
        indent = match.group(4)
        exception_type = match.group(5)
        args = match.group(6)

        return f"{except_clause}{indent}raise {exception_type}({args}) from {exception_var}"

    content = re.sub(pattern2, replace_func2, content, flags=re.MULTILINE | re.DOTALL)

    return content


def fix_file(file_path: Path) -> bool:
    """Fix B904 errors in a single file."""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    original_content = content
    content = fix_multiline_raises(content)

    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed B904 errors in {file_path}")
        return True

    return False


def main():
    """Fix remaining B904 errors in all repository files."""
    target_files = [
        "src/infrastructure/database/repositories/audit_repository_impl.py",
        "src/infrastructure/database/repositories/customer_repository_impl.py",
        "src/infrastructure/database/repositories/merchant_repository_impl.py",
        "src/infrastructure/database/repositories/prediction_repository_impl.py",
        "src/infrastructure/database/repositories/transaction_repository_impl.py",
        "src/infrastructure/database/repositories/alert_repository_impl.py",
    ]

    fixed_count = 0
    for file_path in target_files:
        path = Path(file_path)
        if path.exists():
            if fix_file(path):
                fixed_count += 1

    print(f"Fixed B904 errors in {fixed_count} files")


if __name__ == "__main__":
    main()
