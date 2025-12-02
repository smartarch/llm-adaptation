from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the village into:
        - farm: Farmers who stay and farm
        - cave: All Warriors go to the Cave (travel)
        - spawn farmer: subset of Farmers used to spawn new Farmers
        - spawn warrior: subset of Farmers used to spawn new Warriors
        """
        # Separate farmers and warriors present in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Step 1: Send all warriors to the cave (to later attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Step 2: Compute spawn allocations from farmers based on available wheat
        total_farmers = len(farmers)
        available_wheat = getattr(environment.farm, "wheat", 0)

        spawns_farm = min(total_farmers // 2, available_wheat // 10)

        remaining_wheat_after_farms = available_wheat - spawns_farm * 10

        # Step 3: Compute possible warrior spawns from the remaining farmers
        spawns_warrior = min((total_farmers - 2 * spawns_farm) // 2,
                             remaining_wheat_after_farms // 12)

        # Step 4: Assign farmers to the appropriate spawn/farm groups
        # We will allocate in order: first 2*spawns_farm to "spawn farmer",
        # next 2*spawns_warrior to "spawn warrior", the rest to "farm".
        spawn_farmer_count = 2 * spawns_farm
        spawn_warrior_count = 2 * spawns_warrior

        # Ensure we don't overshoot if counts are misaligned
        spawn_farmer_set = farmers[:spawn_farmer_count]
        remaining_for_warriors = farmers[spawn_farmer_count:]
        spawn_warrior_set = remaining_for_warriors[:spawn_warrior_count]
        farm_set = remaining_for_warriors[spawn_warrior_count:]

        for c in spawn_farmer_set:
            environment.assign_group(c, "spawn farmer")
        for c in spawn_warrior_set:
            environment.assign_group(c, "spawn warrior")
        for c in farm_set:
            environment.assign_group(c, "farm")

        # Note: If there are any farmers not in the above groups (edge cases),
        # they will have been assigned to the last farm_set. Warriors already moved.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the cave into:
        - attack: Warriors attack the Dragon
        - cave: Stay in the Cave (if any)
        - village: Go back to Village (Farmers return to farming)
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers return to village to farm or spawn new villagers
                environment.assign_group(c, "village")