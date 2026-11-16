from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    """
    Economy first (farmers spawn farmers early), then a growing warrior army
    that rotates between the Cave (attacking) and the Village (eating), so the
    Dragon is attacked almost every step and never gets free regeneration.
    """

    FARMER_EAT_AT = 3       # farmers eat when they have gone this many steps unfed
    WARRIOR_EAT_AT = 2      # warriors eat early so they can afford a Cave trip
    CAVE_RETURN_AT = 3      # warriors in the Cave go home at this hunger level
    CAVE_RETURN_HP = 1      # ... or when nearly dead
    FARMER_TARGET = 4       # build up to this many farmers early
    FARMER_SPAWN_UNTIL = 8  # economy spawns only until this step
    WARRIOR_SPAWN_UNTIL = 24

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat

        # 1) Decide who eats: warriors first, then the most hungry villagers.
        def eat_threshold(c):
            return self.WARRIOR_EAT_AT if c.role == "Warrior" else self.FARMER_EAT_AT

        hungry = [c for c in components if c.steps_since_meal >= eat_threshold(c)]
        hungry.sort(key=lambda c: (c.role != "Warrior", -c.steps_since_meal))

        eating = []
        for c in hungry:
            if wheat >= 1:
                eating.append(c)
                wheat -= 1
        eating_ids = {id(c) for c in eating}

        for c in eating:
            environment.assign_group(c, "eat")

        # 2) Everyone else who is not eating.
        rest = [c for c in components if id(c) not in eating_ids]
        farmers_free = [c for c in rest if c.role == "Farmer"]
        warriors_free = [c for c in rest if c.role == "Warrior"]

        # Keep a small wheat reserve for the next round of meals.
        reserve = max(2, len(components) // 2)
        total_farmers = sum(1 for c in components if c.role == "Farmer")

        spawned_ids = set()

        # 3) Spawn using pairs of free farmers.
        while len(farmers_free) - len(spawned_ids) >= 2:
            pair = [f for f in farmers_free if id(f) not in spawned_ids][:2]

            if step <= self.FARMER_SPAWN_UNTIL and total_farmers < self.FARMER_TARGET \
                    and wheat - reserve >= 10:
                group = "spawn farmer"
                wheat -= 10
                total_farmers += 1
            elif step <= self.WARRIOR_SPAWN_UNTIL and wheat - reserve >= 12:
                group = "spawn warrior"
                wheat -= 12
            else:
                break

            for f in pair:
                environment.assign_group(f, group)
                spawned_ids.add(id(f))

        # 4) Remaining farmers farm.
        for f in farmers_free:
            if id(f) not in spawned_ids:
                environment.assign_group(f, "farm")

        # 5) Warriors that are not eating go to the Cave to attack.
        for w in warriors_free:
            environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.role == "Farmer":
                # Farmers do not belong in the Cave.
                environment.assign_group(c, "village")
            elif c.steps_since_meal >= self.CAVE_RETURN_AT or c.hp <= self.CAVE_RETURN_HP:
                # Hungry or nearly dead warriors go home to eat / recover.
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")