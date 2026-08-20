import pytest
from forge.kernels.base import KernelRegistry, RegisteredKernel
from forge.kernels.event_counts import KERNEL_ID, KERNEL_VERSION, EventCountsKernel


def _registry_with_event_counts() -> KernelRegistry:
    registry = KernelRegistry()
    registry.register(
        RegisteredKernel(
            kernel_id=KERNEL_ID,
            kernel_version=KERNEL_VERSION,
            engine="python",
            factory=EventCountsKernel,
        )
    )
    return registry


def test_resolve_returns_a_usable_kernel_instance() -> None:
    registry = _registry_with_event_counts()
    kernel = registry.resolve(kernel_id=KERNEL_ID, kernel_version=KERNEL_VERSION, engine="python")
    assert isinstance(kernel, EventCountsKernel)


def test_resolve_unregistered_kernel_raises_lookup_error() -> None:
    registry = _registry_with_event_counts()
    with pytest.raises(LookupError):
        registry.resolve(kernel_id="forge.unknown", kernel_version="1.0.0", engine="python")


def test_register_duplicate_key_raises() -> None:
    registry = _registry_with_event_counts()
    with pytest.raises(ValueError, match="duplicate"):
        registry.register(
            RegisteredKernel(
                kernel_id=KERNEL_ID,
                kernel_version=KERNEL_VERSION,
                engine="python",
                factory=EventCountsKernel,
            )
        )


def test_different_engine_is_a_distinct_registration() -> None:
    registry = _registry_with_event_counts()
    registry.register(
        RegisteredKernel(
            kernel_id=KERNEL_ID,
            kernel_version=KERNEL_VERSION,
            engine="cpp",
            factory=EventCountsKernel,
        )
    )
    resolved = registry.resolve(kernel_id=KERNEL_ID, kernel_version=KERNEL_VERSION, engine="cpp")
    assert isinstance(resolved, EventCountsKernel)
