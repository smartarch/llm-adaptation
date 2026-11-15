The adaptation strategy prioritizes early aggression while maintaining a stable economy. Warriors are sent to the Cave as soon as they are fed (steps_since_meal < 3), while hungry warriors stay in the Village to eat. Farmers remain in the Village, producing wheat or spawning new villagers. The spawn logic alternates between warriors and farmers to ensure at least two of each are created early. In the Cave, warriors attack unless they are close to starvation (steps_since_meal >= 4) or are at 3 and other less-hungry warriors can cover the attack; they then return to the Village to eat. A forced-attack mechanism ensures the Dragon is never left unattacked for more than two consecutive steps, preventing regeneration. Meals are strictly scheduled: any villager at 5 steps without food eats immediately, and warriors at 3+ steps are fed before returning to the Cave.

```python
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation

class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.spawned_farmers = 0
        self.spawned_warriors = 0
        self.last_attack_step = -10
        self.cave_count = 0
        self.last_spawn_step = -10
        self.target_spawn_farmers = 2
        self.target_spawn_warriors = 2

    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        total_pop = len(components) + getattr(self, 'cave_count', 0)
        reserve = total_pop + 2  # keep enough wheat for meals

        to_eat = []
        farmers_available = []
        warriors_to_cave = []

        for c in components:
            if c.steps_since_meal >= 5:
                to_eat.append(c)
            elif c.role == 'Warrior':
                if c.steps_since_meal >= 3:
                    to_eat.append(c)
                else:
                    warriors_to_cave.append(c)
            else:  # Farmer
                farmers_available.append(c)

        spawn_group = None
        spawn_pair = set()

        if len(farmers_available) >= 2 and step - self.last_spawn_step >= 1:
            need_w = self.spawned_warriors < self.target_spawn_warriors
            need_f = self.spawned_farmers < self.target_spawn_farmers

            # Alternate between spawning warriors and farmers to keep a balance
            if need_w and self.spawned_warriors <= self.spawned_farmers and wheat >= 12 + reserve:
                spawn_group = 'spawn warrior'
                spawn_pair = set(farmers_available[:2])
                self.spawned_warriors += 1
                self.last_spawn_step = step
            elif need_f and wheat >= 10 + reserve:
                spawn_group = 'spawn farmer'
                spawn_pair = set(farmers_available[:2])
                self.spawned_farmers += 1
                self.last_spawn_step = step
            elif need_w and wheat >= 12 + reserve:
                spawn_group = 'spawn warrior'
                spawn_pair = set(farmers_available[:2])
                self.spawned_warriors += 1
                self.last_spawn_step = step

        for c in components:
            if c in to_eat:
                environment.assign_group(c, 'eat')
            elif c in spawn_pair:
                environment.assign_group(c, spawn_group)
            elif c in warriors_to_cave:
                environment.assign_group(c, 'cave')
            elif c.role == 'Farmer':
                environment.assign_group(c, 'farm')
            else:
                environment.assign_group(c, 'farm')

    def assign_in_cave(self, components, environment, group_ids, step: int):
        self.cave_count = len(components)
        warriors = [c for c in components if c.role == 'Warrior']
        farmers = [c for c in components if c.role == 'Farmer']

        send_home = set()

        # 1. Send home any warrior that has not eaten for 4+ steps
        for w in warriors:
            if w.steps_since_meal >= 4:
                send_home.add(w)

        # 2. Handle warriors with steps_since_meal == 3
        threes = [w for w in warriors if w.steps_since_meal == 3 and w not in send_home]
        lows = [w for w in warriors if w.steps_since_meal < 3 and w not in send_home]

        if not lows and threes:
            # Keep one warrior to attack this step, send the rest home to eat
            keep = threes[0]
            for w in threes:
                if w != keep:
                    send_home.add(w)
        else:
            # If there are low-hunger warriors, send all threes home
            for w in threes:
                send_home.add(w)

        # 3. Determine attackers
        attackers = [w for w in warriors if w not in send_home]

        # 4. Force an attack if the dragon would regenerate (no attack for >2 steps)
        if not attackers and warriors:
            if step - getattr(self, 'last_attack_step', -10) > 2:
                forced = min(send_home, key=lambda x: x.steps_since_meal)
                send_home.remove(forced)
                attackers.append(forced)

        attacked = False
        for c in components:
            if c.role == 'Farmer':
                environment.assign_group(c, 'village')
            elif c in send_home:
                environment.assign_group(c, 'village')
            else:
                environment.assign_group(c, 'attack')
                attacked = True

        if attacked:
            self.last_attack_step = step
```