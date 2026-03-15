"""Type definitions for README cleaning."""

from typing import Literal

CleanupMode = Literal["analysis", "embedding"]
SourceKind = Literal["paragraph", "list", "code", "table", "blockquote", "mixed"]
