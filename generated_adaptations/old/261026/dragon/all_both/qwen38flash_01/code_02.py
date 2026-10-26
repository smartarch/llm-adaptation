import math
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._spawn_counter = 0  # Track alternation between warrior/farmer spawns

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        wheat = environment.farm.wheat

        # All warriors in village must go to the cave immediately
        for w in warriors:
            environment.assign_group(w, "cave")

        # Farmer strategy: farm or spawn
        remaining_farmers = list(farmers)

        # Determine if we should spawn this step
        # We need at least 2 farmers to be useful for farming next round
        # Prioritize warriors (higher damage), but alternate to spawn farmers too
        should_spawn = False
        spawn_type = None

        if wheat >= 12 and len(remaining_farmers) >= 4:
            # Safe spawn: keep at least 2 farming
            should_spawn = True
        elif wheat >= 18 and len(remaining_farmers) >= 2:
            # Aggressive spawn: have enough wheat buffer even if no farming this step
            should_spawn = True

        if should_spawn:
            # Alternate between spawning warriors and farmers
            # Warriors are more important for damage, so spawn warriors more often
            if self._spawn_counter % 3 < 2:
                # Spawn warrior (every 3 steps, 2 out of 3 times)
                if wheat >= 12:
                    spawn_type = "spawn warrior"
                    self._spawn_counter += 1
                elif wheat >= 10:
                    spawn_type = "spawn farmer"
                    self._spawn_counter += 1
            else:
                # Spawn farmer (every 3 steps, 1 out of 3 times)
                if wheat >= 10:
                    spawn_type = "spawn farmer"
                    self._spawn_counter += 1
                elif wheat >= 12:
                    spawn_type = "spawn warrior"
                    self._spawn_counter += 1

            if spawn_type and len(remaining_farmers) >= 2:
                for f in remaining_farmers[:2]:
                    environment.assign_group(f, spawn_type)
                remaining_farmers = remaining_farmers[2:]

        # All remaining farmers produce wheat
        for f in remaining_farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        # In the cave, warriors should always attack the dragon
        # Any non-warrior units should be sent back to village
        for c in components:
            if c.role == "Warrior":
                environment.assign_group(c, "attack")
            else:
                # Farmers in cave (shouldn't normally happen) go back to village
                environment.assign_group(c, "village")