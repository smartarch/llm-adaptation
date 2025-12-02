"""
Strategy and reasoning:

- Global goals:
  - All Warriors should go to the Cave and attack the Dragon.
  - All Farmers stay in the Village and either farm or participate in villager-spawns to grow the population (both Farmers and Warriors are useful later).

- Village assignment policy:
  - Move every Warrior to the "cave" group in the village step. They will later be placed in the "attack" group in the cave step.
  - For Farmers, use a simple spawn-based growth mechanism:
    - Reserve at least one Farmer to stay in the Village for farming (to keep wheat production ongoing).
    - Use the remaining Farmers to form the "spawn farmer" group in pairs. For every two Farmers assigned to this group and 10 wheat available in the Farm, one new Farmer will be spawned (the game engine handles the actual spawning and wheat consumption).
    - The number of Farmers allocated to "spawn farmer" is computed as:
      spawn_farm_count = 2 * min(floor((total_farmers - 1) / 2), floor(environment.farm.wheat / 10))
    - The rest of Farmers stay in the "farm" group, continuing to farm wheat.
  - We do not actively spawn Warriors in the village step to keep the strategy simple; any spawned Warriors will naturally be sent to the Cave in the next step.

- Cave assignment policy:
  - Move every Warrior to the "attack" group (they attack the Dragon).
  - Move every Farmer to the "village" group (they return to the Village to farm/spawn).

- This strategy aims for a steady growth of the villager population via spawn mechanics while ensuring all Warriors contribute to dragon damage as soon as they are in the Cave.

Implementation notes:
- The environment.assign_group(component, group_id) method is used to assign components to groups.
- In assign_in_village, we compute spawning potential using environment.farm.wheat and reserve one Farmer for farming.
- In assign_in_cave, we assign Warriors to "attack" and Farmers to "village".

"""

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # All Warriors should go to the Cave (while in village)
        for w in warriors:
            environment.assign_group(w, "cave")

        total_farmers = len(farmers)

        # Reserve at least one Farmer for farming in village
        remaining_for_spawns = max(0, total_farmers - 1)

        # How many spawns can we support with available wheat?
        possible_spawns = min(remaining_for_spawns // 2, environment.farm.wheat // 10)

        spawn_farm_count = 2 * possible_spawns

        if spawn_farm_count > 0:
            to_spawn = farmers[:spawn_farm_count]
            to_farm = farmers[spawn_farm_count:]
            for f in to_spawn:
                environment.assign_group(f, "spawn farmer")
            for f in to_farm:
                environment.assign_group(f, "farm")
        else:
            # All farmers stay in farming
            for f in farmers:
                environment.assign_group(f, "farm")

        # Note: Any new Farmers spawned by the engine will appear in subsequent steps.
        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack; Farmers return to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")