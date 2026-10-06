"""soma_core package - foundational state and security primitives."""

__version__ = "0.97.0"

from soma_core import (
    arbitration,
    cell_inventory,
    defects,
    enforcement,
    errors,
    evidence,
    evidence_collector,
    frontmatter,
    homeostasis,
    inference_provider,
    insights,
    lifecycle,
    locking,
    quarantine,
    receipts,
    scoring,
    storage,
    sweep_session,
    sync,
    telemetry,
    workspace,
)
from soma_core.cell_inventory import (
    CellInventory,
    CellInventoryEntry,
    CellInventoryError,
    inventory_cells,
)
from soma_core.errors import (
    CellCorruptError,
    LockTimeoutError,
    ReceiptExpiredError,
    SomaError,
    SomaValidationError,
)
from soma_core.frontmatter import parse_cell_frontmatter
from soma_core.lifecycle import (
    STATUS_ADAPT,
    STATUS_APOPTOSIS,
    STATUS_APOPTOSIS_WARNING,
    STATUS_DORMANT,
    STATUS_EXTINCT,
    STATUS_NEW,
    STATUS_SURVIVE,
    calculate_fitness_status,
)
from soma_core.locking import workspace_lock
from soma_core.receipts import (
    clear_receipts,
    compute_cell_digest,
    compute_file_digest,
    issue_receipt,
    verify_receipt,
)
from soma_core.scoring import laplace_score, wilson_lower_bound
from soma_core.telemetry import append_signal
from soma_core.workspace import resolve_workspace

__all__ = [
    # Submodules
    "arbitration",
    "cell_inventory",
    "defects",
    "enforcement",
    "errors",
    "evidence",
    "evidence_collector",
    "frontmatter",
    "homeostasis",
    "inference_provider",
    "insights",
    "lifecycle",
    "locking",
    "quarantine",
    "receipts",
    "scoring",
    "storage",
    "sweep_session",
    "sync",
    "telemetry",
    "workspace",
    # Core types & functions
    "CellInventory",
    "CellInventoryEntry",
    "CellInventoryError",
    "inventory_cells",
    "issue_receipt",
    "verify_receipt",
    "clear_receipts",
    "compute_cell_digest",
    "compute_file_digest",
    "ReceiptExpiredError",
    "resolve_workspace",
    "workspace_lock",
    "LockTimeoutError",
    "laplace_score",
    "wilson_lower_bound",
    "calculate_fitness_status",
    "STATUS_NEW",
    "STATUS_SURVIVE",
    "STATUS_ADAPT",
    "STATUS_EXTINCT",
    "STATUS_APOPTOSIS",
    "STATUS_APOPTOSIS_WARNING",
    "STATUS_DORMANT",
    "parse_cell_frontmatter",
    "append_signal",
    "SomaError",
    "SomaValidationError",
    "CellCorruptError",
]

