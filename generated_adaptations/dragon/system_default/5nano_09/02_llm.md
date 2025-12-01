Reasoning and adaptation strategy

Goal and constraints recap
- All Warriors should be sent to the Cave to attack the Dragon.
- Farmers stay in the Village to farm or to spawn new villagers using the stock of wheat.
- Spawning rules: For every two villagers assigned to "spawn farmer" and at least 10 wheat, a new Farmer is spawned. For every two villagers assigned to "spawn warrior" and at least 12 wheat, a new Warrior is spawned.
- The Dragon starts with 50 HP and the game ends in victory when the Dragon dies or a loss if it’s not killed within 30 steps.
- We can only move villagers between groups; the actual spawn effect consumes wheat and creates new villagers (handled by the environment).

Strategy overview
- Village phase:
  - Move all Warriors to the cave group so they will travel to the Cave and fight in the next phase.
  - Farmers stay in the Village and contribute to farming most of the time.
  - Use a simple, wheat-aware spawning heuristic to gradually grow the army:
    - If there are at least two Farmers and wheat >= 12, assign two Farmers to the "spawn warrior" group to produce a new Warrior (consumes 12 wheat).
    - Else if there are at least two Farmers and wheat >= 10, assign two Farmers to the "spawn farmer" group to produce a new Farmer (consumes 10 wheat).
    - The remaining Farmers stay in the "farm" group to keep producing wheat.
- Cave phase:
  - All Warriors in the Cave attack the Dragon (group "attack").
  - Farmers in the Cave (if any, due to edge cases) are sent back to the Village (group "village"), since Farmers should stay in the Village.

This plan prioritizes converting wheat into military strength when feasible, while ensuring farmers keep farming to sustain more spawns in future steps. It adheres to the requirement that each component is assigned to exactly one group and explicitly reassigns any component to its intended group in every step.

Python implementation
- The class SmartAdaptation derives from the provided base class DragonHuntAdaptation.
- It implements assign_in_village and assign_in_cave according to the strategy described above.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Organize villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Send all Warriors to the Cave (they will attack in the cave phase)
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning logic for Farmers (spawn events use two villagers + wheat)
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        spawn_warrior_pair = []
        spawn_farmer_pair = []
        # Prefer spawning a Warrior if we have enough wheat and at least 2 Farmers available
        if len(farmers) >= 2 and wheat >= 12:
            spawn_warrior_pair = farmers[:2]
        # If Warrior spawn isn't triggered, try to spawn a Farmer
        elif len(farmers) >= 2 and wheat >= 10:
            spawn_farmer_pair = farmers[:2]

        assigned_spawn = set(spawn_warrior_pair) | set(spawn_farmer_pair)

        # Assign groups for Farmers
        for f in farmers:
            if f in spawn_warrior_pair:
                environment.assign_group(f, "spawn warrior")
            elif f in spawn_farmer_pair:
                environment.assign_group(f, "spawn farmer")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave, send Warriors to attack the Dragon; Farmers go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers (and any other non-warrior types) go to Village
                environment.assign_group(c, "village")
```