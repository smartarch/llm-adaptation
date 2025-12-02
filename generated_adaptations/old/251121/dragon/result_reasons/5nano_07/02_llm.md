Reasoning and adaptation strategy

Goal and constraints recap:
- Kill the Dragon as fast as possible, within 30 steps.
- All Warriors must eventually go to the Cave and attack the Dragon.
- All Farmers should stay in the Village (but they can spawn new villagers using special spawn groups).
- You must spawn some new Farmers and Warriors to increase killing power.
- The Dragon should be attacked at least once in the first 15 steps.
- At least half of the Warriors should be in the Cave most of the time.

Key observations:
- Warriors are the primary damage dealers. Move all Warriors to the Cave early so they can attack the Dragon promptly.
- Farmers should stay in the Village to farm and to trigger spawns. We can use “spawn farmer” and “spawn warrior” subgroups to produce new villagers using wheat resources.
- Spawns require both a minimum number of villagers in the spawn group and a minimum wheat stock. We should conditionally assign a small number of Farmers to spawn groups when wheat and step budget permit, so we generate additional Farmers and Warriors over time.
- In the cave phase, once Warriors arrive, we want them to attack the Dragon (group “attack”). Farmers in the cave should return to the Village (group “village”).

Strategy outline:
- In assign_in_village:
  - Move all Warriors to the cave (temporary) so they will be in position to attack in the cave phase.
  - Keep Farmers in the Village by default in the “farm” group.
  - Optionally designate a small number of Farmers to the spawn groups to trigger spawns:
    - If step <= 15 and there are at least 4 Farmers and wheat >= 10, assign 2 Farmers to “spawn farmer”.
    - If there are additional Farmers (not in the spawn farmer pool) and wheat >= 12, assign 2 more Farmers to “spawn warrior”. This yields new Warriors when the spawn condition is satisfied by the environment.
  - Ensure that Warriors are placed in cave and Farmers stay in village (or join spawn groups which still reside in the village).
- In assign_in_cave:
  - Assign all Warriors to the “attack” group (they will attack the Dragon now that they are in the Cave).
  - Assign all Farmers to the “village” group (return to the Village).

This approach guarantees:
- The Dragon is attacked early (Warriors are moved to cave and set to attack promptly).
- All Warriors eventually attack, satisfying “All Warriors should attack the Dragon after moving to the Cave.”
- The Cavalcade of Warriors will be sufficient in number to meet the “at least half of the warriors in the Cave most of the time” requirement (we keep all Warriors on the move to cave, and then to attack).
- Spawning occurs in a controlled, step-bounded way to raise the number of Farmers and Warriors, increasing DPS over time without starving wheat resources.

Python implementation

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Classify villagers currently in the Village
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Decide on spawn groups (stay in the Village but trigger spawns)
        spawn_farmers = []
        spawn_warriors = []

        # Wheat available for spawning decisions
        wheat = getattr(environment.farm, "wheat", 0)

        # Spawn up to 2 Farmers if there are enough Farmers and wheat
        if step <= 15 and len(farmers) >= 4 and wheat >= 10:
            spawn_farmers = farmers[:2]

        # Attempt to spawn Warriors using remaining Farmers if there is enough wheat
        remaining_for_warrior = [f for f in farmers if f not in spawn_farmers]
        if step <= 15 and len(remaining_for_warrior) >= 2 and wheat >= 12:
            spawn_warriors = remaining_for_warrior[:2]

        spawn_farm_set = set(spawn_farmers)
        spawn_war_set = set(spawn_warriors)

        # Assign groups for Farmers
        for f in farmers:
            if f in spawn_farm_set:
                environment.assign_group(f, "spawn farmer")
            elif f in spawn_war_set:
                environment.assign_group(f, "spawn warrior")
            else:
                # Default: stay in Village and farm
                environment.assign_group(f, "farm")

        # Assign groups for Warriors: move to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack, Farmers go back to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")
```