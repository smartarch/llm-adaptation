Reasoning and task improvement:
- The previous approach aggressively spawned as many farmers and warriors as possible every village phase, which can leave too many villagers in the cave early and amplify dragon counterattacks, often resulting in losses or slower wins.
- A more robust strategy is to use a staged, risk-aware spawning plan:
  - Early in the game (small step count), emphasize farming to accumulate wheat while keeping most villagers safely in the Village. This builds up wheat reserves for future spawns without risking large numbers in the Cave.
  - Only after some wheat is accumulated and enough Farmers exist to support both farming and future spawns, start spawning Warriors. This provides a rapid DPS boost when there is a buffer of Farmers to sustain wheat production.
  - Throughout, all Warriors should go to the Cave to attack; Farmers stay in the Village to farm or spawn new villagers.
  - Limit per-step spawns to avoid depleting the Village’s defensive capacity too quickly. We cap spawns to small numbers (e.g., up to 2 spawns per type per step) and gate Warrior spawns behind a minimal number of Farmers and available wheat.
- This staged approach should improve DPS growth without exposing too many villagers to dragon counterattacks too early, thereby reducing the expected number of turns to kill the Dragon.

Python code implementing the SmartAdaptation class:

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate Farmers and Warriors currently in the Village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Wheat available in the Farm (default to 0 if not available)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Strategy: staged spawning
        # 1) Early steps: favor farming (avoid too many Warriors in Cave too soon)
        max_farm_spawns = 0
        if len(farmers) >= 2:
            # Cap farmer spawns to 2 per step to avoid depleting Village
            max_farm_spawns = min(len(farmers) // 2, int(wheat // 10), 2)

        used_farmers_for_farm_spawns = 2 * max_farm_spawns
        remaining_farmers_after_farm_spawns = farmers[used_farmers_for_farm_spawns:]

        wheat_after_farm_spawns = wheat - 10 * max_farm_spawns

        # 2) Spawn Warriors: only after we have some Farmers and wheat
        max_war_spawns = 0
        if step >= 3 and len(remaining_farmers_after_farm_spawns) >= 2:
            max_war_spawns = min(
                len(remaining_farmers_after_farm_spawns) // 2,
                int(wheat_after_farm_spawns // 12),
                2  # cap to at most 2 warrior spawns per step to reduce risk
            )

        used_farmers_for_war_spawns = 2 * max_war_spawns
        farmers_for_war_spawn = remaining_farmers_after_farm_spawns[:used_farmers_for_war_spawns]

        # 3) Remaining Farmers go to farming (or spawn/ farm if needed)
        remaining_farmers_final = remaining_farmers_after_farm_spawns[used_farmers_for_war_spawns:]

        # Assign spawn groups
        for c in farmers[:used_farmers_for_farm_spawns]:
            environment.assign_group(c, "spawn farmer")

        for c in farmers_for_war_spawn:
            environment.assign_group(c, "spawn warrior")

        for c in remaining_farmers_final:
            environment.assign_group(c, "farm")

        # All Warriors should go to the Cave to attack
        for c in warriors:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: keep Warriors attacking; Farmers return to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```