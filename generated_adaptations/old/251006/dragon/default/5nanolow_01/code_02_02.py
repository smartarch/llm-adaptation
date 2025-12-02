import abc

from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Strategy improvements:
        # - Assign every villager exactly once in this phase.
        # - Keep all Farmers in Village and use Wheat to spawn as many Farmers as possible
        #   (spawn farmer) first, since they continuously provide Wheat via farming.
        # - Use remaining Wheat to spawn Warriors (spawn warrior) if possible.
        # - Remaining villagers (by role) go to their default roles:
        #     Farmers -> farm
        #     Warriors -> cave (to prepare for attack)
        # - This preserves a clear, deterministic single assignment per component.

        # Split by role for deterministic processing
        farmers = []
        warriors = []
        for c in components:
            if getattr(c, "role", None) == "Farmer":
                farmers.append(c)
            elif getattr(c, "role", None) == "Warrior":
                warriors.append(c)

        # Read available wheat from the Farm
        wheat = 0
        try:
            wheat = int(getattr(environment.farm, "wheat", 0))
        except Exception:
            wheat = 0

        # Determine how many spawn pairs we can support
        # Farmer spawns: need 10 wheat per pair of 2 farmers
        max_pairs_farmers = 0
        if wheat >= 10:
            max_pairs_farmers = min(len(farmers) // 2, wheat // 10)
        spawn_farmers = 2 * max_pairs_farmers

        # Remaining wheat after farmer spawns
        wheat_after_farm_spawns = wheat - (spawn_farmers * 10)

        # Warrior spawns: need 12 wheat per pair of 2 warriors
        max_pairs_warriors = 0
        if wheat_after_farm_spawns >= 12:
            max_pairs_warriors = min(len(warriors) // 2, wheat_after_farm_spawns // 12)
        spawn_warriors = 2 * max_pairs_warriors

        # Build a single assignment map to guarantee exactly one assignment per component
        # Key -> group_id
        assignment = {}

        # Assign farmers: first spawn group, then farm
        for i, f in enumerate(farmers):
            if i < spawn_farmers:
                assignment[f] = "spawn farmer"
            else:
                assignment[f] = "farm"

        # Assign warriors: first spawn group, then cave
        for i, w in enumerate(warriors):
            if i < spawn_warriors:
                assignment[w] = "spawn warrior"
            else:
                assignment[w] = "cave"

        # Validate that every component in this phase has an assignment.
        # If there are any villagers not covered (shouldn't happen), assign to a safe default.
        for c in components:
            if c not in assignment:
                # Default: Farmers -> farm, Warriors -> cave
                if getattr(c, "role", None) == "Farmer":
                    assignment[c] = "farm"
                elif getattr(c, "role", None) == "Warrior":
                    assignment[c] = "cave"
                else:
                    # In case of an unexpected type, put in a neutral safe place
                    assignment[c] = "farm"

        # Apply the assignments
        for c, grp in assignment.items():
            environment.assign_group(c, grp)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave phase, all Warriors should attack.
        # Other villagers can stay in cave or move to village; we choose to keep them in cave by default.
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "cave")