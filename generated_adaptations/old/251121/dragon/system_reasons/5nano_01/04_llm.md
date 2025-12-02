Reasoning and updated adaptation strategy

Goal and constraints recap:
- All Warriors must go to the Cave and then attack the Dragon.
- All Farmers must stay in the Village (except those placed in spawn groups for generating new villagers).
- Spawn mechanics provide a way to grow Farmers and Warriors using pairs of villagers and a wheat cost.
- We want the Dragon attacked early (at least once by step 15) and to grow our army so we have a reasonable chance to kill it quickly.
- We should balance spawning with farming to keep wheat production alive for further spawns.

What to improve:
- Spawn policy should be less greedy on the village wheat and farmers to avoid starving farming, while still guaranteeing “a few” new villagers are spawned early.
- Use a small, deterministic cap on how many new villagers we spawn per step, with a bias toward early farmers (to increase wheat production) and then toward warriors (to increase DPS).
- Tie spawning decisions to step and Dragon HP to adapt to the urgency: more aggressive early on when the Dragon HP is high and we have wheat; taper spawns later or when wheat is tight.
- Ensure the basic rule that all Warriors go to the Cave and all Farmers stay in the Village remains intact.

Strategy description:
- In assign_in_village:
  - Move all Warriors to the Cave (group "cave").
  - Keep Farmers in the Village as the default (group "farm"), but allocate a small, bounded number of Farmers to spawn groups to grow the force:
    - Spawn Farmer group to create new Farmers: requires 2 Farmers and 10 wheat per new Farmer.
    - Spawn Warrior group to create new Warriors: requires 2 Farmers and 12 wheat per new Warrior.
  - Spawn plan is deliberately capped to avoid starving farming:
    - Compute a dynamic cap for spawning based on step and dragon HP, prefer up to a few (e.g., up to 3) new Farmers per step, and up to a few new Warriors per step (e.g., up to 3), constrained by available Farmers and Wheat.
    - Always leave at least a minimal number of Farmers for farming when possible, so Wheat production continues to fuel future spawns.
  - The rest of Farmers stay in the Village and farm (group "farm").
- In assign_in_cave:
  - All Warriors go to "attack" to attack the Dragon.
  - Farmers in the Cave go to the Village (group "village"), staying in the Village as required.

This approach aims to:
- Guarantee early Dragon engagement by moving all Warriors to the Cave promptly.
- Provide a measured but non-trivial number of new Farmers and Warriors early to improve wheat production and DPS.
- Adapt spawning to the game state (step and Dragon HP) to maximize effectiveness without starving wheat production.

Code implementation:
```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _compute_spawns(self, step, dragon_hp, F, wheat):
        """
        Compute how many new Farmers and Warriors to spawn this step.
        Rules (balanced and adaptive):
        - We spawn at most a small number to avoid starving farming.
        - Prefer to spawn up to 3 Farmers per step if resources allow.
        - Then spawn up to 3 Warriors per step with remaining resources.
        - Spawns are bounded by wheat and by available Farmers (2 farmers per new unit).
        - We adapt caps based on step and dragon HP to aggressively spawn early when urgency is high.
        """
        if F < 2 or wheat < 10:
            return 0, 0

        # Dynamic caps: more aggressive early, taper later
        if step < 6:
            cap_farm = 3
            cap_war = 3
        elif step < 12:
            cap_farm = 2
            cap_war = 2
        else:
            cap_farm = 1
            cap_war = 2  # still allow some war spawns later if resources permit

        # First, try to spawn Farmers
        max_farm_spawns = min(F // 2, wheat // 10, cap_farm)

        # Update resources after potential farmer spawns
        wheat_after_farm = wheat - max_farm_spawns * 10
        remaining_farmers = F - max_farm_spawns * 2

        # Then try to spawn Warriors with remaining resources
        max_war_spawns = min(remaining_farmers // 2, wheat_after_farm // 12, cap_war)

        # Optional: guard against extremely aggressive bursts when dragon HP is very low
        # If dragon HP is low and we already have enough warriors, reduce spawns a bit
        if dragon_hp is not None and dragon_hp <= 10:
            max_farm_spawns = max(0, max_farm_spawns - 1)
            max_war_spawns = max(0, max_war_spawns - 1)

        return max_farm_spawns, max_war_spawns

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        In the Village:
        - Move all Warriors to the cave (group "cave").
        - Farmers stay in village by default (group "farm"), but we may spawn a few new Farmers and Warriors
          using "spawn farmer" and "spawn warrior" groups, to grow the population.
        - The rest of Farmers remain in the "farm" group.
        """
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Current wheat available in the Farm
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Dragon HP (for adaptive spawning)
        dragon_hp = getattr(environment.dragon, "hp", None)

        # Compute spawn plan
        spawn_farm_n, spawn_war_n = self._compute_spawns(step, dragon_hp, len(farmers), wheat)

        # Indexes for selecting villagers to spawn groups
        # Warriors all go to cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # Mark which farmers are assigned to spawn groups
        to_spawn_farm = farmers[:2 * spawn_farm_n] if spawn_farm_n > 0 else []
        to_spawn_war = farmers[2 * spawn_farm_n: 2 * spawn_farm_n + 2 * spawn_war_n] if spawn_war_n > 0 else []

        used_for_spawns = set(to_spawn_farm) | set(to_spawn_war)

        for c in to_spawn_farm:
            environment.assign_group(c, "spawn farmer")
        for c in to_spawn_war:
            environment.assign_group(c, "spawn warrior")

        # Remaining farmers go to farming
        for c in farmers:
            if c in used_for_spawns:
                continue
            environment.assign_group(c, "farm")

        # Non-farmer components (if any) should stay in village by default
        for c in components:
            if getattr(c, "role", None) not in ("Farmer", "Warrior"):
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave:
        - Warriors attack the Dragon: assign to "attack".
        - Farmers go back to the Village: assign to "village".
        """
        for v in components:
            role = getattr(v, "role", None)
            if role == "Warrior":
                environment.assign_group(v, "attack")
            else:
                # Farmers (and any others) go to Village
                environment.assign_group(v, "village")
```