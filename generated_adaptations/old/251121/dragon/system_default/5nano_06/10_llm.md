Reasoning and adaptation strategy (final)

Issue recap
- Tests report that some villagers (e.g., John, Nancy) were not assigned in assign_in_village. This caused “not assigned” errors and occasional duplicates in other scenarios.

Strategy improvements
- Use a robust, deterministic, single-pass assignment for villagers in the village.
- Role detection should be resilient to possible inconsistencies in the role attribute:
  - Treat roles case-insensitively and trim whitespace.
  - Accept Farmer, Warrior as valid roles; treat anything else as unknown.
- Assignment plan in assign_in_village:
  - Warriors: always assign to the cave (single explicit step) and mark as assigned.
  - Farmers (and any unknown-role villagers that are effectively farmers): compute the spawn allocations in a single pass:
    - s_f = min(number_of_farmers // 2, wheat // 10) if wheat >= 10 else 0
    - s_w = min((number_of_farmers - 2*s_f) // 2, wheat // 12) if wheat >= 12 else 0
  - Build a definitive mapping so every farmer is assigned to exactly one group:
    - First 2*s_f farmers -> "spawn farmer"
    - Next 2*s_w farmers -> "spawn warrior"
    - Remaining farmers -> "farm"
  - Apply the mapping to all farmers, ensuring every farmer gets exactly one group.
  - Safety net: any component not assigned in this step (unknown roles or edge cases) gets a default assignment to "farm".
- assign_in_cave remains: Warriors -> "attack"; Farmers/Unknown -> "village" (back to village).

This approach guarantees:
- Every component in assign_in_village is assigned exactly once.
- No edge-case farmer is left unassigned.
- The spawning logic respects current wheat and farmer counts.
- The design remains robust to mislabelled roles or unusual components.

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _is_role(self, comp, target: str) -> bool:
        r = getattr(comp, "role", None)
        if isinstance(r, str):
            return r.strip().lower() == target
        return False

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: Stay in Village and farm
        - cave: Go to the Cave
        - spawn farmer: For every two villagers in this group and 10 wheat, spawn a Farmer
        - spawn warrior: For every two villagers in this group and 12 wheat, spawn a Warrior
        """
        # Classify villagers robustly
        farmers = [c for c in components if self._is_role(c, "farmer")]
        warriors = [c for c in components if self._is_role(c, "warrior")]
        unknowns = [c for c in components if not self._is_role(c, "farmer") and not self._is_role(c, "warrior")]

        assigned = set()

        # 1) Warriors must go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")
            assigned.add(w)

        # 2) Prepare spawning allocations for farmers (deterministic single-pass)
        total_farmers = len(farmers)
        current_wheat = getattr(environment.farm, "wheat", 0)
        try:
            wheat_val = int(current_wheat)
        except Exception:
            wheat_val = 0

        s_f = 0
        if wheat_val >= 10:
            s_f = min(total_farmers // 2, wheat_val // 10)

        remaining = total_farmers - 2 * s_f
        s_w = 0
        if wheat_val >= 12:
            s_w = min(remaining // 2, wheat_val // 12)

        # 3) Build a single mapping so every farmer is assigned exactly once
        mapping = {}
        idx = 0
        # First 2*s_f -> spawn farmer
        for _ in range(2 * s_f):
            if idx < total_farmers:
                mapping[farmers[idx]] = "spawn farmer"
                assigned.add(farmers[idx])
                idx += 1
        # Next 2*s_w -> spawn warrior
        for _ in range(2 * s_w):
            if idx < total_farmers:
                mapping[farmers[idx]] = "spawn warrior"
                assigned.add(farmers[idx])
                idx += 1
        # Remaining -> farm
        for i in range(idx, total_farmers):
            mapping[farmers[i]] = "farm"
            assigned.add(farmers[i])

        # 4) Apply assignments for all farmers
        for f in farmers:
            grp = mapping.get(f, "farm")
            environment.assign_group(f, grp)

        # 5) Safety net: any component not yet assigned goes to farm
        for c in components:
            if c not in assigned:
                environment.assign_group(c, "farm")

        # Note: unknowns are covered by the safety net or by farmers if they got included;
        # they will be assigned to farm by the safety net if not explicitly handled.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon (Warriors should go here)
        - cave: Stay in the Cave (not used by our strategy)
        - village: Go to the Village (Farmers return to farming/spawning)
        """
        for c in components:
            if self._is_role(c, "warrior"):
                environment.assign_group(c, "attack")
            else:
                # Farmers (or unknown) in the Cave should go back to the Village
                environment.assign_group(c, "village")
```