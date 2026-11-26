from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    HUNGRY_IN_VILLAGE = 4   # eat when this many steps since meal (village)
    HUNGRY_IN_CAVE = 3      # leave cave when this hungry (travel takes 1 step)
    SPAWN_THRESHOLD = 25    # wheat needed before spawning a warrior
    WARRIOR_CAP = 10

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        warriors = environment.warriors
        farmers = environment.farmers

        total_warriors = len(warriors)
        # how many farmers are currently in the village (available as spawn parents)
        village_farmers = [f for f in farmers if f.location == "Village"
                           and f.steps_since_meal < self.HUNGRY_IN_VILLAGE]
        spawn_budget = wheat >= self.SPAWN_THRESHOLD and total_warriors < self.WARRIOR_CAP
        spawn_slots = 2 if spawn_budget and len(village_farmers) >= 4 else 0

        for c in components:
            if c.steps_since_meal >= self.HUNGRY_IN_VILLAGE and wheat > 0:
                environment.assign_group(c, "eat")
                wheat -= 1
                continue
            if c.role == "Warrior":
                if c.steps_since_meal >= 3 and wheat > 0:
                    environment.assign_group(c, "eat")
                    wheat -= 1
                else:
                    environment.assign_group(c, "cave")
            else:  # Farmer
                if spawn_slots >= 2:
                    environment.assign_group(c, "spawn warrior")
                    spawn_slots -= 2
                else:
                    environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        for c in components:
            if c.steps_since_meal >= self.HUNGRY_IN_CAVE:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")