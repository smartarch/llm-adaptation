Reasoning and adaptation strategy

Goal recap:
- All Warriors should always go to the Cave and attack the Dragon.
- Farmers stay in the Village and either farm (produce wheat) or spawn new villagers when enough wheat is available.
- Spawning rules in Village:
  - spawn farmer: for every two villagers assigned to this group and 10 wheat, a new Farmer is spawned.
  - spawn warrior: for every two villagers assigned to this group and 12 wheat, a new Warrior is spawned.
- In Cave, Warriors attack the Dragon; Farmers should return to the Village.
- The Dragon has HP and the Farm has wheat; spawns consume wheat.

Strategy description:
- assign_in_village:
  - Move all Warriors from Village to the cave group immediately (they will end up in Cave to attack).
  - For Farmers:
    - Try to spawn new Farmers first, as long as there is enough wheat for 10 wheat per 2 farmers. We allocate 2 Farmers per possible spawn to the "spawn farmer" group greedily.
    - After allocating potential Farmers to spawn farmers, use remaining Farmers to spawn Warriors if there is enough wheat for 12 wheat per 2 farmers. Allocate 2 Farmers per possible spawn to the "spawn warrior" group.
    - Any Farmers not allocated to spawn groups are assigned to the "farm" group (regular farming).
  - This strategy maximizes population growth when resources allow, while ensuring Warriors consistently march to the Cave to confront the Dragon.
- assign_in_cave:
  - All Warriors in the Cave are assigned to the "attack" group.
  - All Farmers in the Cave are assigned to the "village" group, sending them back to the Village to continue farming or spawning.

This design adheres to the requirement that every component is assigned to exactly one group. It uses the environment.farm.wheat to determine how many spawns are possible (bounded by two-villager per spawn rule and by available wheat). It ensures Warriors always end up in the attack path, and Farmers are managed to sustain wheat production and possible population growth through spawning.

Python code

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, 'role', None) == 'Farmer']
        warriors = [c for c in components if getattr(c, 'role', None) == 'Warrior']

        # 1) All Warriors go to the Cave (to attack later)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Handle Farmers: spawn growth first, then farming
        # Current wheat in the Farm
        wheat = getattr(getattr(environment, 'farm', None), 'wheat', 0)

        # How many spawns of Farmers can we support?
        max_spawn_farmers = min(wheat // 10, len(farmers) // 2)

        # Assign 2*max_spawn_farmers farmers to "spawn farmer"
        if max_spawn_farmers > 0:
            to_spawn_farm = farmers[:2 * max_spawn_farmers]
            for c in to_spawn_farm:
                environment.assign_group(c, "spawn farmer")

        remaining_farmers = farmers[2 * max_spawn_farmers:]

        # Recompute wheat (spawns will consume wheat; environment handles it)
        wheat_after_farm_spawns = getattr(getattr(environment, 'farm', None), 'wheat', 0)

        # 3) Spawn Warriors if possible with remaining farmers
        max_spawn_warriors = min(wheat_after_farm_spawns // 12, len(remaining_farmers) // 2)
        if max_spawn_warriors > 0:
            to_spawn_war = remaining_farmers[:2 * max_spawn_warriors]
            for c in to_spawn_war:
                environment.assign_group(c, "spawn warrior")

        remaining_after_spawns = remaining_farmers[2 * max_spawn_warriors:]

        # 4) Remaining Farmers go to farming in Village
        for c in remaining_after_spawns:
            environment.assign_group(c, "farm")

        # Note: If there are no Farmers, Warriors were already moved to cave.
        # If there are none in village, this function gracefully does nothing beyond Warrior moves.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In Cave: Warriors should attack, Farmers should go back to Village
        for c in components:
            if getattr(c, 'role', None) == 'Warrior':
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```