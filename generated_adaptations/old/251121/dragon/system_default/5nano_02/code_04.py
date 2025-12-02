"""
Reasoning and strategy:

- Global goals:
  - All Warriors should go to the Cave and attack the Dragon.
  - All Farmers stay in the Village and farm or participate in villager-spawns to grow the population (both Farmers and Warriors are useful later).

- Village assignment policy:
  - Move every Warrior to the "cave" group in the village step. They will later be placed in the "attack" group in the cave step.
  - For Farmers, use a simple spawn-based growth mechanism:
    - Reserve at least one Farmer to stay in the Village for farming (to keep wheat production ongoing) when possible.
    - Use the remaining Farmers to form the "spawn farmer" group in pairs. For every two Farmers assigned to this group and 10 wheat available in the Farm, one new Farmer will be spawned (the game engine handles the actual spawning and wheat consumption).
    - Additionally, optionally form a "spawn warrior" group: for every two Farmers assigned to this group and 12 wheat, one new Warrior will be spawned. This helps grow Warrior numbers without moving them to the Cave yet.
    - The rest of Farmers stay in the Village and are assigned to "farm" to continue producing wheat.
  - This strategy keeps a resilient farming base while growing the population and ensuring Warriors can eventually contribute to dragon damage.

- Cave assignment policy:
  - Move every Warrior to the "attack" group; move every Farmer to the "village" group (return to Village).

- Implementation notes:
  - In assign_in_village:
    - Warriors → "cave".
    - Farmers are allocated into three subgroups: "spawn farmer", "spawn warrior", and "farm".
    - If at least one Farmer exists, index 0 is reserved for farming; the rest can be allocated to spawning groups based on available wheat and remaining farmers.
  - In assign_in_cave:
    - Warriors → "attack".
    - Farmers → "village".

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

        if total_farmers == 0:
            # No farmers to allocate; nothing else to do in village
            return

        # Reserve at least one Farmer for farming in village if possible
        reserve_for_farm = 1 if total_farmers > 0 else 0

        # Remaining farmers available for spawning
        rem = total_farmers - reserve_for_farm

        # Wheat available for spawning
        wheat = getattr(environment.farm, "wheat", 0)

        # Determine how many spawn farmers we can create: each requires 2 villagers and 10 wheat
        spawn_farm_pairs = min(rem // 2, wheat // 10)
        spawn_farm_count = spawn_farm_pairs * 2

        # Update remaining for potential spawn warriors
        rem_after_farm = rem - spawn_farm_count

        # Determine how many spawn warriors we can create: each requires 2 villagers and 12 wheat
        spawn_war_pairs = min(rem_after_farm // 2, wheat // 12)
        spawn_war_count = spawn_war_pairs * 2

        start_spawn = 1  # index 0 is reserved for farming if there is at least one farmer
        # Indices for spawn groups
        farm_indices = set(range(start_spawn, start_spawn + spawn_farm_count))
        war_indices = set(range(start_spawn + spawn_farm_count, start_spawn + spawn_farm_count + spawn_war_count))

        # Assign farmers to the appropriate groups
        # We assume the list order is stable; we assign by index
        for idx, f in enumerate(farmers):
            if idx == 0:
                environment.assign_group(f, "farm")
            elif idx in farm_indices:
                environment.assign_group(f, "spawn farmer")
            elif idx in war_indices:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

        # Note: If there are more farmers beyond those considered, they default to "farm"
        return

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # Warriors attack; Farmers return to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")