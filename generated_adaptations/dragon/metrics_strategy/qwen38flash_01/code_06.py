import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0
        self.MAX_EXTRA_WARRIORS = 5
        self.MAX_EXTRA_FARMERS = 3

    def _assign_in_village_go_cave(self, env, c):
        env.assign_group(c, "cave")

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        # --- Emergency: if dragon is nearly dead or we're late, send EVERYTHING to the cave ---
        late = step >= 18
        # estimate current max damage if all village villagers attacked now (1 per farmer, 3 per warrior)
        potential_dmg = sum(3 if c.role == "Warrior" else 1 for c in components)
        commit_all = late or dragon_hp <= potential_dmg

        if commit_all:
            for c in components:
                environment.assign_group(c, "cave")
            return

        # --- Warriors always go to the cave to start attacking ASAP ---
        for w in warriors:
            self._assign_in_village_go_cave(environment, w)

        n_f = len(farmers)
        if n_f == 0:
            return

        # --- Spawning decisions for farmers ---
        # Need >=3 farmers to spawn (2 for the spawn group + at least 1 farming)
        can_spawn = n_f >= 3

        # Priority A: spawn warriors while we still want more offense
        if can_spawn and self.spawned_warriors < self.MAX_EXTRA_WARRIORS and wheat >= 12:
            environment.assign_group(farmers[0], "spawn warrior")
            environment.assign_group(farmers[1], "spawn warrior")
            self.spawned_warriors += 1
            # the rest farm
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
            return

        # Priority B: spawn farmers to grow the economy
        if can_spawn and self.spawned_farmers < self.MAX_EXTRA_FARMERS and wheat >= 10:
            environment.assign_group(farmers[0], "spawn farmer")
            environment.assign_group(farmers[1], "spawn farmer")
            self.spawned_farmers += 1
            for f in farmers[2:]:
                environment.assign_group(f, "farm")
            return

        # Default: everyone farms
        for f in farmers:
            environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_hp = environment.dragon.hp
        late = step >= 18

        # Estimate total damage if every villager in cave attacks this step
        total_dmg = sum(3 if c.role == "Warrior" else 1 for c in components)
        # If we can finish the dragon now, everyone swings
        finish_now = dragon_hp <= total_dmg

        for c in components:
            if finish_now or late:
                # All-out assault, do not send anyone back
                environment.assign_group(c, "attack")
            else:
                # Normal play: warriors attack, weak villagers retreat to preserve
                if c.hp <= 1:
                    environment.assign_group(c, "village")
                elif c.role == "Warrior":
                    environment.assign_group(c, "attack")
                else:
                    # Farmer in cave: usually send back to farm (1 dmg is low value)
                    environment.assign_group(c, "village")