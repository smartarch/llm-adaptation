"""
SmartAdaptation v5: dynamic, risk-aware and step-cognizant spawning strategy (refined)

Rationale:
- All Warriors should be in the Cave to attack the Dragon as soon as possible.
- Farmers provide Wheat to enable spawning. We must balance Wheat growth with increasing DPS.
- Spawns require 2 villagers in the spawn group and have Wheat costs (10 for spawn farmer, 12 for spawn warrior).
- The Dragon can retaliate, potentially wiping Cave villagers. Therefore we want to limit the number of
  farmers that stay in the Cave at the same time and grow Wheat efficiently before ramping up DPS.
- This version introduces a more nuanced, state-aware spawning policy:
  - Always send all Warriors to the Cave (attack) immediately.
  - In the Village, spawn farmers first to boost Wheat, but cap per-step spawns to avoid depleting Wheat too aggressively.
  - Spawn Warriors only when Dragon HP is sufficiently low or when late steps justify ramping DPS without starving Wheat reserves.
- The strategy aims to kill the Dragon within 30 steps by keeping a steady Wheat growth while enabling targeted DPS growth.

Adaptation details:
- assign_in_village:
  - Move all Warriors to the Cave.
  - Compute max_farm_spawn_events with a per-step cap (up to 4 farmers per step, i.e., 2 events).
  - After farmer spawns, compute remaining Farmers and Wheat.
  - Compute max_war_spawn_events only if Dragon HP is low (or late steps) and Wheat allows.
  - Assign 2*max_farm_spawn Farmers to "spawn farmer".
  - Assign 2*max_war_spawn Farmers to "spawn warrior".
  - Remaining Farmers go to "farm".
- assign_in_cave:
  - Warriors go to "attack".
  - Farmers go to "village".

Note:
- This strategy remains deterministic per step and adapts to dragon health and game progression to optimize turn count.

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
        if dragon_hp is not None:
            if dragon_hp <= 30:
                max_war_spawn_events = min(remaining_farmers // 2, wheat_after_farm // 12)
            elif step >= 15:
                # Late-stage opportunistic spawns
                max_war_spawn_events = min(remaining_farmers // 2, wheat_after_farm // 12)
        else:
            if step >= 20:
                max_war_spawn_events = min(remaining_farmers // 2, wheat_after_farm // 12)

        # 4) Assign to spawn groups and remaining farming
        idx = 0
        to_spawn_farmers = max_farm_spawn_events * 2
        for _ in range(to_spawn_farmers):
            if idx < F:
                environment.assign_group(farmers[idx], "spawn farmer")
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