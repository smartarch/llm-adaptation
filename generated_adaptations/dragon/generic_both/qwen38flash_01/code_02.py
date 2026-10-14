import generated_adaptations.base_classes.dragon as dragon_base


class SmartAdaptation(dragon_base.DragonHuntAdaptation):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # All warriors in the village should head to the cave to attack
        for w in warriors:
            environment.assign_group(w, "cave")

        # --- Spawning logic ---
        # We want to spawn at least 2 new warriors and 2 new farmers total.
        # Priority order: warriors first (3 dmg), then farmers (more wheat).
        # Need 2 villagers in the spawn group + wheat to spawn.
        assigned = set()

        # Try to spawn warriors
        if wheat >= 12 and len(farmers) >= 4:
            for f in farmers[:2]:
                environment.assign_group(f, "spawn warrior")
                assigned.add(id(f))
            self.spawned_warriors += 1
            wheat -= 12

        if wheat >= 12 and len(farmers) >= 4:
            remaining = [f for f in farmers if id(f) not in assigned]
            if len(remaining) >= 2:
                for f in remaining[:2]:
                    environment.assign_group(f, "spawn warrior")
                    assigned.add(id(f))
                self.spawned_warriors += 1
                wheat -= 12

        # Try to spawn farmers (needed for long-term wheat production)
        # Slightly delayed to let warrior spawning go first in early game
        if wheat >= 10 and len(farmers) >= 4 and (step >= 3 or self.spawned_warriors >= 2):
            remaining = [f for f in farmers if id(f) not in assigned]
            if len(remaining) >= 2:
                for f in remaining[:2]:
                    environment.assign_group(f, "spawn farmer")
                    assigned.add(id(f))
                self.spawned_farmers += 1
                wheat -= 10

        if wheat >= 10 and len(farmers) >= 4 and self.spawned_farmers < 2:
            remaining = [f for f in farmers if id(f) not in assigned]
            if len(remaining) >= 2:
                for f in remaining[:2]:
                    environment.assign_group(f, "spawn farmer")
                    assigned.add(id(f))
                self.spawned_farmers += 1
                wheat -= 10

        # All unassigned farmers go farm
        for f in farmers:
            if id(f) not in assigned:
                environment.assign_group(f, "farm")

    def assign_in_cave(self, components, environment, group_ids, step):
        # Separate warriors and other units
        warriors_in_cave = [c for c in components if c.role == "Warrior"]

        for c in warriors_in_cave:
            if c.hp <= 1:
                # Protect critically wounded warriors; send back to village
                # This ensures at least half (those with >1 HP) stay and attack
                environment.assign_group(c, "village")
            else:
                # Healthy warriors attack the Dragon every turn
                environment.assign_group(c, "attack")

        # Any non-warrior (Farmer) in the cave should return to the village
        for c in components:
            if c.role != "Warrior":
                environment.assign_group(c, "village")