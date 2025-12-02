from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step: int):
        # Villagers in Village: separate farmers and warriors
        farmers = [c for c in components if getattr(c, "role", None) == "Farmer"]
        warriors = [c for c in components if getattr(c, "role", None) == "Warrior"]

        # Default: farmers stay farming; warriors go to cave (to attack)
        for c in farmers:
            environment.assign_group(c, "farm")
        for c in warriors:
            environment.assign_group(c, "cave")

        # Read current wheat; be robust to missing data
        wheat = 0
        try:
            wheat = environment.farm.wheat
        except Exception:
            wheat = 0

        # Spawn planning: try to spawn a farmer if possible, and a warrior if possible
        spawn_farm_candidates = []
        if len(farmers) >= 2 and wheat >= 10:
            # Take any two farmers to join the spawn farmer group
            spawn_farm_candidates = farmers[:2]

        for c in spawn_farm_candidates:
            environment.assign_group(c, "spawn farmer")

        # Determine warrior spawn candidates; avoid using the same individuals as spawn_farm_candidates
        remaining_warriors_for_spawn = [w for w in warriors if w not in spawn_farm_candidates]
        spawn_war_candidates = []
        if len(remaining_warriors_for_spawn) >= 2 and wheat >= 12:
            spawn_war_candidates = remaining_warriors_for_spawn[:2]

        for c in spawn_war_candidates:
            environment.assign_group(c, "spawn warrior")

        # If we still need more early presence in the cave (e.g., step < 15)
        # ensure at least a couple of Warriors head to the cave for an early attack.
        if step < 15:
            extra_needed = 2
            extra_candidates = [w for w in remaining_warriors_for_spawn if w not in spawn_war_candidates]
            extra_to_send = extra_candidates[:min(extra_needed, len(extra_candidates))]
            for c in extra_to_send:
                environment.assign_group(c, "cave")

        # Note: Any villagers not explicitly moved above will keep their existing role-state
        # and will be re-evaluated in subsequent steps.

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the Cave: Warriors attack the Dragon; Farmers go back to Village
        for c in components:
            if getattr(c, "role", None) == "Warrior":
                environment.assign_group(c, "attack")
            else:
                environment.assign_group(c, "village")