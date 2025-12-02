Reasoning and updated strategy:

- Core goals kept:
  - All Warriors should end up in the Cave to attack the Dragon.
  - All Farmers stay in the Village (but can seed spawns to grow the population).
  - Spawn mechanics are used conservatively to avoid starving the wheat economy.
  - The Dragon must be attacked early (within the first 15 steps), and we want a steady DPS boost from spawned villagers without compromising early advantage.

- What’s different from before:
  - Spawn logic is more restrained and deterministic: we only attempt spawns when there are enough Farmers and enough wheat, and we limit to at most one seed per type per step unless wheat is abundant.
  - We explicitly keep all Warriors heading to the Cave early (and thus ready to attack as soon as they arrive in the Cave).
  - Farmers are kept in the Village baseline, with only small, controlled seed attempts to maintain wheat production while growing the population.

- How this helps:
  - Early Dragon engagement is guaranteed by routing all Warriors to the Cave.
  - A gradual but steady population increase increases total DPS over time without collapsing the Wheat economy.
  - By spawning only when thresholds are met, we reduce the risk of starving the farm and losing DPS in the short term.

Code:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # In the Village:
        # - Farmers stay in the Village to farm
        # - Warriors head to the Cave to attack
        # - Spawn farmers/warriors conservatively when wheat allows
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default assignments: Farmers -> farm, Warriors -> cave
        for c in farmers:
            environment.assign_group(c, "farm")
        for c in warriors:
            environment.assign_group(c, "cave")

        # Read current wheat (robust to missing data)
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # Spawn farmer: if we have at least 4 farmers and wheat >= 10, seed 1 new Farmer
        spawn_farm = []
        if len(farmers) >= 4 and wheat >= 10:
            spawn_farm = farmers[:2]
            for c in spawn_farm:
                environment.assign_group(c, "spawn farmer")

        # Spawn warrior: if there are enough remaining villagers to seed and wheat >= 12
        remaining_for_war_spawn = [c for c in farmers + warriors if c not in spawn_farm]
        spawn_war = []
        if len(remaining_for_war_spawn) >= 2 and wheat >= 12:
            spawn_war = remaining_for_war_spawn[:2]
            for c in spawn_war:
                environment.assign_group(c, "spawn warrior")

        # End of village assignment. In subsequent steps, assign_in_cave will handle moving to attack.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack the Dragon; Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```