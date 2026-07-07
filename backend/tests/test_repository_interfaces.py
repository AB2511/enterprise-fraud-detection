"""Repository Interface Compliance Tests."""

import pytest
import inspect
from typing import get_type_hints

from src.application.interfaces.customer_repository import CustomerRepository
from src.application.interfaces.merchant_repository import MerchantRepository
from src.application.interfaces.transaction_repository import TransactionRepository
from src.application.interfaces.prediction_repository import PredictionRepository
from src.application.interfaces.alert_repository import AlertRepository
from src.application.interfaces.audit_repository import AuditRepository
from src.application.interfaces.user_repository import UserRepository
from src.application.interfaces.model_repository import ModelRepository

from src.infrastructure.database.repositories.customer_repository_impl import CustomerRepositoryImpl
from src.infrastructure.database.repositories.merchant_repository_impl import MerchantRepositoryImpl
from src.infrastructure.database.repositories.transaction_repository_impl import TransactionRepositoryImpl
from src.infrastructure.database.repositories.prediction_repository_impl import PredictionRepositoryImpl
from src.infrastructure.database.repositories.alert_repository_impl import AlertRepositoryImpl
from src.infrastructure.database.repositories.audit_repository_impl import AuditRepositoryImpl
from src.infrastructure.database.repositories.user_repository_impl import UserRepositoryImpl
from src.infrastructure.database.repositories.model_repository_impl import ModelRepositoryImpl


