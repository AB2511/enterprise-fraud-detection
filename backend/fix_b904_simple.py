#!/usr/bin/env python3
"""
Simple script to fix B904 exception chaining errors.
"""

import re
from pathlib import Path


def fix_file(file_path: Path) -> bool:
    """Fix B904 errors in a single file."""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Fix pattern: raise SomeException(...) at end of except block (no 'from' clause)
    # This handles the common case where we just need to add 'from e'

    # Pattern 1: except Exception as e: ... raise SomeException(...)
    lines = content.split("\n")
    new_lines = []

    for i, line in enumerate(lines):
        new_lines.append(line)

        # Check if this is a raise statement without 'from'
        if re.match(r"\s+raise\s+\w+\(.*\)$", line) and "from " not in line and i > 0:

            # Look backwards to find the except clause
            except_var = None
            for j in range(i - 1, max(0, i - 10), -1):  # Look back up to 10 lines
                except_match = re.match(r"\s*except\s+\w+(?:\s+as\s+(\w+)):", lines[j])
                if except_match:
                    except_var = except_match.group(1)
                    break

            # If we found an exception variable, add 'from var'
            if except_var:
                new_lines[-1] = line + f" from {except_var}"

    content = "\n".join(new_lines)

    # Save if changed
    if content != original_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed B904 errors in {file_path}")
        return True

    return False


def main():
    """Fix B904 errors in repository files."""
    # Target the main problematic files
    target_files = [
        "src/infrastructure/database/repositories/audit_repository_impl.py",
        "src/infrastructure/database/repositories/customer_repository_impl.py",
        "src/infrastructure/database/repositories/merchant_repository_impl.py",
        "src/infrastructure/database/repositories/prediction_repository_impl.py",
        "src/infrastructure/database/repositories/transaction_repository_impl.py",
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
