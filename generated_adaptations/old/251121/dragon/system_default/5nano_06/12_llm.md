Reasoning and adaptation strategy (final)

Issue recap
- Tests report that some villagers (e.g., John, Nancy, Robert) were not assigned in assign_in_village. The root cause is that we only treated explicit Farmer/Warrior roles to split farmers vs warriors, which could miss some villagers if their role attribute isn’t perfectly aligned or if there are unknown/edge-case entries.

Strategy improvements
- Make assignment in village robust to any non-warrior villagers by treating every non-warrior as a farmer for assignment purposes.
- Do a deterministic, single-pass allocation:
  - Warriors are always assigned to the cave (single explicit step).
  - All non-warrior villagers (including unknowns) are considered farmers for the spawning/farming allocations.
  - Compute spawning allocations using current wheat and total number of farmers.
  - Build a definitive mapping so every farmer is assigned to exactly one of: "spawn farmer", "spawn warrior", or "farm".
  - Apply the mapping to all farmers; no safety-net is needed if all farmers are included in the mapping.
- This guarantees every component in assign_in_village is assigned exactly once and eliminates “not assigned” errors.

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

        Robust approach: treat all non-warriors as farmers for allocation purposes.
        """
        # Warriors are explicitly those with role "Warrior"
        warriors = [c for c in components if self._is_role(c, "warrior")]
        # Treat all non-warriors (including unknowns) as farmers for allocation
        farmers = [c for c in components if not self._is_role(c, "warrior")]

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
                mapping[ farmers[idx] ] = "spawn farmer"
                assigned.add(farmers[idx])
                idx += 1
        # Next 2*s_w -> spawn warrior
        for _ in range(2 * s_w):
            if idx < total_farmers:
                mapping[ farmers[idx] ] = "spawn warrior"
                assigned.add(farmers[idx])
                idx += 1
        # Remaining -> farm
        for i in range(idx, total_farmers):
            mapping[ farmers[i] ] = "farm"
            assigned.add(farmers[i])

        # 4) Apply assignments for all farmers
        for f in farmers:
            grp = mapping.get(f, "farm")
            environment.assign_group(f, grp)

        # Note: All villagers (farmers or unknowns) should now be assigned.
        # Warriors were assigned to cave earlier; unknowns are treated as farmers above.

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