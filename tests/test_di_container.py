# -*- coding: utf-8 -*-
"""
Unit Tests for RenForge DI Container

Tests for DIContainer and interfaces.
"""

import pytest
from interfaces.di_container import DIContainer, Lifetime


class TestDIContainer:
    """Tests for DIContainer."""
    
    def test_register_and_resolve(self, di_container):
        """Test basic registration and resolution."""
        class IService:
            pass
        
        class ConcreteService:
            pass
        
        di_container.register(IService, ConcreteService)
        
        instance = di_container.resolve(IService)
        
        assert isinstance(instance, ConcreteService)
    
    def test_singleton_lifetime(self, di_container):
        """Test singleton returns same instance."""
        class IService:
            pass
        
        class ConcreteService:
            pass
        
        di_container.register(IService, ConcreteService, Lifetime.SINGLETON)
        
        instance1 = di_container.resolve(IService)
        instance2 = di_container.resolve(IService)
        
        assert instance1 is instance2
    
    def test_transient_lifetime(self, di_container):
        """Test transient returns new instance each time."""
        class IService:
            pass
        
        class ConcreteService:
            pass
        
        di_container.register(IService, ConcreteService, Lifetime.TRANSIENT)
        
        instance1 = di_container.resolve(IService)
        instance2 = di_container.resolve(IService)
        
        assert instance1 is not instance2
    
    def test_register_factory(self, di_container):
        """Test factory registration."""
        class IService:
            def __init__(self, value):
                self.value = value
        
        di_container.register_factory(
            IService,
            lambda c: IService(42)
        )
        
        instance = di_container.resolve(IService)
        
        assert instance.value == 42
    
    def test_register_instance(self, di_container):
        """Test registering an existing instance."""
        class IService:
            pass
        
        existing = IService()
        
        di_container.register_instance(IService, existing)
        
        resolved = di_container.resolve(IService)
        
        assert resolved is existing
    
    def test_resolve_unregistered_raises(self, di_container):
        """Test that resolving unregistered interface raises."""
        class IUnregistered:
            pass
        
        with pytest.raises(KeyError):
            di_container.resolve(IUnregistered)
    
    def test_try_resolve_unregistered_returns_none(self, di_container):
        """Test that try_resolve returns None for unregistered."""
        class IUnregistered:
            pass
        
        result = di_container.try_resolve(IUnregistered)
        
        assert result is None
    
    def test_is_registered(self, di_container):
        """Test checking if interface is registered."""
        class IService:
            pass
        
        class ConcreteService:
            pass
        
        assert not di_container.is_registered(IService)
        
        di_container.register(IService, ConcreteService)
        
        assert di_container.is_registered(IService)
    
    def test_global_instance(self):
        """Test global singleton instance."""
        DIContainer.reset_instance()
        
        instance1 = DIContainer.instance()
        instance2 = DIContainer.instance()
        
        assert instance1 is instance2
    
    def test_fluent_api(self, di_container):
        """Test fluent registration API."""
        class IA:
            pass
        class IB:
            pass
        class A:
            pass
        class B:
            pass
        
        result = (di_container
            .register(IA, A)
            .register(IB, B))
        
        assert result is di_container
        assert di_container.is_registered(IA)
        assert di_container.is_registered(IB)
