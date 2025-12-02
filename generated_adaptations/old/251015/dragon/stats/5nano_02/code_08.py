# Reasoning embedded as comments:
# Objective: improve win rate by a more predictable, resource-aware spawning cadence
# and by guaranteeing Warriors stay in the Cave to maximize DPS. The previous approaches
# either spawned too aggressively (draining wheat, overcrowding spawn groups) or did not
# balance farming vs spawning with the dragon pressure.
# Strategy implemented here:
# - Enforce: all Warriors in Village go to the Cave and Attack the Dragon (as required).
# - In the Village, use a cadence-based spawning plan:
#   - Spawn farmers in small, controlled batches when there are enough wheat and enough
#     farmers available to participate in the spawn (requires 2 farmers per batch and 10 wheat).
#   - Spawn warriors in small batches only when there are enough farmers left (at least 4)
#     and enough wheat (12). This creates a gradual DPS boost without starving the village.
#   - The rest of the farmers stay in farming to accumulate wheat for future spawns.
# - In the Cave: Warriors Attack; Farmers go back to Village.
# This cadence aims to steadily grow both population and wheat, while ensuring constant Dragon DPS
# from Warriors in the Cave, reducing the chance of dragon overwhelming the village.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # 1) Ensure all Warriors in Village head to the Cave to attack
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "cave")

        # 2) Collect Farmers currently in the Village
        farmers = [c for c in components if c.role == "Farmer"]

        # 3) Read current wheat in farm
        wheat = int(getattr(environment.farm, "wheat", 0))

        # 4) Cadence-based, conservative spawning policy
        # - Spawn 2 Farmers every 4 steps if possible (requires 2 farmers in spawn group and 10 wheat)
        # - Spawn 2 Warriors every 7 steps if possible (requires 4+ farmers and 12 wheat)
        spawn_farmers_to_assign = 0
        spawn_warriors_to_assign = 0

        # Check if a farm spawn can occur now
        if step % 4 == 0 and len(farmers) >= 2 and wheat >= 10:
            spawn_farmers_to_assign = 2  # signal 2 farmers to the "spawn farmer" group

        # Check if a warrior spawn can occur now, given remaining farmers and wheat
        remaining_farmers_after_farm_spawn = len(farmers) - spawn_farmers_to_assign
        if step % 7 == 0 and remaining_farmers_after_farm_spawn >= 4 and wheat >= 12:
            spawn_warriors_to_assign = 2  # signal 2 farmers to the "spawn warrior" group

        # 5) Assign groups among Farmers according to cadence
        for idx, f in enumerate(farmers):
            if idx < spawn_farmers_to_assign:
                environment.assign_group(f, "spawn farmer")
            elif idx < spawn_farmers_to_assign + spawn_warriors_to_assign:
                environment.assign_group(f, "spawn warrior")
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: keep Warriors in "attack"; Farmers go back to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")