class TestRepositoryInterfaceCompliance:
    """Test that all repository implementations properly implement their interfaces."""

    @pytest.mark.parametrize("interface_class,implementation_class", [
        (CustomerRepository, CustomerRepositoryImpl),
        (MerchantRepository, MerchantRepositoryImpl),
        (TransactionRepository, TransactionRepositoryImpl),
        (PredictionRepository, PredictionRepositoryImpl),
        (AlertRepository, AlertRepositoryImpl),
        (AuditRepository, AuditRepositoryImpl),
        (UserRepository, UserRepositoryImpl),
        (ModelRepository, ModelRepositoryImpl),
    ])
    def test_interface_compliance(self, interface_class, implementation_class):
        """Test that repository implementations comply with their interfaces."""
        
        # Verify implementation inherits from interface
        assert issubclass(implementation_class, interface_class), \
            f"{implementation_class.__name__} must inherit from {interface_class.__name__}"
        
        # Get all abstract methods from interface
        interface_methods = set()
        for name, method in inspect.getmembers(interface_class, inspect.ismethod):
            if getattr(method, '__isabstractmethod__', False):
                interface_methods.add(name)
        
        # Also check for abstract methods in parent classes
        for base in interface_class.__mro__:
            for name, method in inspect.getmembers(base, inspect.ismethod):
                if getattr(method, '__isabstractmethod__', False):
                    interface_methods.add(name)
        
        # Get all methods implemented in the implementation class
        implementation_methods = set()
        for name, method in inspect.getmembers(implementation_class, inspect.ismethod):
            if not name.startswith('_'):  # Skip private methods
                implementation_methods.add(name)
        
        # Check that all interface methods are implemented
        missing_methods = interface_methods - implementation_methods
        assert len(missing_methods) == 0, \
            f"{implementation_class.__name__} is missing methods: {missing_methods}"

    @pytest.mark.parametrize("interface_class,implementation_class", [
        (CustomerRepository, CustomerRepositoryImpl),
        (MerchantRepository, MerchantRepositoryImpl),
        (TransactionRepository, TransactionRepositoryImpl),
        (PredictionRepository, PredictionRepositoryImpl),
        (AlertRepository, AlertRepositoryImpl),
        (AuditRepository, AuditRepositoryImpl),
        (UserRepository, UserRepositoryImpl),
        (ModelRepository, ModelRepositoryImpl),
    ])
    def test_method_signatures_match(self, interface_class, implementation_class):
        """Test that method signatures match between interface and implementation."""
        
        interface_methods = {}
        for name, method in inspect.getmembers(interface_class, inspect.ismethod):
            if getattr(method, '__isabstractmethod__', False):
                interface_methods[name] = inspect.signature(method)
        
        implementation_methods = {}
        for name, method in inspect.getmembers(implementation_class, inspect.ismethod):
            if name in interface_methods:
                implementation_methods[name] = inspect.signature(method)
        
        # Check signature compatibility
        for method_name in interface_methods:
            if method_name in implementation_methods:
                interface_sig = interface_methods[method_name]
                impl_sig = implementation_methods[method_name]
                
                # Check parameter names and types
                interface_params = list(interface_sig.parameters.keys())
                impl_params = list(impl_sig.parameters.keys())
                
                assert interface_params == impl_params, \
                    f"Parameter mismatch in {implementation_class.__name__}.{method_name}: " \
                    f"interface has {interface_params}, implementation has {impl_params}"

    def test_all_repositories_have_async_methods(self):
        """Test that all repository methods are async."""
        implementations = [
            CustomerRepositoryImpl,
            MerchantRepositoryImpl,
            TransactionRepositoryImpl,
            PredictionRepositoryImpl,
            AlertRepositoryImpl,
            AuditRepositoryImpl,
            UserRepositoryImpl,
            ModelRepositoryImpl,
        ]
        
        for repo_class in implementations:
            for name, method in inspect.getmembers(repo_class, inspect.isfunction):
                if not name.startswith('_') and name != '__init__':
                    assert inspect.iscoroutinefunction(method), \
                        f"{repo_class.__name__}.{name} must be async"

    def test_crud_operations_exist(self):
        """Test that all repositories implement basic CRUD operations."""
        required_crud_methods = ['create', 'get_by_id', 'update', 'delete']
        
        implementations = [
            CustomerRepositoryImpl,
            MerchantRepositoryImpl,
            PredictionRepositoryImpl,
            AlertRepositoryImpl,
            UserRepositoryImpl,
            ModelRepositoryImpl,
        ]
        
        for repo_class in implementations:
            repo_methods = [name for name, _ in inspect.getmembers(repo_class, inspect.isfunction)]
            
            for crud_method in required_crud_methods:
                assert crud_method in repo_methods, \
                    f"{repo_class.__name__} missing CRUD method: {crud_method}"

    def test_pagination_support(self):
        """Test that repositories support pagination parameters."""
        implementations = [
            CustomerRepositoryImpl,
            MerchantRepositoryImpl,
            PredictionRepositoryImpl,
            AlertRepositoryImpl,
            AuditRepositoryImpl,
            UserRepositoryImpl,
            ModelRepositoryImpl,
        ]
        
        for repo_class in implementations:
            # Find list methods (methods that return lists)
            for name, method in inspect.getmembers(repo_class, inspect.isfunction):
                if name.startswith('list_') or name.startswith('get_') and 'list' in name.lower():
                    sig = inspect.signature(method)
                    param_names = list(sig.parameters.keys())
                    
                    # Check for pagination parameters
                    has_limit = 'limit' in param_names
                    has_offset = 'offset' in param_names
                    
                    if has_limit or has_offset:
                        assert has_limit, f"{repo_class.__name__}.{name} has offset but no limit"
                        # offset is optional for some methods
                        
    def test_repository_initialization(self):
        """Test that all repositories can be initialized with AsyncSession."""
        from unittest.mock import Mock
        
        mock_session = Mock()
        
        implementations = [
            CustomerRepositoryImpl,
            MerchantRepositoryImpl,
            TransactionRepositoryImpl,
            PredictionRepositoryImpl,
            AlertRepositoryImpl,
            AuditRepositoryImpl,
            UserRepositoryImpl,
            ModelRepositoryImpl,
        ]
        
        for repo_class in implementations:
            # Should not raise exception
            instance = repo_class(mock_session)
            assert instance is not None
            # Check that session is stored
            assert hasattr(instance, '_session')

    def test_exception_imports(self):
        """Test that repositories import proper exception classes."""
        implementations = [
            CustomerRepositoryImpl,
            MerchantRepositoryImpl,
            TransactionRepositoryImpl,
            PredictionRepositoryImpl,
            AlertRepositoryImpl,
            AuditRepositoryImpl,
            UserRepositoryImpl,
            ModelRepositoryImpl,
        ]
        
        for repo_class in implementations:
            module = inspect.getmodule(repo_class)
            
            # Check for exception imports in module
            module_dict = module.__dict__
            expected_exceptions = ['RepositoryError', 'NotFoundError']
            
            for exception in expected_exceptions:
                # Should have access to exception classes (either imported or available)
                # This is a basic check - in practice exceptions should be properly imported
                assert hasattr(module, exception) or exception in module_dict or \
                       any(exception in str(imp) for imp in module_dict.values() if hasattr(imp, '__name__')), \
                    f"{repo_class.__name__} module should have access to {exception}"