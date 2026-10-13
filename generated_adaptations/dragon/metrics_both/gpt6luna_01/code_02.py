from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._farmers_spawned = 0
        self._warriors_spawned = 0
        self._last_spawn_step = -100

    def assign_in_village(self, components, environment, group_ids, step: int):
        farmers = []
        for component in components:
            if str(component.role).lower() == "warrior":
                environment.assign_group(component, "cave")
            else:
                farmers.append(component)

        # Default every Farmer to farming; selected pairs are reassigned below.
        for farmer in farmers:
            environment.assign_group(farmer, "farm")

        if not group_ids or len(farmers) < 2:
            return

        dragon_hp = getattr(environment.dragon, "hp", 1)
        if dragon_hp <= 0:
            return

        wheat = getattr(environment.farm, "wheat", 0)
        spawn_role = None

        # Meet both minimum spawn goals, alternating so the economy and combat
        # force grow together. Spawn Warriors first when the goals are tied.
        need_farmers = self._farmers_spawned < 2
        need_warriors = self._warriors_spawned < 2

        if need_farmers or need_warriors:
            if need_warriors and (
                not need_farmers
                or self._warriors_spawned <= self._farmers_spawned
            ):
                spawn_role = "spawn warrior"
            else:
                spawn_role = "spawn farmer"
        # Once both goals are met, use surplus wheat for extra Warriors while
        # retaining at least one Farmer to keep producing wheat.
        elif (
            len(farmers) >= 3
            and wheat >= 24
            and step - self._last_spawn_step >= 2
        ):
            spawn_role = "spawn warrior"

        if spawn_role is None:
            return

        cost = 12 if spawn_role == "spawn warrior" else 10
        if wheat < cost:
            return

        for farmer in farmers[:2]:
            environment.assign_group(farmer, spawn_role)

        if spawn_role == "spawn warrior":
            self._warriors_spawned += 1
        else:
            self._farmers_spawned += 1
        self._last_spawn_step = step

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for component in components:
            if str(component.role).lower() == "warrior":
                environment.assign_group(component, "attack")
            else:
                environment.assign_group(component, "village")