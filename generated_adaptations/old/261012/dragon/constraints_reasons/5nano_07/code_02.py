from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Village into:
        - farm: stay in Village and farm
        - cave: go to the Cave (will be re-assigned to attack in assign_in_cave)
        - spawn farmer: for every two villagers assigned to this group and 10 wheat, spawn a Farmer
        - spawn warrior: for every two villagers assigned to this group and 12 wheat, spawn a Warrior
        """
        # Separate by current role
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default assignments: Farmers -> farm, Warriors -> cave (they will attack in cave)
        for f in farmers:
            self.environment_assign_safe(f, environment, "farm")
        for w in warriors:
            self.environment_assign_safe(w, environment, "cave")

        # Spawning decisions (prefer to spawn using Farmers)
        spawn_farmers = set()
        spawn_warriors = set()

        available_wheat = getattr(environment, "farm").wheat if hasattr(environment, "farm") else 0

        # Attempt to spawn 1 farmer if possible
        if len(farmers) >= 2 and available_wheat >= 10:
            # pick two Farmers to spawn a farmer
            spawn_farmers.update(farmers[:2])

        # Attempt to spawn 1 warrior if possible (and enough farmers remain)
        remaining_for_warrior = [f for f in farmers if f not in spawn_farmers]
        if len(remaining_for_warrior) >= 2:
            # use two more to spawn a warrior if wheat allows
            if available_wheat >= 22 or (available_wheat >= 12 and len(spawn_farmers) == 0):
                spawn_warriors.update(remaining_for_warrior[:2])

        # Re-assign spawn groups
        for f in spawn_farmers:
            self.environment_assign_safe(f, environment, "spawn farmer")
        for f in spawn_warriors:
            self.environment_assign_safe(f, environment, "spawn warrior")

        # Ensure any remaining Farmers stay in farm
        # (We already assigned all farmers to either farm or spawn groups above.)
        # Warriors remain in cave unless assigned to spawn groups (which we avoided beyond the above).

    def assign_in_cave(self, components, environment, group_ids, step: int):
        """
        Divide Villagers in the Cave into:
        - attack: Attack the Dragon (all Warriors should attack)
        - cave: Stay in the Cave
        - village: Go to the Village (Farmers can return, or be in cave as needed)
        """
        for c in components:
            role = getattr(c, "role", None)
            if role == "Warrior":
                # All warriors should attack the dragon
                self.environment_assign_safe(c, environment, "attack")
            else:
                # Farmers stay in the Village
                self.environment_assign_safe(c, environment, "village")

    # Helper to safely assign (in case environment expects a plain call)
    def environment_assign_safe(self, component, environment, group_id):
        # Some environments may require access via the environment instance;
        # Use the provided method directly if available.
        if hasattr(environment, "assign_group"):
            environment.assign_group(component, group_id)
        else:
            # Fallback: if the base API changes, try a direct call attribute
            setattr(component, "group", group_id)