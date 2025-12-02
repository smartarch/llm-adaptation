```py
"""
SmartAdaptation v4: refined, risk-aware and step-cognizant spawning strategy

Rationale:
- All Warriors should be in the Cave to attack the Dragon as soon as possible.
- Farmers provide Wheat to enable spawning; we must balance growing Wheat with increasing DPS.
- Spawns require 2 villagers in the spawn group and a Wheat cost (10 for spawn farmer, 12 for spawn warrior).
- Dragon can retaliate in the Cave; we want to keep Cave populations healthy while still ramping up DPS.
- This version uses a more nuanced, step- and Dragon HP-aware spawning policy:
  - Always send all Warriors to the Cave (attack) immediately.
  - In the Village, spawn farmers first to boost Wheat, but cap per-step spawns to avoid draining Wheat too aggressively.
  - Spawn Warriors only when:
    - Dragon HP is reasonably low (hard cap) or
    - We are in late steps where DPS can be ramped without risking the Wheat buffer.
- The strategy aims to reach a kill within 30 steps by keeping a steady Wheat growth while enabling targeted DPS growth.

Implementation details:
- assign_in_village:
  - Move all Warriors to the Cave.
  - Compute max_farm_spawn with a per-step cap (up to 2 spawn-farmer events per step, i.e., up to 4 farmers).
  - After farmer spawns, compute remaining Farmers and Wheat.
  - Compute max_war_spawn only if the Dragon HP threshold is met (or late steps), respecting Wheat and available Farmers.
  - Assign 2*max_farm_spawn Farmers to "spawn farmer".
  - Assign 2*max_war_spawn Farmers to "spawn warrior".
  - Remaining Farmers go to "farm".
- assign_in_cave:
  - Warriors go to "attack".
  - Farmers go to "village".

Note:
- This strategy remains deterministic given the observed state per step and avoids aggressive, unbounded spawning early on.

"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        F = len(farmers)
        W = len(warriors)

        # Wheat available at the Farm
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = environment.farm.wheat

        # Dragon health (if observable)
        dragon_hp = None
        if hasattr(environment, "dragon") and hasattr(environment.dragon, "hp"):
            dragon_hp = environment.dragon.hp

        # 1) Move all Warriors to Cave (to attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmer spawns: up to a per-step cap, respecting Wheat
        # Per-step cap: at most 2 spawn-farmer events -> up to 4 farmers
        max_farm_spawn_events = min(F // 2, wheat // 10, 2)

        # Wheat left after farmer spawns
        wheat_after_farm = max(0, wheat - max_farm_spawn_events * 10)

        # Remaining farmers after allocating 2 per farmer-spawn
        remaining_farmers = F - max_farm_spawn_events * 2

        # 3) Warrior spawns: conditional on HP or late-step progression
        max_war_spawn_events = 0
        if dragon_hp is not None and dragon_hp <= 25:
            max_war_spawn_events = min(remaining_farmers // 2, wheat_after_farm // 12)
        elif step >= 20:
            # Late-stage opportunistic spawns
            max_war_spawn_events = min(remaining_farmers // 2, wheat_after_farm // 12)

        # 4) Assign to spawn groups and remaining farming
        idx = 0
        to_spawn_farmers = max_farm_spawn_events * 2
        for _ in range(to_spawn_farmers):
            if idx < F:
                environmental = farmers[idx]
                environment.assign_group(environmental, "spawn farmer")
                idx += 1

        to_spawn_warriors = max_war_spawn_events * 2
        for _ in range(to_spawn_warriors):
            if idx < F:
                environment.assign_group(farmers[idx], "spawn warrior")
                idx += 1

        # 5) Remaining farmers go to farming
        for j in range(idx, F):
            environment.assign_group(farmers[j], "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors should attack, Farmers should return to the Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```