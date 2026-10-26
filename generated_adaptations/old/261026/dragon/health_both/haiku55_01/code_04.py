from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    TARGET_WARRIORS = 6      # total warriors we want to maintain
    TARGET_FARMERS = 6       # total farmers we want to maintain early on
    MIN_FARMERS_IN_VILLAGE = 2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cave_warriors = 0   # warriors in cave, observed in last cave phase
        self.cave_farmers = 0    # farmers in cave, observed in last cave phase

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # 1) Every warrior goes to the cave to attack.
        for w in warriors:
            environment.assign_group(w, "cave")

        # Estimate total population for targets.
        total_warriors = len(warriors) + self.cave_warriors
        total_farmers = len(farmers) + self.cave_farmers

        # 2) If no warriors are (or will be) fighting, send farmers to attack.
        no_warriors_fighting = (total_warriors == 0)
        available = list(farmers)
        if dragon_hp > 0 and no_warriors_fighting:
            # Keep a minimum number of farmers in the village for farming/spawning.
            n_attackers = max(0, len(available) - self.MIN_FARMERS_IN_VILLAGE)
            n_attackers = min(n_attackers, max(1, len(available) // 2))
            for _ in range(n_attackers):
                environment.assign_group(available.pop(0), "cave")

        budget = wheat

        # 3) Spawn at most one pair per type per step, reassigned each step.
        #    Early on, grow the farmer population for wheat income.
        spawned_warrior = False
        spawned_farmer = False

        if (total_farmers < self.TARGET_FARMERS
                and budget >= 10 and len(available) >= 2):
            environment.assign_group(available.pop(0), "spawn farmer")
            environment.assign_group(available.pop(0), "spawn farmer")
            budget -= 10
            spawned_farmer = True

        if (total_warriors < self.TARGET_WARRIORS
                and budget >= 12 and len(available) >= 2):
            environment.assign_group(available.pop(0), "spawn warrior")
            environment.assign_group(available.pop(0), "spawn warrior")
            budget -= 12
            spawned_warrior = True

        # 4) Everyone else farms.
        for f in available:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        self.cave_warriors = len(warriors)
        self.cave_farmers = len(farmers)

        for w in warriors:
            environment.assign_group(w, "attack")

        for f in farmers:
            if warriors:
                # Warriors are present, so farmers return to the village.
                environment.assign_group(f, "village")
            else:
                # No warriors left: farmers keep the damage up.
                environment.assign_group(f, "attack")