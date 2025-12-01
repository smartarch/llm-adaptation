Reasoning and adaptation strategy

Problem overview:
- Warriors should immediately head to the Cave and attack the Dragon. Farmers stay in the Village to farm wheat and optionally spawn more villagers.
- Spawning rules: to spawn a new villager, at least two villagers must be assigned to a spawn group and there must be sufficient wheat:
  - Spawn a Farmer: 2 villagers in the "spawn farmer" group and 10 wheat.
  - Spawn a Warrior: 2 villagers in the "spawn warrior" group and 12 wheat.
- Farming yields wheat per farmer per step: Farmers yield 5 wheat, Warriors yield 2 wheat (when farming).
- The Dragon can retaliate, and we must ensure enough villagers survive while killing the Dragon within 30 steps.

Strategy summary:
- In village:
  - Move all Warriors to the cave group (to go attack immediately).
  - Manage Farmers with a simple growth plan:
    - Use a portion of Farmers to form the "spawn farmer" group to create new Farmers as wheat allows.
    - Use another portion of Farmers to form the "spawn warrior" group to create more Warriors as wheat allows, ensuring we maintain a core farm capacity.
    - The remaining Farmers stay in the "farm" group to keep wheat production high.
  - This balances immediate Dragon damage via Warriors while growing the population to sustain long-term DPS and survivability.
- In cave:
  - All Warriors stay in the cave and are assigned to the "attack" group to fight the Dragon.
  - All Farmers return to the Village (assigned to "village") to continue farming or spawning.

Implementation notes:
- The strategy assigns groups deterministically per step based on current components and available wheat.
- The spawning logic uses current wheat and the number of available Farmers to determine how many pairs can form the spawn groups, with a cap given by wheat resources.
- This approach ensures that all Warriors go to the cave to attack, while Farmers remain in the Village to farm or spawn new villagers as Wheat permits.

Now, the Python implementation:

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Partition villagers in the Village into groups:
        # - farm: stay in Village and farm
        # - cave: go to the Cave (for Warriors)
        # - spawn farmer: for every two villagers and 10 wheat, spawn a new Farmer
        # - spawn warrior: for every two villagers and 12 wheat, spawn a new Warrior

        # Collect villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors should go to the cave (in village).
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Handle Farmers: decide how many go to spawn groups vs farming
        # We will allocate farmers sequentially to spawn groups based on available wheat.
        spawn_farm_cap = 0
        spawn_war_cap = 0

        # Wheat available for spawning (use current wheat; spawning will consume wheat in the environment)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # Maximum number of new Farmers we can spawn this step (by pair constraint)
        spawn_farm_cap = min(len(farmers) // 2, wheat // 10)

        # After reserving space for spawn farmers, determine how many farmers can spawn warriors
        # Use remaining wheat after potential farm spawns.
        remaining_wheat_after_farm = wheat - (spawn_farm_cap * 10)
        remaining_farmers_after_farm = len(farmers) - (spawn_farm_cap * 2)
        spawn_war_cap = min(remaining_farmers_after_farm // 2, remaining_wheat_after_farm // 12)

        # Assign farmers to groups according to the planning
        idx = 0
        # Spawn farmers: take 2 farmers per spawned farmer
        for _ in range(spawn_farm_cap * 2):
            if idx >= len(farmers):
                break
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1

        # Spawn warriors: take 2 farmers per spawned warrior
        for _ in range(spawn_war_cap * 2):
            if idx >= len(farmers):
                break
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1

        # Remaining farmers go to farming
        for j in range(idx, len(farmers)):
            environment.assign_group(farmers[j], "farm")

        # Note: Some villagers could be neither farmer nor warrior (if such exist); ensure they
        # are grouped in a safe default (farm) if they slip through.
        # If there are any components left unassigned in village (unexpected), assign them to farm.
        # (This is a safety net; normally all farmers are accounted for above.)

        # End of assign_in_village

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: - Warriors go to attack the Dragon
        # - Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers (and any other non-Warrior) return to Village
                environment.assign_group(c, "village")
```