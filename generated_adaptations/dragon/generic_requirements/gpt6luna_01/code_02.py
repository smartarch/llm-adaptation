from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_warriors = 0
        self.spawned_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp

        spawn_group = None
        if len(farmers) >= 2 and dragon_hp > 0:
            if self.spawned_warriors < 2 and wheat >= 12:
                spawn_group = "spawn warrior"
            elif self.spawned_farmers < 2 and wheat >= 10:
                spawn_group = "spawn farmer"
            elif (
                self.spawned_warriors < 4
                and step <= 12
                and wheat >= 24
            ):
                spawn_group = "spawn warrior"

        spawn_pair = set()
        if spawn_group is not None:
            # Use the lowest-health farmers for the temporary spawn assignment.
            pair = sorted(farmers, key=lambda c: c.hp)[:2]
            spawn_pair = {id(c) for c in pair}
            if spawn_group == "spawn warrior":
                self.spawned_warriors += 1
            else:
                self.spawned_farmers += 1

        for component in components:
            if component.role == "Warrior":
                environment.assign_group(component, "cave")
            elif id(component) in spawn_pair:
                environment.assign_group(component, spawn_group)
            else:
                environment.assign_group(component, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if component.role == "Warrior":
                environment.assign_group(component, "attack")
            else:
                # Farmers remain in the Village rather than fighting.
                environment.assign_group(component, "village")