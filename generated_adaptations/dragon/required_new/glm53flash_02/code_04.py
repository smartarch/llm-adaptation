from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    EAT_AT = 4          # eat in village when this hungry
    LEAVE_CAVE_AT = 3   # leave cave when this hungry (arrive at 4, eat)
    WARRIOR_CAP = 12

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        total_warriors = len(environment.warriors)
        total_villagers = total_warriors + len(environment.farmers)

        emergency = step >= 22 and total_warriors > 0
        assault = total_warriors >= 5 or step >= 14 or emergency

        # how many villagers need to eat this step (reserve wheat for them)
        hungry_count = sum(1 for c in components if c.steps_since_meal >= self.EAT_AT)

        # spawn planning (only while there's still time to use the new units)
        spawn_w = 0
        spawn_f = 0
        if not emergency and step < 18:
            reserve = hungry_count + 8  # buffer for food + future meals
            if wheat - reserve >= 12 and total_warriors < self.WARRIOR_CAP:
                spawn_w = 2
            if wheat - reserve - 12 >= 30 and total_villagers < 10 and step < 12:
                spawn_f = 2

        spawn_slots = spawn_w + spawn_f

        for c in components:
            # 1) eating has top priority
            if c.steps_since_meal >= self.EAT_AT and wheat > 0:
                environment.assign_group(c, "eat")
                wheat -= 1
                continue

            # 2) spawn duties
            if spawn_slots > 0:
                if spawn_w >= 2:
                    environment.assign_group(c, "spawn warrior")
                    spawn_w -= 1
                    spawn_slots -= 1
                    wheat -= 6
                elif spawn_f >= 2:
                    environment.assign_group(c, "spawn farmer")
                    spawn_f -= 1
                    spawn_slots -= 1
                    wheat -= 5
                continue

            # 3) warriors fight when the assault is on
            if c.role == "Warrior":
                if assault:
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "farm")
                continue

            # 4) farmers: farm (or join emergency assault)
            if emergency:
                environment.assign_group(c, "cave")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.steps_since_meal >= self.LEAVE_CAVE_AT:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")