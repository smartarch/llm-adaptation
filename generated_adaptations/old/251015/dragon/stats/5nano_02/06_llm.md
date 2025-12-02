```py
# Reasoning and strategy (embedded as comments for traceability):
# - The previous approach allowed explosive spawning of farmers (via "spawn farmer")
#   and did not balance spawning with the need for Warriors in the Cave to DPS the Dragon.
# - To improve, we adopt a conservative, cadence-based spawning policy:
#   - All Warriors must be sent to the Cave to attack (as required).
#   - In the Village, prefer farming for wheat and spawn at most one batch per a small cadence.
#   - Spawn farmer: require at least 2 farmers in the village and at least 10 wheat; perform this
#     only on a cadence (e.g., every 6 steps) and spawn exactly 2 villagers to keep growth controlled.
#   - Spawn warrior: require at least 4 farmers and at least 12 wheat; perform this on a slower cadence
#     (e.g., every 9 steps) and spawn exactly 2 villagers to boost DPS gradually.
#   - This cadence helps accumulate enough wheat for spawning while preventing unbounded population growth
#     and reduces the risk of letting the Dragon overwhelm the village.
# - Cave handling stays simple: Warriors go to attack; Farmers return to Village.

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy:
        # - Move all Warriors to the Cave to attack (enforcing the constraint).
        # - In the Village, spawn farmers and possibly warriors in a controlled cadence.
        # - Remaining farmers continue farming to produce wheat for future spawns.

        # 1) Move all Warriors in the Village to the Cave (attack-ready)
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "cave")

        # 2) Gather Farmers currently in the Village
        farmers = [c for c in components if c.role == "Farmer"]

        # 3) Read current wheat
        wheat = getattr(environment.farm, "wheat", 0)

        # 4) Cadence-based spawning decisions (conservative)
        spawn_farmers_to_assign = 0
        spawn_warriors_to_assign = 0

        # Spawn 1 batch of 2 farmers every 6 steps if possible
        if (step % 6 == 0) and len(farmers) >= 2 and wheat >= 10:
            spawn_farmers_to_assign = 2

        # Spawn 1 batch of 2 warriors every 9 steps if possible
        if (step % 9 == 0) and len(farmers) >= 4 and wheat >= 12:
            spawn_warriors_to_assign = 2

        # 5) Assign groups among Farmers
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
```