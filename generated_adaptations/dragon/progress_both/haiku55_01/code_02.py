from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Farmers stay in the Village (farm, eat, and fund spawns).
    Warriors rotate between Village (eat) and Cave (attack) based on
    steps_since_meal so that nobody starves.
    """

    FARMER_EAT_THRESHOLD = 3
    WARRIOR_EAT_THRESHOLD = 2
    CAVE_RETURN_THRESHOLD = 3
    SPAWN_WINDOW = 20  # only spawn early, keep wheat for meals later

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # Process the longest-unfed villagers first.
        ordered = sorted(components, key=lambda c: c.steps_since_meal, reverse=True)

        eaters = []
        warriors_ready = []
        free_farmers = []
        remaining = []

        # 1) Decide who eats (eating has priority, limited by available wheat).
        for c in ordered:
            s = c.steps_since_meal
            threshold = self.WARRIOR_EAT_THRESHOLD if c.role == "Warrior" else self.FARMER_EAT_THRESHOLD
            if s >= threshold and wheat > 0:
                eaters.append(c)
                wheat -= 1
            else:
                remaining.append(c)

        # 2) Split the rest into warriors (dispatch to cave) and farmers (spawn/farm).
        for c in remaining:
            if c.role == "Warrior":
                warriors_ready.append(c)
            else:
                free_farmers.append(c)

        # Reserve wheat for one meal per villager in the next step(s).
        reserve = len(components)

        spawn_warrior_groups = []
        spawn_farmer_groups = []
        spawn_members = set()

        # 3) Spawning (early game only). Farmers act as spawners in pairs.
        if step <= self.SPAWN_WINDOW:
            while len(free_farmers) - len(spawn_members) >= 2:
                available = [f for f in free_farmers if id(f) not in spawn_members]
                pair = available[:2]
                if wheat - reserve >= 12:
                    spawn_warrior_groups.append(pair)
                    wheat -= 12
                elif wheat - reserve >= 10:
                    spawn_farmer_groups.append(pair)
                    wheat -= 10
                else:
                    break
                for f in pair:
                    spawn_members.add(id(f))

        spawn_ids = set()
        for grp in spawn_warrior_groups + spawn_farmer_groups:
            for f in grp:
                spawn_ids.add(id(f))

        # Assign groups
        for c in eaters:
            environment.assign_group(c, "eat")

        for grp in spawn_warrior_groups:
            for f in grp:
                environment.assign_group(f, "spawn warrior")

        for grp in spawn_farmer_groups:
            for f in grp:
                environment.assign_group(f, "spawn farmer")

        for c in warriors_ready:
            if dragon_hp > 0 and c.steps_since_meal < self.WARRIOR_EAT_THRESHOLD:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

        for f in free_farmers:
            if id(f) in spawn_ids:
                continue
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                # Farmers do not belong in the cave: send them home.
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.CAVE_RETURN_THRESHOLD:
                # Warrior is getting hungry: go eat before it starves.
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")