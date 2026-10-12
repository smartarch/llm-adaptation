from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Separate villagers by role
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Helper to assign a single component
        def assign(c, grp):
            environment.assign_group(c, grp)

        # 1) If no warriors yet and we are in the first 15 steps, try to spawn a Warrior
        if len(warriors) == 0 and step <= 15 and len(farmers) >= 2:
            # Need at least 12 wheat to spawn a Warrior (with 2 farmers in group)
            if environment.farm.wheat >= 12:
                # Put two farmers into the spawn warrior group to trigger a spawn
                assign(farmers[0], "spawn warrior")
                assign(farmers[1], "spawn warrior")
                # The rest of farmers go to farming
                for c in farmers[2:]:
                    assign(c, "farm")
                # All existing farmers accounted for; done for this step
                # Warriors (none currently) would be handled by later steps
                return
            else:
                # Not enough wheat yet; fall back to normal distribution
                for f in farmers:
                    assign(f, "farm")
                for w in warriors:
                    assign(w, "cave")
                return

        # 2) Normal path: move all existing Warriors to the Cave (to prep for attack)
        for w in warriors:
            assign(w, "cave")

        # 3) Farmers: decide to spawn farmers if wheat allows; otherwise farm
        if len(farmers) >= 2 and environment.farm.wheat >= 10:
            # Spawn up to 2 farmers this step if possible (requires 10 wheat)
            to_spawn_farmers = min(2, len(farmers))
            # Put first few to spawn farmer
            for f in farmers[:to_spawn_farmers]:
                assign(f, "spawn farmer")
            # The rest (if any) go to farming
            for f in farmers[to_spawn_farmers:]:
                assign(f, "farm")
        else:
            # Nothing to spawn or not enough wheat, all farmers farm
            for f in farmers:
                assign(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, all Warriors should attack; Farmers should go back to Village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")