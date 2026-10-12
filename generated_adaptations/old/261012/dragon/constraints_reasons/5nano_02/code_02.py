from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village to groups:
        - All Warriors -> cave (to move to cave)
        - Farmers -> farm by default
        - Optional spawns:
          * If at least 2 farmers and wheat >= 10, assign 2 farmers to "spawn farmer"
          * If after that at least 2 other farmers and wheat >= 12, assign 2 to "spawn warrior"
        """
        # Separate farmers and warriors in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default: all farmers stay in village and farm
        for f in farmers:
            environment.assign_group(f, "farm")

        # Move all Warriors to cave (they will be re-assigned to attack in assign_in_cave)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Spawn logic (spawn groups operate in village phase)
        assigned = set()

        # Try to spawn farmers: pick first two farmers if wheat allows
        if len(farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 10:
            for f in farmers[:2]:
                environment.assign_group(f, "spawn farmer")
                assigned.add(f)

        # Try to spawn warriors: use next two farmers if wheat allows
        remaining_farmers = [f for f in farmers if f not in assigned]
        if len(remaining_farmers) >= 2 and getattr(environment.farm, "wheat", 0) >= 12:
            for f in remaining_farmers[:2]:
                environment.assign_group(f, "spawn warrior")
                assigned.add(f)

        # Any remaining farmers (not assigned to spawn groups) stay in farm
        for f in farmers:
            if f in assigned:
                continue
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave to groups:
        - Warriors -> attack (attack the Dragon)
        - Farmers -> village (return to Village)
        """
        for comp in components:
            role = getattr(comp, "role", None)
            if role == "Warrior":
                environment.assign_group(comp, "attack")
            elif role == "Farmer":
                environment.assign_group(comp, "village")
            else:
                # Fallback: keep sensible default
                environment.assign_group(comp, "village")