import generated_adaptations.base_classes.dragon as dragon_base


class SmartAdaptation(dragon_base.DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_w = 0
        self.spawned_f = 0
        self.phase_done = False

    def assign_in_village(self, components, environment, group_ids, step):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        wheat = environment.farm.wheat

        # BOOTSTRAP PHASE (first few turns): grow farmer pool to 3+
        # Use 1 warrior + 1 farmer to spawn a farmer (costs 10 wheat)
        # Do this only ONCE to get from 2F to 3F
        if not self.phase_done and self.spawned_f < 1 and wheat >= 10 and len(warriors) >= 1 and len(farmers) >= 1:
            # Send other warriors to cave while we bootstrap
            for w in warriors[1:]:
                environment.assign_group(w, "cave")
            # Use 1 warrior + 1 farmer as spawn fodder for a new farmer
            environment.assign_group(warriors[0], "spawn farmer")
            environment.assign_group(farmers[0], "spawn farmer")
            self.spawned_f += 1
            self.phase_done = True
            # Remaining farmers farm
            for f in farmers[1:]:
                environment.assign_group(f, "farm")
            return

        # NORMAL PHASE: All warriors to cave, spawn aggressively
        for w in warriors:
            environment.assign_group(w, "cave")

        # Try to spawn warriors as aggressively as possible
        # Priority: 2 farmers → spawn warrior (keep 1+ farmers farming if possible)
        # If short on farmers but have a low-HP warrior, use it as fodder
        
        remaining_farmers = list(farmers)

        # Spawn warriors: prefer 2 farmers, fallback to 1 farmer + 1 warrior
        while wheat >= 12 and len(remaining_farmers) >= 3:
            # 2 farmers go to spawn, at least 1 remains to farm
            environment.assign_group(remaining_farmers[0], "spawn warrior")
            environment.assign_group(remaining_farmers[1], "spawn warrior")
            wheat -= 12
            self.spawned_w += 1
            remaining_farmers = remaining_farmers[2:]

        # If only 2 farmers left and wheat >= 12, still spawn (no farming this turn)
        # This is worth it if we're close to killing the dragon or have many warriors in cave
        if wheat >= 12 and len(remaining_farmers) == 2 and self.spawned_w >= 1:
            environment.assign_group(remaining_farmers[0], "spawn warrior")
            environment.assign_group(remaining_farmers[1], "spawn warrior")
            wheat -= 12
            self.spawned_w += 1
            remaining_farmers = []

        # If 0 or 1 farmers left and we still have wheat >= 10, spawn a farmer
        if wheat >= 10 and len(remaining_farmers) >= 2:
            environment.assign_group(remaining_farmers[0], "spawn farmer")
            environment.assign_group(remaining_farmers[1], "spawn farmer")
            wheat -= 10
            self.spawned_f += 1
            remaining_farmers = remaining_farmers[2:]

        # All remaining farmers farm
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        # ALL warriors in cave attack every single turn unconditionally
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")