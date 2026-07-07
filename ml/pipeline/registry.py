"""
Stage Registry

Registry for pipeline stages to enable dynamic stage registration and lookup.
"""

from ml.pipeline.stage import PipelineStage


class StageRegistry:
    """
    Registry for pipeline stages.

    Allows stages to be registered by name and instantiated dynamically.
    Useful for plugin-style architectures and configuration-driven pipelines.
    """

    def __init__(self):
        """Initialize empty registry"""
        self._stages: dict[str, type[PipelineStage]] = {}

    def register(
        self,
        name: str,
        stage_class: type[PipelineStage],
        overwrite: bool = False,
    ) -> None:
        """
        Register a stage class.

        Args:
            name: Stage name for lookup
            stage_class: Stage class (must inherit from PipelineStage)
            overwrite: Whether to overwrite existing registration
        """
        if not issubclass(stage_class, PipelineStage):
            raise TypeError(f"Stage class must inherit from PipelineStage, got {stage_class}")

        if name in self._stages and not overwrite:
            raise ValueError(f"Stage '{name}' already registered")

        self._stages[name] = stage_class

    def unregister(self, name: str) -> None:
        """
        Unregister a stage.

        Args:
            name: Stage name to unregister
        """
        if name not in self._stages:
            raise ValueError(f"Stage '{name}' not registered")

        del self._stages[name]

    def get(self, name: str) -> type[PipelineStage]:
        """
        Get stage class by name.

        Args:
            name: Stage name

        Returns:
            Stage class
        """
        if name not in self._stages:
            raise ValueError(f"Stage '{name}' not registered")

        return self._stages[name]

    def create_stage(self, name: str, stage_name: str | None = None, **kwargs) -> PipelineStage:
        """
        Create stage instance.

        Args:
            name: Registered stage class name
            stage_name: Instance name (defaults to class name)
            **kwargs: Arguments for stage constructor

        Returns:
            Stage instance
        """
        stage_class = self.get(name)
        instance_name = stage_name or name

        return stage_class(name=instance_name, **kwargs)

    def list_registered(self) -> list[str]:
        """List all registered stage names"""
        return sorted(self._stages.keys())

    def is_registered(self, name: str) -> bool:
        """Check if stage is registered"""
        return name in self._stages

    def clear(self) -> None:
        """Clear all registrations"""
        self._stages.clear()

    def __len__(self) -> int:
        """Get number of registered stages"""
        return len(self._stages)

    def __contains__(self, name: str) -> bool:
        """Check if stage is registered"""
        return name in self._stages


# Global stage registry
_global_registry = StageRegistry()


def register_stage(
    name: str,
    stage_class: type[PipelineStage] | None = None,
    overwrite: bool = False,
):
    """
    Register stage in global registry.

    Can be used as decorator:

    @register_stage("my_stage")
    class MyStage(PipelineStage):
        ...

    Or as function:
    register_stage("my_stage", MyStage)
    """
    if stage_class is None:
        # Used as decorator
        def decorator(cls: type[PipelineStage]) -> type[PipelineStage]:
            _global_registry.register(name, cls, overwrite=overwrite)
            return cls

        return decorator
    else:
        # Used as function
        _global_registry.register(name, stage_class, overwrite=overwrite)


def get_stage_registry() -> StageRegistry:
    """Get global stage registry"""
    return _global_registry


def create_stage(name: str, **kwargs) -> PipelineStage:
    """Create stage from global registry"""
    return _global_registry.create_stage(name, **kwargs)
