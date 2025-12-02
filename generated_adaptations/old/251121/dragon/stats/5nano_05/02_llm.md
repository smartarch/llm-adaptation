```python
# Reasoning and adaptation strategy:
# - Globally: Warriors should be the primary offensive force. All Warriors will be directed
#   to the Cave and then tasked to Attack the Dragon. Farmers are valuable for wheat
#   production and for spawning new villagers; thus, Farmers should stay in the Village
#   and either farm or participate in controlled spawns to expand the force when wheat allows.
#
# - Village strategy (assign_in_village):
#   - Move all Warriors to the Cave (group "cave") so they head toward the Dragon.
#   - For Farmers, split them into:
#       * "spawn farmer" group: for every two farmers assigned here and 10 wheat, a new Farmer is spawned.
#       * "spawn warrior" group: for every two farmers assigned here and 12 wheat, a new Warrior is spawned.
#       * "farm" group: the remaining farmers stay in the Village to farm wheat.
#   - To keep it deterministic and safe, compute possible spawns given current wheat:
#       max_spawns_farmers = min(len(farmers) // 2, environment.farm.wheat // 10)
#       assign the first 2*max_spawns_farmers farmers to "spawn farmer".
#       Reduce available wheat by 10*max_spawns_farmers for the purpose of calculating warrior spawns.
#       max_spawns_warriors = min((len(farmers) - 2*max_spawns_farmers) // 2, 
#                                 (environment.farm.wheat - 10*max_spawns_farmers) // 12)
#       assign the next 2*max_spawns_warriors farmers to "spawn warrior".
#       The remainder of farmers go to "farm".
#   - Note: Wheat consumption is modelled locally to decide spawn group sizes; the game system
#     will actually apply spawns if enough wheat exists.
#
# - Cave strategy (assign_in_cave):
#   - All Warriors should Attack the Dragon (group "attack").
#   - All Farmers should vacate to the Village (group "village").
#   - This ensures Farmers remain in Village to farm/ spawn while Warriors focus on killing the Dragon.
#
# - Implementation details:
#   - Use environment.assign_group(component, group_id) to place each villager into the correct group.
#   - Use the component's read-only attributes (role, hp) to decide distribution; do not mutate them.
#   - Ensure we only assign to valid group_ids provided by the function's argument.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Gather farmers and warriors present in the Village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # First, move all warriors to cave (attack later in assign_in_cave, but here we set their next destination)
        for c in warriors:
            environment.assign_group(c, "cave")

        # Now allocate farmers into spawn groups and farming
        # If there are no farmers, nothing else to do
        if not farmers:
            return

        # Calculate max possible spawns given current wheat
        #  - Spawn farmer requires 2 villagers in the group and 10 wheat
        #  - Spawn warrior requires 2 villagers in the group and 12 wheat
        total_wheat = getattr(environment.farm, "wheat", 0)

        max_spawns_farmers = min(len(farmers) // 2, total_wheat // 10) if total_wheat >= 10 else 0

        # Assign first 2*max_spawns_farmers farmers to "spawn farmer"
        spawn_farmer_count = 2 * max_spawns_farmers
        spawn_farmer_villagers = farmers[:spawn_farmer_count]

        # Remaining wheat after allocating spawn farmers
        wheat_after_farm_spawns = total_wheat - 10 * max_spawns_farmers

        remaining_farmers = farmers[spawn_farmer_count:]

        max_spawns_warriors = 0
        if remaining_farmers and wheat_after_farm_spawns >= 12:
            max_spawns_warriors = min(len(remaining_farmers) // 2, wheat_after_farm_spawns // 12)

        spawn_warrior_count = 2 * max_spawns_warriors
        spawn_warrior_villagers = remaining_farmers[:spawn_warrior_count]

        # Rest go to farming
        farming_villagers = remaining_farmers[spawn_warrior_count:]

        # Apply group assignments
        for c in spawn_farmer_villagers:
            environment.assign_group(c, "spawn farmer")

        for c in spawn_warrior_villagers:
            environment.assign_group(c, "spawn warrior")

        for c in farming_villagers:
            environment.assign_group(c, "farm")

        # If there were any farmers not covered (edge case), ensure they go to farm
        # (Already covered by farming_villagers)

        # Note: Warriors already moved to "cave" above; Farmers moved as per above.

        # If there are any non-Farmer non-Warrior components (edge case), default to farm
        # but since components are either Farmer or Warrior, nothing else to handle.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: move Warriors to Attack the Dragon; Farmers go back to Village
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers or any other role should go to Village
                environment.assign_group(c, "village")
```