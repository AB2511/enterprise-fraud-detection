#!/usr/bin/env python3
"""Fix repository import statements."""

import os
import re

# Repository files to fix
repo_files = [
    "src/infrastructure/database/repositories/prediction_repository_impl.py",
    "src/infrastructure/database/repositories/alert_repository_impl.py", 
    "src/infrastructure/database/repositories/audit_repository_impl.py",
]

for repo_file in repo_files:
    if os.path.exists(repo_file):
        with open(repo_file, 'r') as f:
            content = f.read()
        
        # Fix the import line for domain exceptions
        old_pattern = r"from src\.domain\.exceptions\.base import DomainException"
        new_import = "from src.domain.exceptions.base import DomainException, NotFoundError, RepositoryError"
        
        if re.search(old_pattern, content):
            content = re.sub(old_pattern, new_import, content)
            
            with open(repo_file, 'w') as f:
                f.write(content)
            print(f"Fixed imports in {repo_file}")
        else:
            print(f"Pattern not found in {repo_file}")
    else:
        print(f"File not found: {repo_file}")