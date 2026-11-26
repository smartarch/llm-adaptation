from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.warriors_spawned = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        ids = {g: i for i, g in enumerate(group_ids)} if isinstance(group_ids[0], int) else None
        # helper: group id may be name or index; use names directly
        def gid(name):
            return name

        wheat = environment.farm.wheat
        total_warriors = sum(1 for w in environment.warriors if w.hp > 0)
        hungry = [c for c in components if c.steps_since_meal >= 4]
        rest = [c for c in components if c.steps_since_meal < 4]

        # 1) feed the hungry
        for c in hungry:
            environment.assign_group(c, gid("eat"))

        # 2) decide for the rest
        # reserve wheat for upcoming meals (everyone must eat within 6 steps)
        all_vills = list(environment.farmers) + list(environment.warriors)
        upcoming_meals = sum(1 for v in all_vills if v.steps_since_meal >= 1)
        reserve = upcoming_meals + 10  # buffer

        available = wheat - reserve

        if wheat < 20:
            # everyone farms to build up food supply
            for c in rest:
                environment.assign_group(c, gid("farm"))
            return

        # spawn warriors while we have few of them and wheat allows
        if total_warriors < 6 and available >= 12 and len(rest) >= 2:
            pair = rest[:2]
            for c in pair:
                environment.assign_group(c, gid("spawn warrior"))
            rest = rest[2:]
            available -= 12
            self.warriors_spawned += 1

        # send all warriors to the cave
        for c in rest:
            if c.role == "Warrior":
                environment.assign_group(c, gid("cave"))
                rest_left = True
        # farmers: farm unless we have plenty of wheat
        for c in rest:
            if c.role == "Warrior":
                continue
            if wheat >= 40 and total_warriors >= 2:
                environment.assign_group(c, gid("cave"))
            else:
                environment.assign_group(c, gid("farm"))

    def assign_in_cave(self, components, environment, group_ids, step: int):
        def gid(name):
            return name

        for c in components:
            # starving soon -> go home to eat (travel takes 1 step, eat next)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, gid("village"))
            else:
                environment.assign_group(c, gid("attack"))