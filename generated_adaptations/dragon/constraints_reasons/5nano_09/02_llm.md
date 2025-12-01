Reasoning and adaptation strategy

Goal and constraints recap
- All Warriors should go to the Cave, then attack the Dragon. All Farmers should stay in the Village.
- We want to attack the Dragon early (at least once in the first 15 steps) and continue applying pressure.
- We should spawn new villagers (both Farmers and Warriors) to increase DPS and wheat production, but spawning requires two villagers in a spawn group and some wheat (10 for a Farmer, 12 for a Warrior).
- We want to keep the majority of Warriors in the Cave to attack, and keep Farmers in the Village (but we can use some Farmers as “spawn” candidates in the Village to growing the population).

Strategy outline
- assign_in_village:
  - Move all Warriors to the Cave (group 'cave'), so they will eventually attack from the Cave.
  - Farmers stay in the Village by default in the 'farm' group, but we will opportunistically spawn new villagers:
    - Use two Farmers in the "spawn farmer" group to spawn one new Farmer, provided there is at least 10 wheat.
    - Use two other Farmers in the "spawn warrior" group to spawn one new Warrior, provided there is at least 12 wheat.
    - To avoid exhausting farmers, cap spawns per step (e.g., up to 2 spawns per type per step).
  - Any remaining Farmers after allocating spawns go to the 'farm' group (continue farming to grow wheat).
- assign_in_cave:
  - All Warriors in the Cave should be assigned to the 'attack' group so they actually attack the Dragon.
  - All Farmers in the Cave should be assigned to the 'village' group to move back to the Village (they should not stay in the Cave).

This approach guarantees:
- All Warriors reach the Cave and attack early (fulfills the “attack in the first 15 steps” and “all warriors in cave” requirements).
- Farmers stay in the Village and continue farming, with some being used as spawn material to increase both the farmer and warrior populations as wheat allows.
- There will be spawning events early enough to increase DPS with new villagers, aiding in killing the Dragon within 30 steps.

Code
```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate farmers and warriors in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All warriors should go to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawn planning among farmers
        remaining_farmers = list(farmers)  # copy

        to_spawn_farm = []  # two villagers -> spawn one new Farmer
        to_spawn_war = []   # two villagers -> spawn one new Warrior

        wheat = environment.farm.wheat if hasattr(environment, "farm") else 0

        # Try to spawn up to 2 farmers this step
        spawn_farm_slots = 2
        while len(remaining_farmers) >= 2 and wheat >= 10 and spawn_farm_slots > 0:
            a = remaining_farmers.pop(0)
            b = remaining_farmers.pop(0)
            to_spawn_farm.extend([a, b])
            wheat -= 10
            spawn_farm_slots -= 1

        # Try to spawn up to 2 warriors this step
        spawn_war_slots = 2
        while len(remaining_farmers) >= 2 and wheat >= 12 and spawn_war_slots > 0:
            a = remaining_farmers.pop(0)
            b = remaining_farmers.pop(0)
            to_spawn_war.extend([a, b])
            wheat -= 12
            spawn_war_slots -= 1

        # 3) Assign groups for spawning
        for c in to_spawn_farm:
            environment.assign_group(c, "spawn farmer")
        for c in to_spawn_war:
            environment.assign_group(c, "spawn warrior")

        # 4) Remaining farmers stay in the village and farm
        for c in remaining_farmers:
            environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack; Farmers should go back to village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```