Reasoning for improvement

- Problem focus: Win rate is still 0% in simulations. The previous approach reliably assigns villagers but doesn’t aggressively optimize DPS early enough, and it can be sensitive to edge cases where role data is noisy.
- Key levers to improve win rate:
  - Aggressively increase early DPS by spawning Warriors as soon as wheat allows, while still keeping some farming to generate more wheat for future spawns.
  - Use Dragon HP as a hint to adapt spawning: when HP is high, push for more Warriors; when HP is low, save wheat to finish off the Dragon.
  - Maintain robustness: every component must be assigned exactly once in assign_in_village, and Warriors must go to the Cave. Unknown or mislabelled roles should be treated as Farmers to avoid unassigned components.

Strategy implemented

- assign_in_village:
  - All Warriors go to the Cave (for immediate attack later).
  - Treat all non-Warriors as potential farmers and decide on a dynamic split between:
    - spawn farmer (needs 2 villagers and 10 wheat)
    - spawn warrior (needs 2 villagers and 12 wheat)
    - farm (stay in village)
  - The dynamic split uses:
    - total_farmers = number of non-warriors
    - wheat = current wheat in the Farm
    - dragon_hp = current Dragon HP
    - If dragon_hp > 25, prioritize spawning Warriors: s_f = 0, s_w = min(total_farmers // 2, wheat // 12)
    - Else, compute s_f and s_w normally:
      - s_f = min(total_farmers // 2, wheat // 10)
      - remaining = total_farmers - 2*s_f
      - s_w = min(remaining // 2, wheat // 12)
      - If dragon_hp <= 20, reduce s_w by half to save wheat for finishing
  - Build a definitive mapping so every farmer-like villager is assigned exactly once:
    - First 2*s_f go to "spawn farmer"
    - Next 2*s_w go to "spawn warrior"
    - Remaining go to "farm"
  - Apply mapping to all farmers (non-warriors). This keeps all components assigned and ensures aggressive use of wheat for DPS when warranted.

- assign_in_cave:
  - Warriors -> "attack"
  - Others -> "village" (return to the Village)

This approach aims to improve the win rate by increasing DPS early via Warrior spawns when wheat and HP permit, while preserving robustness against edge cases.

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
        Enhanced strategy:
        - All Warriors -> cave (they will attack in the cave)
        - All other villagers (treated as Farmers for spawning) -> farm, spawn farmer, or spawn warrior
          based on current wheat and dragon HP.
        Spawning decisions are dynamic:
          - If dragon HP > 25: spawn Warriors as much as wheat allows, minimal or zero farmers spawned.
          - Else: compute s_f and s_w normally, with a safeguard to reduce s_w when HP <= 20.
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

        # Dragon HP
        hp = getattr(environment.dragon, "hp", None)

        # 2) Compute spawning allocations
        s_f = 0
        s_w = 0

        # Aggressive Warrior spawning if HP is very high
        if hp is not None and isinstance(hp, int) and hp > 25:
            if wheat_val >= 12:
                s_w = min(total_farmers // 2, wheat_val // 12)
        else:
            if wheat_val >= 10:
                s_f = min(total_farmers // 2, wheat_val // 10)
            remaining = total_farmers - 2 * s_f
            if wheat_val >= 12:
                s_w = min(remaining // 2, wheat_val // 12)
            if hp is not None and isinstance(hp, int) and hp <= 20:
                s_w = max(0, s_w // 2)

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