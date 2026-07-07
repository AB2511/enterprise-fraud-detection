#!/usr/bin/env python3
"""
Engineering Verification - Import Verification

Systematically verify all Python modules import successfully.
"""

import sys
import os
import importlib
from pathlib import Path
import traceback
from typing import List, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

class ImportVerifier:
    """Verify all module imports in the project."""
    
    def __init__(self):
        self.results = {
            "successful_imports": [],
            "failed_imports": [],
            "import_errors": {},
            "circular_imports": [],
            "missing_dependencies": []
        }
    
    def find_python_modules(self, directory: Path) -> List[Path]:
        """Find all Python modules in the directory."""
        python_files = []
        
        for file_path in directory.rglob("*.py"):
            # Skip __pycache__ and .git directories
            if "__pycache__" in str(file_path) or ".git" in str(file_path):
                continue
            
            # Skip test files for now (we'll handle them separately)
            if "test_" in file_path.name or file_path.name.startswith("test_"):
                continue
                
            python_files.append(file_path)
        
        return python_files
    
    def module_path_to_import_name(self, file_path: Path) -> str:
        """Convert file path to import module name."""
        # Get relative path from project root
        rel_path = file_path.relative_to(PROJECT_ROOT)
        
        # Remove .py extension
        if rel_path.name == "__init__.py":
            # For __init__.py, use parent directory
            module_parts = rel_path.parent.parts
        else:
            # For regular .py files
            module_parts = rel_path.with_suffix('').parts
        
        # Join with dots
        return '.'.join(module_parts)
    
    def verify_module_import(self, module_name: str) -> Dict[str, Any]:
        """Verify a single module can be imported."""
        try:
            # Try to import the module
            importlib.import_module(module_name)
            
            return {
                "success": True,
                "module": module_name,
                "error": None
            }
            
        except ImportError as e:
            error_msg = str(e)
            
            # Check if it's a missing dependency
            if "No module named" in error_msg:
                missing_dep = error_msg.split("'")[1] if "'" in error_msg else "unknown"
                self.results["missing_dependencies"].append(missing_dep)
            
            return {
                "success": False,
                "module": module_name,
                "error": error_msg,
                "error_type": "ImportError"
            }
            
        except Exception as e:
            return {
                "success": False,
                "module": module_name,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def verify_all_imports(self) -> Dict[str, Any]:
        """Verify all module imports in the project."""
        
        print("🔍 Discovering Python modules...")
        
        # Find all Python modules
        ml_modules = self.find_python_modules(PROJECT_ROOT / "ml")
        script_modules = []
        
        # Add script files
        for script_file in PROJECT_ROOT.glob("*.py"):
            if not script_file.name.startswith("test_"):
                script_modules.append(script_file)
        
        all_modules = ml_modules + script_modules
        
        print(f"Found {len(all_modules)} Python modules to verify")
        
        # Verify each module
        print("\n📦 Verifying module imports...")
        
        for file_path in all_modules:
            try:
                module_name = self.module_path_to_import_name(file_path)
                print(f"  Checking: {module_name}")
                
                result = self.verify_module_import(module_name)
                
                if result["success"]:
                    self.results["successful_imports"].append(module_name)
                    print(f"    ✓ {module_name}")
                else:
                    self.results["failed_imports"].append(module_name)
                    self.results["import_errors"][module_name] = result["error"]
                    print(f"    ✗ {module_name}: {result['error']}")
                    
            except Exception as e:
                print(f"    ⚠ Error processing {file_path}: {e}")
        
        return self.results
    
    def generate_report(self) -> None:
        """Generate import verification report."""
        
        print("\n" + "="*60)
        print("IMPORT VERIFICATION REPORT")
        print("="*60)
        
        total_modules = len(self.results["successful_imports"]) + len(self.results["failed_imports"])
        success_rate = len(self.results["successful_imports"]) / total_modules if total_modules > 0 else 0
        
        print(f"Total Modules: {total_modules}")
        print(f"Successful Imports: {len(self.results['successful_imports'])}")
        print(f"Failed Imports: {len(self.results['failed_imports'])}")
        print(f"Success Rate: {success_rate:.1%}")
        
        if self.results["failed_imports"]:
            print(f"\n❌ FAILED IMPORTS ({len(self.results['failed_imports'])}):")
            print("-" * 40)
            
            for module in self.results["failed_imports"]:
                error = self.results["import_errors"].get(module, "Unknown error")
                print(f"  {module}: {error}")
        
        if self.results["missing_dependencies"]:
            unique_deps = list(set(self.results["missing_dependencies"]))
            print(f"\n📋 MISSING DEPENDENCIES ({len(unique_deps)}):")
            print("-" * 40)
            
            for dep in unique_deps:
                print(f"  {dep}")
                
        if len(self.results["failed_imports"]) == 0:
            print(f"\n🎉 All imports successful!")
        else:
            print(f"\n⚠️  {len(self.results['failed_imports'])} imports failed - fix required")


def main():
    """Main verification entry point."""
    
    print("Engineering Verification - Import Check")
    print("="*50)
    
    verifier = ImportVerifier()
    
    try:
        # Run verification
        results = verifier.verify_all_imports()
        
        # Generate report
        verifier.generate_report()
        
        # Exit with appropriate code
        success = len(results["failed_imports"]) == 0
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"\n❌ Import verification failed: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()