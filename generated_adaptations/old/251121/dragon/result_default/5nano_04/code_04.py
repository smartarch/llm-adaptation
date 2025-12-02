from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Village into:
        - farm: stay in village and farm
        - cave: go to cave
        - spawn farmer: for every two villagers assigned to this group and 10 wheat, a new Farmer is spawned
        - spawn warrior: for every two villagers assigned to this group and 12 wheat, a new Warrior is spawned

        Strategy (improved):
        - All Warriors go to cave.
        - For Farmers, spawn only a limited number per turn (cap), to avoid starving wheat production.
          Prefer spawning farmers when wheat allows; then consider spawning warriors from remaining farmers if possible.
        - The rest of farmers farm.
        """
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        total_farmers = len(farmers)

        # Move all warriors to the cave
        for w in warriors:
            environment.assign_group(w, "cave")

        if total_farmers == 0:
            return

        wheat = getattr(environment.farm, "wheat", 0)

        # Cap on spawned pairs per turn to keep wheat production healthy
        max_pairs_per_turn = 3  # up to 6 new villagers per turn

        spawn_farm_pairs = 0
        if wheat >= 10 and total_farmers >= 2:
            spawn_farm_pairs = min(total_farmers // 2, wheat // 10, max_pairs_per_turn)
        spawn_farm_count = 2 * spawn_farm_pairs

        remaining_farmers = total_farmers - spawn_farm_count
        wheat_after_farm = wheat - (spawn_farm_pairs * 10)

        spawn_war_pairs = 0
        if wheat_after_farm >= 12 and remaining_farmers >= 2:
            spawn_war_pairs = min(remaining_farmers // 2, wheat_after_farm // 12, max_pairs_per_turn)
        spawn_war_count = 2 * spawn_war_pairs

        farm_count = remaining_farmers - spawn_war_count

        idx = 0
        # Assign to spawn farmer
        for _ in range(spawn_farm_count):
            environment.assign_group(farmers[idx], "spawn farmer")
            idx += 1
        # Assign to spawn warrior
        for _ in range(spawn_war_count):
            environment.assign_group(farmers[idx], "spawn warrior")
            idx += 1
        # Assign remaining to farm
        for _ in range(farm_count):
            environment.assign_group(farmers[idx], "farm")
            idx += 1

        # If any farmers left (due to rounding or edge cases), send them to farm
        while idx < total_farmers:
            environment.assign_group(farmers[idx], "farm")
            idx += 1

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            elif role == "Farmer":
                environment.assign_group(c, "village")