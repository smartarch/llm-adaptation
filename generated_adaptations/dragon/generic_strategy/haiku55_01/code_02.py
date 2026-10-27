from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    # Warriors leave the cave for food once they have gone this many steps without eating
    CAVE_HUNGER_LIMIT = 3
    # Farmers eat once they have gone this many steps without eating
    FARM_HUNGER_LIMIT = 4
    # Target population sizes (spawning stops once reached)
    TARGET_WARRIORS = 4
    TARGET_FARMERS = 4

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Population counts observed in the cave on the last cave step
        self._cave_warriors = 0
        self._cave_farmers = 0

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        # Total population estimate = villagers here + villagers seen in cave last step
        total_warriors = len(warriors) + self._cave_warriors
        total_farmers = len(farmers) + self._cave_farmers

        # 1) Decide who eats (most hungry first, limited by wheat)
        def needs_meal(c):
            if c.role == "Warrior":
                return c.steps_since_meal >= 1
            return c.steps_since_meal >= self.FARM_HUNGER_LIMIT

        hungry = sorted([c for c in components if needs_meal(c)],
                        key=lambda c: c.steps_since_meal, reverse=True)
        eating = []
        for c in hungry:
            if wheat >= 1:
                eating.append(c)
                wheat -= 1
        eating_ids = set(id(c) for c in eating)

        for c in eating:
            environment.assign_group(c, "eat")

        # 2) Spawning from farmers that are not eating
        free_farmers = [c for c in farmers if id(c) not in eating_ids]
        spawn_used = set()

        def take_pair():
            pair = [c for c in free_farmers if id(c) not in spawn_used][:2]
            return pair

        # Warriors are the priority for damage, but ensure at least 2 of each role
        while len(take_pair()) == 2:
            pair = take_pair()
            want_warrior = total_warriors < self.TARGET_WARRIORS and wheat >= 12
            want_farmer = total_farmers < self.TARGET_FARMERS and wheat >= 10
            if want_warrior and (total_warriors < 2 or total_warriors <= total_farmers or not want_farmer):
                for c in pair:
                    environment.assign_group(c, "spawn warrior")
                    spawn_used.add(id(c))
                wheat -= 12
                total_warriors += 1
            elif want_farmer:
                for c in pair:
                    environment.assign_group(c, "spawn farmer")
                    spawn_used.add(id(c))
                wheat -= 10
                total_farmers += 1
            else:
                break

        # 3) Everyone else in the village
        for c in components:
            if id(c) in eating_ids or id(c) in spawn_used:
                continue
            if c.role == "Warrior" and c.steps_since_meal == 0:
                # Fed warrior: go fight
                environment.assign_group(c, "cave")
            elif c.role == "Warrior":
                # Hungry but no wheat to eat: stay put rather than fight hungry
                environment.assign_group(c, "farm")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        warriors = [c for c in components if c.role == "Warrior"]
        farmers = [c for c in components if c.role != "Warrior"]

        # Farmers should never be here; send them home
        for c in farmers:
            environment.assign_group(c, "village")

        # Warriors that must eat, most hungry first
        hungry = sorted([c for c in warriors if c.steps_since_meal >= self.CAVE_HUNGER_LIMIT],
                        key=lambda c: c.steps_since_meal, reverse=True)
        leave = hungry
        # Keep at least one warrior attacking so the Dragon is not left unattacked
        if warriors and len(leave) == len(warriors):
            leave = leave[:-1]
        leave_ids = set(id(c) for c in leave)

        for c in warriors:
            if id(c) in leave_ids:
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")

        # Remember the cave population for spawn planning in the village
        self._cave_warriors = len(warriors)
        self._cave_farmers = len(farmers)