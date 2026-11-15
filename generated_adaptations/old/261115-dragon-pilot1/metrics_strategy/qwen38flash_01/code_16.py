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
            if w.steps_since_meal >= 6:
                # Must eat NOW (scm=6 means starving)
                environment.assign_group(w, "eat")
            elif w.steps_since_meal >= 2:
                # Eat to reset, then go to cave fresh (arrive scm=1, get 5 attacks)
                environment.assign_group(w, "eat")
            elif dragon_hp <= 8:
                # Endgame: rush to cave regardless
                environment.assign_group(w, "cave")
            else:
                # scm=0 or 1: go to cave immediately
                environment.assign_group(w, "cave")

        # --- Farmers in Village ---
        hungry = [f for f in farmers if f.steps_since_meal >= 4]
        available = [f for f in farmers if f.steps_since_meal < 4]

        for f in hungry:
            environment.assign_group(f, "eat")

        # --- Spawn warriors aggressively ---
        spawn_pool = available[:]

        if dragon_hp <= 8:
            # Endgame: no spawning, rush cave
            for f in spawn_pool:
                if f.steps_since_meal <= 2:
                    environment.assign_group(f, "cave")
                else:
                    environment.assign_group(f, "eat")
            available = []
        elif len(spawn_pool) >= 2 and wheat >= 12:
            # Spawn one warrior pair per step
            environment.assign_group(spawn_pool[0], "spawn warrior")
            environment.assign_group(spawn_pool[1], "spawn warrior")
            available = spawn_pool[2:]
        elif len(spawn_pool) >= 2 and wheat >= 10 and step <= 1:
            # Very early: spawn a farmer to boost economy
            environment.assign_group(spawn_pool[0], "spawn farmer")
            environment.assign_group(spawn_pool[1], "spawn farmer")
            available = spawn_pool[2:]
        else:
            available = spawn_pool

        # Remaining farmers farm
        for f in available:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        for c in components:
            if dragon_hp <= 5:
                # Absolutely everyone attacks - game will end in 1-2 steps
                environment.assign_group(c, "attack")
            elif c.role == "Warrior":
                if c.steps_since_meal >= 6:
                    # Starving: can't damage dragon, must leave
                    environment.assign_group(c, "village")
                elif dragon_hp <= 12 and c.steps_since_meal >= 5:
                    # Near end: even scm=5 attack is worth it, leave next step
                    environment.assign_group(c, "attack")
                else:
                    # Attack at scm 0-5 (6 consecutive attacks possible)
                    environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                if dragon_hp <= 8:
                    # Endgame: farmers help
                    environment.assign_group(c, "attack")
                else:
                    # Not useful in cave, go back to farm
                    environment.assign_group(c, "village")