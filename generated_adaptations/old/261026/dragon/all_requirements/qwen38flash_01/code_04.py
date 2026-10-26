import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._total_spawns = 0

    def assign_in_village(self, components, environment, group_ids, step):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # Late game: if dragon is nearly dead, send everyone to cave for final blow
        if dragon_hp <= 8:
            for w in warriors:
                environment.assign_group(w, "cave")
            for f in farmers:
                environment.assign_group(f, "cave")
            return

        # All warriors go to the Cave to attack the Dragon
        for w in warriors:
            environment.assign_group(w, "cave")

        n_farmers = len(farmers)

        # Determine what to spawn: alternate warrior/farmer spawns
        # Track total spawns to alternate
        want_warrior = (self._total_spawns % 2 == 0)

        # Try to spawn
        spawn_done = False

        if want_warrior and wheat >= 12 and n_farmers >= 3:
            # Use 2 farmers to spawn a warrior, keep at least 1 farming
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
            self._total_spawns += 1
            spawn_done = True
        elif not want_warrior and wheat >= 10 and n_farmers >= 3:
            # Use 2 farmers to spawn a farmer, keep at least 1 farming
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
            self._total_spawns += 1
            spawn_done = True
        elif wheat >= 12 and n_farmers >= 3:
            # Try warrior spawn even if not alternating (ensure warriors get spawned)
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
            self._total_spawns += 1
            spawn_done = True
        elif wheat >= 10 and n_farmers >= 3:
            # Try farmer spawn
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
            self._total_spawns += 1
            spawn_done = True
        elif wheat >= 12 and n_farmers == 2:
            # Only 2 farmers: spawn a warrior (will need to wait a step for wheat)
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
            self._total_spawns += 1
            spawn_done = True
        elif wheat >= 10 and n_farmers == 2:
            # Only 2 farmers: spawn a farmer
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
            self._total_spawns += 1
            spawn_done = True

        if not spawn_done:
            for f in farmers:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        # All villagers in cave attack the Dragon
        for c in components:
            environment.assign_group(c, "attack")