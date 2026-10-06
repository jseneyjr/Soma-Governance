"""Package for soma enzymes (deprecated in v0.96.2, removal in v0.97.0)."""
import warnings

warnings.warn(
    "The 'enzymes' package and shims are deprecated as of v0.96.2 and will be removed in v0.97.0. "
    "Use soma_cli or soma_core directly.",
    DeprecationWarning,
    stacklevel=2,
)
