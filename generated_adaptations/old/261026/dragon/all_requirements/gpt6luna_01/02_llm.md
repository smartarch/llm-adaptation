The strategy sends every village warrior to the Cave and keeps farmers in the Village, except that pairs of farmers can temporarily join a spawn group. It prioritizes spawning farmers early to strengthen wheat production, then uses available wheat to spawn warriors. In the Cave, warriors attack whenever the Dragon is alive; farmers return to the Village, with one early farmer attack as a fallback if no warriors are available to ensure the Dragon is attacked promptly. Every component is explicitly assigned on each call.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0
        self.farmer_spawn_target = 2
        self.warrior_spawn_target = 3
        self.early_farmer_attack_done = False

    @staticmethod
    def _assign(environment, component, group_name, group_ids):
        # The supplied group names are the valid group IDs.
        group_id = group_name if group_name in group_ids else group_name
        environment.assign_group(component, group_id)

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = [c for c in components if c.role == "Farmer"]
        warriors = [c for c in components if c.role == "Warrior"]

        wheat = environment.farm.wheat
        spawn_group = None

        # Use farmers for spawning so that village warriors can go straight
        # to the Cave. Spawn farmers first to grow the wheat supply.
        if len(farmers) >= 2:
            need_farmers = self.spawned_farmers < self.farmer_spawn_target
            need_warriors = self.spawned_warriors < self.warrior_spawn_target

            if need_farmers and wheat >= 10:
                spawn_group = "spawn farmer"
                self.spawned_farmers += 1
            elif need_warriors and wheat >= 12:
                spawn_group = "spawn warrior"
                self.spawned_warriors += 1

        # Assign every farmer, including the pair selected for spawning.
        spawn_pair = set()
        if spawn_group is not None:
            # Prefer healthy villagers for the pair; health does not otherwise
            # affect their farming or spawning.
            pair = sorted(farmers, key=lambda c: getattr(c, "hp", 0), reverse=True)[:2]
            spawn_pair = {id(c) for c in pair}
            for component in pair:
                self._assign(environment, component, spawn_group, group_ids)

        for component in farmers:
            if id(component) not in spawn_pair:
                self._assign(environment, component, "farm", group_ids)

        # Warriors are never held back in the Village for spawning.
        for component in warriors:
            self._assign(environment, component, "cave", group_ids)

    def assign_in_cave(self, components, environment, group_ids, step: int):
        dragon_alive = environment.dragon.hp > 0
        cave_warriors = [c for c in components if c.role == "Warrior"]
        cave_farmers = [c for c in components if c.role == "Farmer"]

        for component in cave_warriors:
            self._assign(
                environment,
                component,
                "attack" if dragon_alive else "cave",
                group_ids,
            )

        # Farmers normally return to the Village. If no warrior is available
        # early in the game, let one farmer make a single fallback attack.
        fallback = None
        if (
            dragon_alive
            and not cave_warriors
            and cave_farmers
            and step <= 14
            and not self.early_farmer_attack_done
        ):
            fallback = max(cave_farmers, key=lambda c: getattr(c, "hp", 0))
            self.early_farmer_attack_done = True

        for component in cave_farmers:
            if component is fallback:
                self._assign(environment, component, "attack", group_ids)
            else:
                self._assign(environment, component, "village", group_ids)
```