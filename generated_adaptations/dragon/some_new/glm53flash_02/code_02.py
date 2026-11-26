from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.wave_size = 2  # warriors per wave

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon = environment.dragon
        cave_warriors = sum(1 for w in environment.warriors if w.location == "Cave")
        # how many warriors we want attacking at once
        wanted = 4 if dragon.hp < 100 else 2

        ids = {g: i for i, g in enumerate(group_ids)}
        for c in components:
            # 1) hunger has top priority (6-step limit, travel takes a step)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, ids["eat"])
                continue
            # 2) send reinforcements to the cave if needed and fed enough
            if (c.role == "Warrior" and dragon.hp < 100
                    and cave_warriors + self._pending < wanted
                    and wheat >= 12 and c.hp > 1):
                environment.assign_group(c, ids["cave"])
                self._pending += 1
                continue
            # 3) spawn a warrior occasionally when rich in wheat
            if wheat > 40 and c.steps_since_meal <= 2 and step % 4 == 0:
                environment.assign_group(c, ids["spawn warrior"])
                continue
            # 4) default: farm
            environment.assign_group(c, ids["farm"])

        # resolve pending count roughly at end of step
        self._pending = 0

    def assign_in_cave(self, components, environment, group_ids, step: int):
        ids = {g: i for i, g in enumerate(group_ids)}
        dragon = environment.dragon
        for c in components:
            # starving -> go home to eat (travel takes one step, then eat)
            if c.steps_since_meal >= 4:
                environment.assign_group(c, ids["village"])
                continue
            # weak villagers retreat too
            if c.hp <= 1:
                environment.assign_group(c, ids["village"])
                continue
            # everyone else attacks (even farmers help once engaged)
            if dragon.hp > 0:
                environment.assign_group(c, ids["attack"])
            else:
                environment.assign_group(c, ids["village"])