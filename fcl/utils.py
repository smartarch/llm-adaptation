class HashableDict(dict):
    """Dictionary usable as a key (used for variable bindings of quantified formulas)."""

    def __hash__(self):  # type: ignore[override]
        return hash(tuple(sorted(self.items())))
