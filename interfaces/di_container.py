# -*- coding: utf-8 -*-
"""
RenForge Dependency Injection Container

Simple DI container for managing service instances and their dependencies.
Supports singleton and transient lifetimes.
"""

from typing import Dict, Type, Any, Optional, Callable, TypeVar
from enum import Enum

from renforge_logger import get_logger

logger = get_logger("di")

T = TypeVar('T')


class Lifetime(Enum):
    """Service lifetime options."""
    SINGLETON = "singleton"  # Single instance for entire app
    TRANSIENT = "transient"  # New instance each time


class ServiceRegistration:
    """Represents a registered service."""
    
    def __init__(
        self,
        interface: Type,
        implementation: Type,
        lifetime: Lifetime,
        factory: Optional[Callable[['DIContainer'], Any]] = None
    ):
        self.interface = interface
        self.implementation = implementation
        self.lifetime = lifetime
        self.factory = factory
        self.instance: Optional[Any] = None


class DIContainer:
    """
    Simple Dependency Injection Container.
    
    Provides service registration and resolution with support for:
    - Singleton and transient lifetimes
    - Factory functions for complex initialization
    - Interface-based resolution
    
    Usage:
        container = DIContainer()
        container.register(IMainView, MainView, Lifetime.SINGLETON)
        
        view = container.resolve(IMainView)
    """
    
    _global_instance: Optional['DIContainer'] = None
    
    def __init__(self):
        self._registrations: Dict[Type, ServiceRegistration] = {}
        logger.debug("DIContainer created")
    
    # =========================================================================
    # SINGLETON ACCESS
    # =========================================================================
    
    @classmethod
    def instance(cls) -> 'DIContainer':
        """Get or create the global container instance."""
        if cls._global_instance is None:
            cls._global_instance = DIContainer()
        return cls._global_instance
    
    @classmethod
    def reset_instance(cls):
        """Reset the global instance (for testing)."""
        cls._global_instance = None
    
    # =========================================================================
    # REGISTRATION
    # =========================================================================
    
    def register(
        self,
        interface: Type[T],
        implementation: Type[T],
        lifetime: Lifetime = Lifetime.SINGLETON
    ) -> 'DIContainer':
        """
        Register a service.
        
        Args:
            interface: The interface/protocol type
            implementation: The concrete implementation type
            lifetime: Singleton or transient
            
        Returns:
            Self for chaining
        """
        self._registrations[interface] = ServiceRegistration(
            interface=interface,
            implementation=implementation,
            lifetime=lifetime
        )
        logger.debug(f"Registered {interface.__name__} -> {implementation.__name__} ({lifetime.value})")
        return self
    
    def register_factory(
        self,
        interface: Type[T],
        factory: Callable[['DIContainer'], T],
        lifetime: Lifetime = Lifetime.SINGLETON
    ) -> 'DIContainer':
        """
        Register a service with a factory function.
        
        Args:
            interface: The interface/protocol type
            factory: Factory function that creates the instance
            lifetime: Singleton or transient
            
        Returns:
            Self for chaining
        """
        self._registrations[interface] = ServiceRegistration(
            interface=interface,
            implementation=type(None),  # Placeholder
            lifetime=lifetime,
            factory=factory
        )
        logger.debug(f"Registered factory for {interface.__name__} ({lifetime.value})")
        return self
    
    def register_instance(
        self,
        interface: Type[T],
        instance: T
    ) -> 'DIContainer':
        """
        Register an existing instance as a singleton.
        
        Args:
            interface: The interface/protocol type
            instance: The pre-created instance
            
        Returns:
            Self for chaining
        """
        registration = ServiceRegistration(
            interface=interface,
            implementation=type(instance),
            lifetime=Lifetime.SINGLETON
        )
        registration.instance = instance
        self._registrations[interface] = registration
        logger.debug(f"Registered instance for {interface.__name__}")
        return self
    
    # =========================================================================
    # RESOLUTION
    # =========================================================================
    
    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve a service by interface.
        
        Args:
            interface: The interface type to resolve
            
        Returns:
            Instance of the registered implementation
            
        Raises:
            KeyError: If interface is not registered
        """
        if interface not in self._registrations:
            raise KeyError(f"No registration found for {interface.__name__}")
        
        registration = self._registrations[interface]
        
        # Return existing instance for singletons
        if registration.lifetime == Lifetime.SINGLETON and registration.instance is not None:
            return registration.instance
        
        # Create new instance
        if registration.factory:
            instance = registration.factory(self)
        else:
            instance = self._create_instance(registration.implementation)
        
        # Store singleton
        if registration.lifetime == Lifetime.SINGLETON:
            registration.instance = instance
        
        return instance
    
    def try_resolve(self, interface: Type[T]) -> Optional[T]:
        """
        Try to resolve a service, returning None if not registered.
        
        Args:
            interface: The interface type to resolve
            
        Returns:
            Instance or None
        """
        try:
            return self.resolve(interface)
        except KeyError:
            return None
    
    def _create_instance(self, implementation: Type) -> Any:
        """Create an instance of the implementation type."""
        try:
            # Try to create with container injection
            return implementation()
        except TypeError:
            # If that fails, try without args
            logger.warning(f"Could not auto-construct {implementation.__name__}")
            raise
    
    # =========================================================================
    # UTILITY
    # =========================================================================
    
    def is_registered(self, interface: Type) -> bool:
        """Check if an interface is registered."""
        return interface in self._registrations
    
    def get_registrations(self) -> Dict[str, str]:
        """Get a dict of interface name -> implementation name."""
        return {
            iface.__name__: reg.implementation.__name__
            for iface, reg in self._registrations.items()
        }
    
    def clear(self):
        """Clear all registrations."""
        self._registrations.clear()
        logger.debug("Container cleared")
    
    def __repr__(self) -> str:
        return f"DIContainer(registrations={len(self._registrations)})"
