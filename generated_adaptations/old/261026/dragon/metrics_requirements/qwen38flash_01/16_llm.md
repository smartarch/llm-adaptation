

# Critical Realization

I've been hardcoding group names like `"spawn warrior"` and `"spawn farmer"`, but the prompt's description of `assign_in_village` actually lists the groups as `"farm"`, `"cave"`, and `"spawn"` (singular, not type-suffixed). More importantly, the function signature receives **`group_ids`** — the authoritative list of valid group names for that environment. I never used it. This means every `environment.assign_group(unit, "spawn warrior")` call likely referred to a non-existent group, so my units were effectively unassigned every turn — producing nothing, attacking nothing, forever losing.

## Fix

Use `group_ids` to dynamically discover valid group names via substring matching (`"cave"`, `"farm"`, `"spawn"`, `"attack"`, `"village"`), with safe fallbacks. Assign every unit every turn — no unassigned units, ever.

## Strategy
- Warriors in village → "cave" group (substring match).
- Farmers: pair up into the "spawn" group (engine decides warrior vs farmer); any odd farmer farms.
- Warriors in cave → "attack" group, every turn, no exceptions.
- Non-warriors in cave → sent back to village.
- All group names resolved at call time from `group_ids`, so I adapt to whatever the simulator actually uses.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @staticmethod
    def _find_group(group_ids, *keywords, default=None):
        """Search group_ids (list/iterable) for an entry containing any keyword."""
        try:
            ids = list(group_ids)
        except TypeError:
            ids = []
        # Try each keyword in priority order.
        for kw in keywords:
            for g in ids:
                if kw in str(g).lower():
                    return g
        return default

    def assign_in_village(self, components, environment, group_ids, step):
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]

        cave_group  = self._find_group(group_ids, "cave",  default="cave")
        farm_group  = self._find_group(group_ids, "farm",  default="farm")
        spawn_group = self._find_group(group_ids, "spawn", default="spawn")

        # Every warrior in the village must move to the cave immediately.
        for w in warriors:
            environment.assign_group(w, cave_group)

        if not farmers:
            return

        # Pair farmers into the spawn group so new warriors keep arriving.
        num_pairs = len(farmers) // 2
        for f in farmers[: num_pairs * 2]:
            environment.assign_group(f, spawn_group)
        for f in farmers[num_pairs * 2:]:
            environment.assign_group(f, farm_group)

    def assign_in_cave(self, components, environment, group_ids, step):
        attack_group  = self._find_group(group_ids, "attack",  default="attack")
        village_group = self._find_group(group_ids, "village", default="village")

        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, attack_group)
            else:
                environment.assign_group(c, village_group)
```