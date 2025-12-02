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
        Strategy:
        - Move all Warriors to cave.
        - Attempt to spawn at most 1 Warrior if there are enough Farmers and wheat.
        - With remaining Farmers, spawn as many Farmers as possible given remaining wheat.
        - Any leftover Farmers go to farming.
        - This yields incremental growth in the army while avoiding destabilizing the cave with too many villagers at once.
        """
        # Separate farmers and warriors present in the village
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Step 1: Send all warriors to the cave (to later attack)
        for w in warriors:
            environment.assign_group(w, "cave")

        # Step 2: Determine spawn plan with a conservative, greedy policy
        total_farmers = len(farmers)
        available_wheat = getattr(environment.farm, "wheat", 0)

        spawns_warrior = 0
        # Try to spawn at most 1 Warrior if we have enough resources
        if total_farmers >= 2 and available_wheat >= 12:
            spawns_warrior = 1

        # Reserve farmers for potential Warrior spawn, and compute remaining wheat
        reserved_for_warrior = 2 * spawns_warrior
        remaining_farmers_after_warrior = total_farmers - reserved_for_warrior
        remaining_wheat_after_warrior = available_wheat - (12 * spawns_warrior)

        spawns_farm = 0
        if remaining_farmers_after_warrior >= 2 and remaining_wheat_after_warrior >= 10:
            spawns_farm = min(remaining_farmers_after_warrior // 2,
                              remaining_wheat_after_warrior // 10)

        # Step 3: Assign villagers to the appropriate spawn/farm groups
        # Order: first 2*spawns_warrior to "spawn warrior", then 2*spawns_farm to "spawn farmer",
        # rest to "farm"
        idx = 0
        if spawns_warrior > 0:
            to_spawn_warrior = farmers[:2 * spawns_warrior]
            for c in to_spawn_warrior:
                environment.assign_group(c, "spawn warrior")
            idx += 2 * spawns_warrior

        if spawns_farm > 0:
            to_spawn_farm = farmers[idx: idx + 2 * spawns_farm]
            for c in to_spawn_farm:
                environment.assign_group(c, "spawn farmer")
            idx += 2 * spawns_farm

        # Remaining farmers go to farming
        for c in farmers[idx:]:
            environment.assign_group(c, "farm")

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