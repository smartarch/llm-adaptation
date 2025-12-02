from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _best_spawn_distribution(self, num_farmers, wheat):
        """
        Brute-force search for the best (k1, k2) where:
          - k1: number of spawn farmer events
          - k2: number of spawn warrior events
          Constraints:
            2*(k1 + k2) <= num_farmers
            10*k1 + 12*k2 <= wheat
          Objective:
            maximize (k1 + k2); tie-break prefer larger k2 (more warrior spawns)
        Returns tuple (k1, k2)
        """
        best_k1, best_k2 = 0, 0
        best_total = 0
        max_possible = num_farmers // 2
        for k1 in range(0, max_possible + 1):
            for k2 in range(0, max_possible - k1 + 1):
                if 10 * k1 + 12 * k2 <= wheat:
                    total = k1 + k2
                    if total > best_total:
                        best_total = total
                        best_k1, best_k2 = k1, k2
                    elif total == best_total:
                        # tie-break: prefer more warrior spawns
                        if k2 > best_k2:
                            best_k1, best_k2 = k1, k2
        return best_k1, best_k2

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Village into:
        - farm: Farmers stay in the Village to farm
        - cave: Warriors go to the Cave
        - spawn farmer: For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned.
        - spawn warrior: For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned.
        """
        # Separate by role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default allocations
        to_farm = []
        to_cave = []
        to_spawn_farmer = []
        to_spawn_warrior = []

        # All Warriors should head to the Cave to attack
        to_cave.extend(warriors)

        # Farmers present in village
        available_farmers = list(farmers)
        num_farmers = len(available_farmers)

        # Wheat available in the Farm
        wheat = 0
        farm_env = getattr(environment, "farm", None)
        if farm_env is not None:
            wheat = getattr(farm_env, "wheat", 0)

        # Compute best spawn distribution this step
        k1, k2 = self._best_spawn_distribution(num_farmers, wheat)

        # Allocate farmers for spawns
        take_for_farm = 2 * k1
        take_for_warrior = 2 * k2

        to_spawn_farmer = available_farmers[:take_for_farm]
        to_spawn_warrior = available_farmers[take_for_farm: take_for_farm + take_for_warrior]

        # Remaining farmers go to farm
        to_farm = available_farmers[take_for_farm + take_for_warrior:]

        # Assign groups
        for c in to_farm:
            environment.assign_group(c, "farm")
        for c in to_spawn_farmer:
            environment.assign_group(c, "spawn farmer")
        for c in to_spawn_warrior:
            environment.assign_group(c, "spawn warrior")
        for c in to_cave:
            environment.assign_group(c, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Assign villagers in the Cave into:
        - attack: Attack the Dragon
        - cave: Stay in the Cave (not used in this strategy, but kept for completeness)
        - village: Go to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to the Village
                environment.assign_group(c, "village")