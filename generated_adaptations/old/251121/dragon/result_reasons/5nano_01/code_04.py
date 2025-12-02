from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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

        # Wheat available in the Farm
        wheat = 0
        farm_env = getattr(environment, "farm", None)
        if farm_env is not None:
            wheat = getattr(farm_env, "wheat", 0)

        # Determine spawns: maximize spawns given resources and farmer availability
        # Spawn farmers: each event uses 2 farmers and 10 wheat
        max_spawn_farmers = min(len(available_farmers) // 2, wheat // 10)
        if max_spawn_farmers > 0:
            take = 2 * max_spawn_farmers
            to_spawn_farmer = available_farmers[:take]
            available_farmers = available_farmers[take:]
            wheat -= max_spawn_farmers * 10  # consume wheat for spawned farmers
        else:
            to_spawn_farmer = []

        # Spawn warriors: with remaining farmers and wheat, each event uses 2 farmers and 12 wheat
        max_spawn_warriors = min(len(available_farmers) // 2, wheat // 12)
        if max_spawn_warriors > 0:
            take = 2 * max_spawn_warriors
            to_spawn_warrior = available_farmers[:take]
            available_farmers = available_farmers[take:]
            wheat -= max_spawn_warriors * 12  # consume wheat for spawned warriors
        else:
            to_spawn_warrior = []

        # Remaining farmers go to farming in the Village
        to_farm = available_farmers

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
        - cave: Stay in the Cave
        - village: Go to the Village
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers go back to the Village
                environment.assign_group(c, "village")