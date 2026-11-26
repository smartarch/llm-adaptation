

Looking at the failures, I can identify several key issues:

1. **Dragon not killed**: The rotation pattern causes too much regen (dragon heals 5 HP/step when not attacked), and not enough warriors are spawned fast enough.
2. **No warriors spawned when needed**: The spawning logic was too conservative, especially when 0 warriors existed.
3. **Not spawning villagers when population is small**: Missing the rule about spawning when < 5 villagers with enough wheat and free farmers.

The core fix: be much more aggressive about spawning warriors (especially when 0 exist), keep a minimum number farming, stagger warriors going to the cave to maintain continuous attack coverage, and push all-out attack when dragon is low.

```py
import abc
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def assign_in_village(self, components, environment, group_ids, step):
        wheat = environment.farm.wheat
        dragon_hp = environment.dragon.hp
        all_warriors = environment.warriors
        all_farmers = environment.farmers
        num_warriors = len(all_warriors)
        num_farmers = len(all_farmers)
        total = num_warriors + num_farmers
        warriors_in_cave = sum(1 for w in all_warriors if w.location == "Cave")

        # Endgame: dragon low, send everyone to cave to attack
        if dragon_hp <= 30:
            for c in components:
                environment.assign_group(c, "cave")
            return

        # Categorize by hunger and role
        must_eat = []
        fresh_farmers = []
        fresh_warriors = []

        for c in components:
            if c.steps_since_meal >= 4:
                must_eat.append(c)
            elif c.role == "Farmer":
                fresh_farmers.append(c)
            else:
                fresh_warriors.append(c)

        # 1) Assign eaters first
        for v in must_eat:
            environment.assign_group(v, "eat")

        # 2) Determine spawning needs
        # Urgent spawn if: 0 warriors, or < 5 total villagers with free farmers
        need_warrior_spawn = (num_warriors == 0) or (num_warriors < 3 and warriors_in_cave == 0 and len(fresh_warriors) == 0)
        need_any_spawn = (total < 5) or need_warrior_spawn

        # Allocate farmers: keep enough farming, use excess for spawning
        # Minimum 2 farmers farming to sustain food supply
        min_farm = 2
        if num_warriors == 0 and len(fresh_farmers) >= 2:
            # Critical: no warriors. Sacrifice extra farming to spawn.
            min_farm = 1 if len(fresh_farmers) > 2 else 0

        farm_pool = []
        spawn_pool = []
        for f in fresh_farmers:
            if len(farm_pool) < min_farm:
                farm_pool.append(f)
            else:
                spawn_pool.append(f)

        # Execute warrior spawns from excess farmers
        remaining_wheat = wheat
        for i in range(0, len(spawn_pool) - 1, 2):
            if remaining_wheat >= 12 and need_any_spawn:
                environment.assign_group(spawn_pool[i], "spawn warrior")
                environment.assign_group(spawn_pool[i + 1], "spawn warrior")
                remaining_wheat -= 12
                need_any_spawn = (total + 1 < 5) or (num_warriors + 1 < 3 and need_warrior_spawn)
            else:
                environment.assign_group(spawn_pool[i], "farm")
                farm_pool.append(spawn_pool[i])
                environment.assign_group(spawn_pool[i + 1], "farm")
                farm_pool.append(spawn_pool[i + 1])

        if len(spawn_pool) % 2 == 1:
            environment.assign_group(spawn_pool[-1], "farm")
            farm_pool.append(spawn_pool[-1])

        # 3) Assign remaining farmers to farm
        for f in farm_pool:
            environment.assign_group(f, "farm")

        # 4) Send fresh warriors to cave, stagger if multiple fresh ones
        # If we have 2+ fresh warriors (steps_since_meal=0), stagger them
        # Send at most ceil(n/2) to cave now, rest stay (they'll go next step or after eating)
        if len(fresh_warriors) >= 2:
            # Split: half go to cave, half stay (will farm/eat/rotate)
            to_cave = fresh_warriors[::2]
            to_stay = fresh_warriors[1::2]
            for w in to_cave:
                environment.assign_group(w, "cave")
            for w in to_stay:
                environment.assign_group(w, "farm")  # stay in village, farm until hungry
        else:
            for w in fresh_warriors:
                environment.assign_group(w, "cave")

    def assign_in_cave(self, components, environment, group_ids, step):
        dragon_hp = environment.dragon.hp

        for c in components:
            if dragon_hp <= 30:
                # All-out assault: attack even if starving
                environment.assign_group(c, "attack")
            elif c.steps_since_meal >= 4:
                # Will hit 6 next step if we wait; go to village NOW
                # Arrives in village at steps_since_meal=5, eats immediately. Safe.
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```