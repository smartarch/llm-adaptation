from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers currently in the Village into:
        - farm: stay in Village and farm
        - cave: go to Cave
        - spawn farmer: for every 2 villagers in this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: for every 2 villagers in this group and 12 wheat, a new Warrior is spawned
        """
        # Gather villagers by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # 1) All Warriors go to the Cave
        for w in warriors:
            environment.assign_group(w, "cave")

        # 2) Farmers stay in Village by default (farmable)
        # We'll decide how many to allocate to spawn groups based on available wheat.
        wheat = getattr(getattr(environment, "farm", None), "wheat", 0)

        # 3) Spawn planning (limited and deterministic)
        # Calculate how many farmers can be sent to spawn farmer (max 2)
        spawn_farmer_count = 0
        if wheat >= 10:
            spawn_farmer_count = min(2, len(farmers))

        # Assign first batch to "spawn farmer"
        for i, f in enumerate(farmers):
            if i < spawn_farmer_count:
                environment.assign_group(f, "spawn farmer")

        # Remaining farmers not assigned to spawn farmer
        remaining_for_warrior = farmers[spawn_farmer_count:]

        # Calculate if we can spawn warriors: need at least 2 villagers in group and at least 12 wheat
        spawn_warrior_count = 0
        if wheat >= 12 and len(remaining_for_warrior) >= 2:
            # Spawn up to 2 Warriors (requires 2 villagers in the group)
            spawn_warrior_count = 2

        # Assign to "spawn warrior" if possible
        for idx in range(spawn_warrior_count):
            environment.assign_group(remaining_for_warrior[idx], "spawn warrior")

        # Remaining farmers go to "farm"
        for f in remaining_for_warrior[spawn_warrior_count:]:
            environment.assign_group(f, "farm")

        # Note: Any farmers not explicitly assigned here are covered by the above logic.
        # If a farmer list is empty, nothing to do for farmers.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        In the Cave, split villagers as:
        - attack: Warriors
        - cave: Stay in Cave (not used by our strategy, but keep for completeness)
        - village: Farmers go back to Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers return to the Village
                environment.assign_group(c, "village")