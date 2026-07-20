"""Application Layer Audit Script."""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set

def extract_service_methods(service_file: Path) -> Set[str]:
    """Extract all async method names from a service file."""
    methods = set()
    try:
        with open(service_file, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                if not node.name.startswith('_'):
                    methods.add(node.name)
    except Exception as e:
        print(f"Error parsing {service_file.name}: {e}")
    
    return methods

def extract_use_case_calls(use_case_file: Path) -> Dict[str, List[str]]:
    """Extract service method calls from use case file."""
    calls_by_class = {}
    
    try:
        with open(use_case_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all use case classes
        class_pattern = r'class (\w+UseCase)'
        classes = re.findall(class_pattern, content)
        
        for class_name in classes:
            # Find service calls in this class
            service_calls = re.findall(r'self\._service\.(\w+)\(', content)
            calls_by_class[class_name] = list(set(service_calls))
    
    except Exception as e:
        print(f"Error parsing {use_case_file.name}: {e}")
    
    return calls_by_class

def main():
    base_path = Path('src/application')
    services_path = base_path / 'services'
    use_cases_path = base_path / 'use_cases'
    
    # Extract available service methods
    service_methods = {}
    for service_file in services_path.glob('*_service.py'):
        service_name = service_file.stem
        service_methods[service_name] = extract_service_methods(service_file)
    
    print("=" * 80)
    print("APPLICATION LAYER AUDIT - STEP 1")
    print("=" * 80)
    print()
    
    print("AVAILABLE SERVICES AND METHODS:")
    print("-" * 80)
    for service_name, methods in sorted(service_methods.items()):
        print(f"\n{service_name}:")
        for method in sorted(methods):
            print(f"  ✓ {method}()")
    
    print("\n" + "=" * 80)
    print("USE CASE DEPENDENCY ANALYSIS:")
    print("=" * 80)
    
    total_use_cases = 0
    issues = []
    
    for use_case_file in sorted(use_cases_path.glob('*_use_cases.py')):
        if use_case_file.name == '__init__.py':
            continue
        
        print(f"\n{use_case_file.name}:")
        print("-" * 80)
        
        calls_by_class = extract_use_case_calls(use_case_file)
        
        if not calls_by_class:
            print("  ⚠️  No use cases found or parsing error")
            issues.append(f"{use_case_file.name}: No use cases found")
            continue
        
        # Determine which service this use case depends on
        service_map = {
            'customer_use_cases.py': 'customer_service',
            'merchant_use_cases.py': 'merchant_service',
            'transaction_use_cases.py': 'transaction_service',
            'prediction_use_cases.py': 'prediction_service',
            'alert_use_cases.py': 'alert_service',
            'audit_use_cases.py': 'audit_service',
            'user_use_cases.py': 'user_service',
            'model_use_cases.py': 'model_service',  # May not exist
        }
        
        expected_service = service_map.get(use_case_file.name)
        available_methods = service_methods.get(expected_service, set())
        
        for class_name, calls in sorted(calls_by_class.items()):
            total_use_cases += 1
            print(f"\n  {class_name}:")
            
            if not calls:
                print("    ℹ️  No service calls detected")
                continue
            
            for call in sorted(calls):
                if call in available_methods:
                    print(f"    ✓ {call}() - EXISTS")
                else:
                    print(f"    ✗ {call}() - MISSING")
                    issues.append(f"{class_name}: calls {call}() but not in {expected_service}")
    
    print("\n" + "=" * 80)
    print("AUDIT SUMMARY:")
    print("=" * 80)
    print(f"Total Use Cases: {total_use_cases}")
    print(f"Services Found: {len(service_methods)}")
    print(f"Issues Found: {len(issues)}")
    
    if issues:
        print("\nDETAILED ISSUES:")
        print("-" * 80)
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()
