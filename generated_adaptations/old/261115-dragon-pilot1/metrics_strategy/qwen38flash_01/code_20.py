from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # --- Warriors in Village ---
        for w in warriors:
            if w.steps_since_meal >= 2:
                # Eat to reset, next step we go fresh to cave
                environment.assign_group(w, "eat")
            elif dragon_hp <= 6:
                # Endgame rush
                environment.assign_group(w, "cave")
            else:
                # scm 0 or 1: go to cave (arrive scm 1 or 2, attack ~4 times)
                environment.assign_group(w, "cave")

        # --- Farmers in Village ---
        hungry = [f for f in farmers if f.steps_since_meal >= 4]
        available = [f for f in farmers if f.steps_since_meal < 4]

        for f in hungry:
            environment.assign_group(f, "eat")

        # --- Spawn logic: aggressive warrior spawning ---
        pool = available[:]

        if dragon_hp <= 6:
            # Endgame: send all available farmers to cave
            for f in pool:
                if f.steps_since_meal <= 2:
                    environment.assign_group(f, "cave")
                else:
                    environment.assign_group(f, "eat")
            available = []
        elif len(pool) >= 2 and wheat >= 12 and step >= 2:
            # Spawn warrior pair as often as possible
            environment.assign_group(pool[0], "spawn warrior")
            environment.assign_group(pool[1], "spawn warrior")
            available = pool[2:]
        elif len(pool) >= 2 and wheat >= 10 and step <= 1:
            # Early farmer boost
            environment.assign_group(pool[0], "spawn farmer")
            environment.assign_group(pool[1], "spawn farmer")
            available = pool[2:]
        else:
            available = pool

        for f in available:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        for c in components:
            if dragon_hp <= 4:
                # Final blow - everyone attacks
                environment.assign_group(c, "attack")
            elif c.role == "Warrior":
                if c.steps_since_meal >= 5:
                    # Leave now (arrive village at scm=6, eat that step costs 1HP)
                    environment.assign_group(c, "village")
                else:
                    # Attack at scm 0-4 (4 attacks per cycle)
                    environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                if dragon_hp <= 6:
                    environment.assign_group(c, "attack")
                else:
                    environment.assign_group(c, "village")