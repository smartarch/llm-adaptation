```py
"""
SmartAdaptation v3: dynamic, risk-aware spawning to accelerate Dragon kill

Rationale:
- All Warriors must go to the Cave and attack the Dragon. Farmers stay in the Village to farm or spawn new villagers.
- Spawning consumes Wheat and requires 2 villagers in the spawn group.
- Dragon retaliation is dangerous: it can damage all villagers in the Cave or eat one random Cave villager.
  Therefore we want to minimize the number of farmers that share the Cave with Warriors, while still
  growing Wheat fast enough to unlock more spawns and escalate damage early.
- This version introduces step- and Dragon-health-aware spawning:
  - Always send all Warriors to the Cave (attack) as soon as possible.
  - In the Village, prioritize Farmer spawns (spawn farmer) to quickly boost Wheat production, but cap
    how many such spawns happen in a single step to avoid destroying Wheat reserves too aggressively.
  - Only spawn Warriors (spawn warrior) when Dragon HP is sufficiently low or the battle has progressed
    enough to justify accelerating DPS, preventing large numbers of villagers from being hurt in the Cave early.
- The strategy adapts to the current game state (step, dragon HP, Wheat) to try to kill the Dragon within 30 steps.

Adaptation details:
- assign_in_village:
  - Move all Warriors to the Cave (environment.assign_group w, "cave").
  - Compute max possible Farm spawns: max_farm_spawn = min(F // 2, Wheat // 10), capped to a small limit per step.
  - Compute Wheat left after Farm spawns and remaining Farmers.
  - Compute Warrior spawns only if the Dragon is sufficiently weakened (dragon_hp <= 30) or step is late enough.
  - Assign 2*spawn_farmers Farmers to "spawn farmer".
  - Assign 2*spawn_warriors Farmers to "spawn warrior" (from remaining Farmers).
  - Remaining Farmers go to "farm".
- assign_in_cave:
  - Warriors -> "attack"
  - Farmers -> "village"

This approach aims to keep Cave casualties modest while steadily increasing Wheat and DPS, with responsiveness to the Dragon's health.

"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by current role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        F = len(farmers)
        W = len(warriors)

        # Wheat available at the Farm
        wheat = 0
        if hasattr(environment, "farm") and hasattr(environment.farm, "wheat"):
            wheat = environment.farm.wheat

        # Dragon health (may be None if not observable)
        dragon_hp = None
        if hasattr(environment, "dragon") and hasattr(environment.dragon, "hp"):
            dragon_hp = environment.dragon.hp

        # 1) Farmer spawns: as many as possible, but cap per-step to avoid depleting Wheat too fast
        max_farm_spawn = min(F // 2, wheat // 10)
        max_farm_spawn_cap_per_step = 3  # limit to 3 farm-spawn events per step
        max_farm_spawn = min(max_farm_spawn, max_farm_spawn_cap_per_step)

        # Wheat left after farmer spawns
        wheat_after_farm = max(0, wheat - max_farm_spawn * 10)

        # Remaining farmers after allocating 2 per farmer-spawn
        remaining_farmers = F - max_farm_spawn * 2

        # 2) Warrior spawns: only when it makes sense (dragon weakened or late stage)
        max_war_spawn = 0
        if dragon_hp is not None and dragon_hp <= 30:
            max_war_spawn = min(remaining_farmers // 2, wheat_after_farm // 12)
        elif step >= 4:
            # Late-stage opportunistic spawn if Wheat is available
            max_war_spawn = min(remaining_farmers // 2, wheat_after_farm // 12)

        # Assign: move all Warriors to Cave (they will attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 3) Assign 2*max_farm_spawn farmers to "spawn farmer"
        idx = 0
        to_spawn_farmers = max_farm_spawn * 2
        for _ in range(to_spawn_farmers):
            if idx < F:
                environment.assign_group(farmers[idx], "spawn farmer")
                idx += 1

        # 4) Assign 2*max_war_spawn farmers to "spawn warrior"
        to_spawn_warriors = max_war_spawn * 2
        for _ in range(to_spawn_war_spawn):
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