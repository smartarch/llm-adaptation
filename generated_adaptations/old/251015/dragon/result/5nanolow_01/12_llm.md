```py
import abc

# Assuming the base class can be imported from the given module path
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Strategy enhancements:
        - Always keep Warriors in the Cave to attack (attack group).
        - Use spawning to grow population and DPS:
          - Spawn Farmers: for every two Farmers assigned to "spawn farmer" and 10 wheat, one new Farmer is spawned.
          - Spawn Warriors: for every two Farmers (or other villagers) assigned to "spawn warrior" and 12 wheat, one new Warrior is spawned.
        - We select villagers for spawning in a data-driven way:
          - Compute how many Farmer-pairs we can use for farmer spawns: spawn_f_count = min(num_farmers//2, wheat//10)
          - After allocating farmer spawns, compute wheat remaining and how many Warrior-spawns we can perform: spawn_w_count = min((num_farmers - 2*spawn_f_count)//2, (wheat - 10*spawn_f_count)//12)
          - Allocate first 2*spawn_f_count to "spawn farmer" and next 2*spawn_w_count to "spawn warrior".
          - Remaining Farmers go to "farm".
        - If no wheat is available or not enough villagers for spawning, fall back to farming.
        - All Warriors are moved to the cave (attack) as required.
        - This approach aims to boost near-term DPS via faster population growth while respecting the constraints.
        """
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) Always send Warriors to cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Spawning decisions in Village
        wheat = getattr(environment.farm, "wheat", 0)
        num_farmers = len(farmers)

        # Potential farmer spawns (needs 2 farmers + 10 wheat)
        spawn_f_count = min(num_farmers // 2, wheat // 10)

        # Remaining wheat after farmer spawns
        wheat_after_farm = wheat - 10 * spawn_f_count

        # Potential warrior spawns (needs 2 villagers + 12 wheat)
        # Use remaining villagers after farmer-spawns
        remaining_for_warriors = max(0, num_farmers - 2 * spawn_f_count)
        spawn_w_count = 0
        if wheat_after_farm >= 12:
            spawn_w_count = min(remaining_for_warriors // 2, wheat_after_farm // 12)

        # Assign spawning groups
        # First 2*spawn_f_count farmers to spawn farmer
        spawn_farmer_candidates = farmers[: 2 * spawn_f_count]
        # Next 2*spawn_w_count villagers to spawn warrior (if any)
        spawn_warrior_candidates = farmers[2 * spawn_f_count: 2 * spawn_f_count + 2 * spawn_w_count]

        for f in spawn_farmer_candidates:
            environment.assign_group(f, "spawn farmer")
        for f in spawn_warrior_candidates:
            environment.assign_group(f, "spawn warrior")

        # Remaining farmers go to farming
        remaining_farmers = farmers[2 * spawn_f_count + 2 * spawn_w_count :]
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave, keep Warriors in "attack" and move Farmers back to the Village.
        Any other components default to cave to be safe.
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "cave")
```