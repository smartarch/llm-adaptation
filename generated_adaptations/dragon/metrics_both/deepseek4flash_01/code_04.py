from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_attack_step = -10

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        farmers = [c for c in components if c.role == 'Farmer']

        # Determine who must eat
        to_eat = set()
        for c in components:
            if c.steps_since_meal >= 5:
                # Mandatory meal to avoid starvation
                to_eat.add(c)
            elif c.role == 'Warrior' and c.steps_since_meal >= 2:
                # Warriors at 2+ should reset; going at 2 yields fewer attacks
                to_eat.add(c)

        avail_farmers = [f for f in farmers if f not in to_eat]
        reserve = len(components) + 1

        # Spawn logic: prioritize warriors, but keep at least 3-4 farmers
        spawn_group = None
        spawn_pair = []
        if len(avail_farmers) >= 2:
            if wheat >= 12 + reserve:
                spawn_group = 'spawn warrior'
                spawn_pair = avail_farmers[:2]
            elif wheat >= 10 + reserve and len(farmers) < 4:
                spawn_group = 'spawn farmer'
                spawn_pair = avail_farmers[:2]

        # Assign every component exactly once
        for c in components:
            if c in to_eat:
                environment.assign_group(c, 'eat')
            elif c in spawn_pair:
                environment.assign_group(c, spawn_group)
            elif c.role == 'Warrior' and c.steps_since_meal < 2:
                environment.assign_group(c, 'cave')
            else:
                environment.assign_group(c, 'farm')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        send_home = set()
        for c in components:
            if c.role != 'Warrior':
                # Farmers shouldn't be here, send them back
                send_home.add(c)
            elif c.steps_since_meal >= 6:
                # Too weak to deal damage; must return to eat
                send_home.add(c)

        attacked = False
        for c in components:
            if c in send_home:
                environment.assign_group(c, 'village')
            else:
                environment.assign_group(c, 'attack')
                attacked = True

        if attacked:
            self.last_attack_step = step