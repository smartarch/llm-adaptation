Strategy rationale for improving win rate

Goal: Increase the Dragon kill rate while still obeying the assignment rules (all Warriors must go to the Cave and attack; Farmers (and unknowns treated as Farmers) generate Wheat or spawn new villagers when possible). The previous approach ensured assignment correctness but produced very slow progress. The improved strategy focuses on two levers that influence DPS and resources early on:

1) Dynamic spawning driven by wheat and dragon health
- Use current wheat to decide how many pairs of Farmers to allocate to spawn groups:
  - s_f = min(total_farmers // 2, wheat // 10) for spawning Farmers
  - s_w = min((total_farmers - 2*s_f) // 2, wheat // 12) for spawning Warriors
- If the Dragon HP is already low (e.g., <= 20), reduce the Warrior spawning to save wheat for finishing the Dragon, by halving s_w in that case.
- Rationale: Early extra Warriors boost DPS (each deals 3 damage). Spawning uses wheat and some farmers away from farming, but it can pay off by accelerating dragon death.

2) Robust, single-pass assignment with unknown roles
- Treat all non-Warrior villagers as Farmers for the purpose of spawn/farm assignments. This avoids edge cases where some components have unclear role data and ensures every component is assigned exactly once in assign_in_village.
- Always move all Warriors to the cave in village, then apply a single deterministic mapping for farmers/unknowns to either spawn groups or farming.
- This keeps the system predictable and test-friendly while enabling the DPS-oriented strategy.

3) Cave behavior remains simple and effective
- In cave, all Warriors attack the Dragon; any Farmers/unknowns go back to the village to continue farming/spawning.

Code: a final class implementing the above strategy

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
        Enhanced strategy:
        - All Warriors -> cave (they will attack in the cave)
        - All other villagers (treated as Farmers for spawning) -> farm, spawn farmer, or spawn warrior
          based on current wheat and dragon HP.
        Spawning decisions are dynamic:
          s_f = min(total_farmers // 2, wheat // 10)
          s_w = min((total_farmers - 2*s_f) // 2, wheat // 12)
          If dragon HP <= 20, halve s_w to save wheat for finishing.
        """
        # Separate warriors and all others (treated as farmers)
        warriors = [c for c in components if self._is_role(c, "warrior")]
        others = [c for c in components if not self._is_role(c, "warrior")]

        # 1) Move all Warriors to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        total_farmers = len(others)
        current_wheat = getattr(environment.farm, "wheat", 0)
        try:
            wheat_val = int(current_wheat)
        except Exception:
            wheat_val = 0

        # 2) Compute spawning allocations
        s_f = 0
        if wheat_val >= 10:
            s_f = min(total_farmers // 2, wheat_val // 10)

        remaining = total_farmers - 2 * s_f
        s_w = 0
        if wheat_val >= 12:
            s_w = min(remaining // 2, wheat_val // 12)

        # If dragon HP is known and <= 20, reduce Warrior spawning to save wheat
        hp = getattr(environment.dragon, "hp", None)
        if isinstance(hp, int) and hp <= 20:
            s_w = s_w // 2

        # 3) Build a definitive mapping so every 'farmer-like' villager is assigned exactly once
        mapping = {}
        idx = 0
        # First 2*s_f -> spawn farmer
        for _ in range(2 * s_f):
            if idx < total_farmers:
                mapping[others[idx]] = "spawn farmer"
                idx += 1
        # Next 2*s_w -> spawn warrior
        for _ in range(2 * s_w):
            if idx < total_farmers:
                mapping[others[idx]] = "spawn warrior"
                idx += 1
        # Remaining -> farm
        for i in range(idx, total_farmers):
            mapping[others[i]] = "farm"

        # 4) Apply assignments for all 'farmers' (others)
        for v in others:
            grp = mapping.get(v, "farm")
            environment.assign_group(v, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon (Warriors)
        - village: Go to the Village (Farmers/Unknowns)
        """
        for c in components:
            if self._is_role(c, "warrior"):
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```