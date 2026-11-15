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
            if dragon_hp <= 15:
                # Endgame: rush to cave unless starving
                if w.steps_since_meal >= 4:
                    environment.assign_group(w, "eat")
                else:
                    environment.assign_group(w, "cave")
            elif w.steps_since_meal >= 3:
                # Eat: arrive back at cave fresh, get 4 attacks
                environment.assign_group(w, "eat")
            elif w.steps_since_meal <= 1:
                # Fresh: go to cave (arrive scm<=2, can attack 4 times at scm 2-5)
                environment.assign_group(w, "cave")
            else:
                # scm==2: eat to be fresh, better than 3 attacks
                environment.assign_group(w, "eat")

        # --- Farmers in Village ---
        hungry_farmers = [f for f in farmers if f.steps_since_meal >= 4]
        available_farmers = [f for f in farmers if f.steps_since_meal < 4]

        for f in hungry_farmers:
            environment.assign_group(f, "eat")

        # --- Spawn logic: aggressively spawn warriors ---
        if dragon_hp > 15:
            # Normal phase: spawn warriors continuously
            if len(available_farmers) >= 2 and wheat >= 12:
                environment.assign_group(available_farmers[0], "spawn warrior")
                environment.assign_group(available_farmers[1], "spawn warrior")
                available_farmers = available_farmers[2:]
            elif len(available_farmers) >= 2 and wheat >= 10 and step <= 2:
                # Early: spawn a farmer to boost economy
                environment.assign_group(available_farmers[0], "spawn farmer")
                environment.assign_group(available_farmers[1], "spawn farmer")
                available_farmers = available_farmers[2:]

        # Remaining farmers farm
        for f in available_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        for c in components:
            if c.role == "Warrior":
                if dragon_hp <= 10:
                    # Absolute endgame: attack regardless of hunger
                    environment.assign_group(c, "attack")
                elif c.steps_since_meal >= 5:
                    # Must leave NOW: transit at scm=5→6 costs 1HP but prevents worse
                    environment.assign_group(c, "village")
                else:
                    # scm 0-4: attack (arrived at scm~1-2, attacking through 5 = 4 attacks)
                    environment.assign_group(c, "attack")
            elif c.role == "Farmer":
                # Farmers in cave: leave unless endgame
                if dragon_hp <= 5 and c.steps_since_meal < 5:
                    environment.assign_group(c, "attack")
                else:
                    environment.assign_group(c, "village")