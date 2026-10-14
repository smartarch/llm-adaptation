import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0
        self.MAX_EXTRA_WARRIORS = 5
        self.MAX_EXTRA_FARMERS = 2
        self.attack_started = False

    def _all_to_cave(self, environment, components):
        for c in components:
            environment.assign_group(c, "cave")

    def assign_in_village(self, components, environment, group_ids, step: int):
        if not components:
            return

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # If attack phase has started, send ALL villagers to cave and join the assault.
        if self.attack_started:
            self._all_to_cave(environment, components)
            return

        # Panic: too late to farm, send everyone.
        if step >= 22 or dragon_hp <= 8:
            self.attack_started = True
            self._all_to_cave(environment, components)
            return

        # Warriors from village head to cave (they will stay there safely).
        for w in warriors:
            environment.assign_group(w, "cave")

        n_f = len(farmers)
        if n_f == 0:
            return

        # Aggressive warrior spawning: we accept that the 2 spawner farmers
        # do not farm this step, because the spawned warrior hides safely
        # in the cave and the remaining farmers keep the wheat flowing.
        if (n_f >= 2 and self.spawned_warriors < self.MAX_EXTRA_WARRIORS
                and wheat >= 12):
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
            self.spawned_warriors += 1
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
            return

        # Spawn a farmer only when we have surplus (>=3 farmers so one keeps farming).
        if (n_f >= 3 and self.spawned_farmers < self.MAX_EXTRA_FARMERS
                and wheat >= 10):
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
            self.spawned_farmers += 1
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
            return

        # Default: farm.
        for f in farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        if not components:
            return

        dragon_hp = environment.dragon.hp
        warriors_in_cave = [c for c in components if c.role == "Warrior"]
        farmers_in_cave = [c for c in components if c.role == "Farmer"]

        # Compute damage if EVERYONE in cave attacks this step.
        total_dmg = 3 * len(warriors_in_cave) + 1 * len(farmers_in_cave)

        # Trigger conditions for the assault.
        start_attack = (
            self.attack_started
            or len(warriors_in_cave) >= 4
            or step >= 7
            or (total_dmg >= dragon_hp and len(warriors_in_cave) >= 2)
            or step >= 22
        )

        if start_attack:
            self.attack_started = True
            for c in components:
                environment.assign_group(c, "attack")
        else:
            # Accumulation phase: warriors hide (no retaliation), farmers
            # go home to farm / spawn.
            for c in components:
                if c.role == "Warrior":
                    environment.assign_group(c, "cave")
                else:
                    environment.assign_group(c, "village")