import abc

# Assuming the base class can be imported from the given module path
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Aggressive, bounded, data-driven spawning strategy:
        - Warriors -> cave (attack)
        - Farmers -> village (farm/spawn)
        - Spawn as many Farmers as possible this turn:
            spawn_f_count = min(num_farmers // 2, wheat // 10)
            Assign 2 * spawn_f_count farmers to "spawn farmer"
            Remaining farmers to "farm"
        - No Warrior-spawns in village; Warriors are already in cave.
        """
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Always send Warriors to Cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning decisions in Village (Farmers only)
        wheat = getattr(environment.farm, "wheat", 0)
        num_farmers = len(farmers)

        # Potential farmer spawns (needs 2 farmers + 10 wheat each)
        spawn_f_count = min(num_farmers // 2, wheat // 10)

        # Wheat left after farmer spawns
        wheat_after_farm = wheat - 10 * spawn_f_count

        # Assign spawning groups
        spawn_farmer_candidates = farmers[: 2 * spawn_f_count]
        remaining_farmers = farmers[2 * spawn_f_count:]

        for f in spawn_farmer_candidates:
            environment.assign_group(f, "spawn farmer")

        # Remaining farmers go to farming
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave, keep Warriors in "attack" and move Farmers back to the Village.
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "cave")