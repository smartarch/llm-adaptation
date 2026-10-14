from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    FARMER_CAP = 6          # stop spawning farmers beyond this count
    FINISH_HP_THRESHOLD = 10  # send farmers to fight when the dragon is this weak

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role == "Farmer"]

        # Warriors always go to the cave to attack the dragon
        for w in warriors:
            environment.assign_group(w, "cave")

        # Late game: when the dragon is nearly dead, farmers also join the fight
        if dragon_hp <= self.FINISH_HP_THRESHOLD:
            for f in farmers:
                environment.assign_group(f, "cave")
            return

        # Choose at most one spawn per step, using a pair of farmers
        spawn_target = None
        if len(farmers) >= 2:
            if wheat >= 12:
                spawn_target = "spawn warrior"
            elif wheat >= 10 and len(farmers) < self.FARMER_CAP:
                spawn_target = "spawn farmer"

        spawn_pair = farmers[:2] if spawn_target is not None else []

        for f in farmers:
            if f in spawn_pair:
                environment.assign_group(f, spawn_target)
            else:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = environment.dragon.hp
        for c in components:
            if c.role == "Warrior":
                # Warriors keep attacking; they never retreat
                environment.assign_group(c, "attack")
            else:
                # Farmers only fight in the finishing phase
                if dragon_hp <= self.FINISH_HP_THRESHOLD:
                    environment.assign_group(c, "attack")
                else:
                    environment.assign_group(c, "village")