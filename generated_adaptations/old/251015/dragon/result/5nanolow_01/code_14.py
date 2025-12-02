import abc

# Assuming the base class can be imported from the given module path
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Enhanced strategy:
        - Always keep Warriors in the Cave to attack (attack group).
        - Farmers stay in the Village.
        - Early burst spawning: if step < 3 and there is enough wheat, spawn up to 2 farmers
          by placing 2*spawn_farmers into "spawn farmer" group (each spawn uses 2 farmers and 10 wheat).
          Remaining farmers go to "farm".
        - If step >= 3 or not enough wheat, spawn nowhere and put all farmers in "farm".
        """

        # Separate farmers and warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Always send Warriors to cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning decisions in Village (only early, and only if wheat allows)
        wheat = getattr(environment.farm, "wheat", 0)
        num_farmers = len(farmers)

        spawn_f_count = 0
        if step < 3:
            # Potential farmer spawns (needs 2 farmers + 10 wheat each)
            spawn_f_count = min(num_farmers // 2, wheat // 10)

        # Use spawning if allowed
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