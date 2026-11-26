**Strategy description:**

- **Eating safety:** A villager starves after 6 consecutive steps without eating. So:
  - In the Cave, any villager with `steps_since_meal >= 4` is sent to the Village (travel takes a step, so they arrive at 5 and eat on the next step, before HP loss).
  - In the Village, any villager with `steps_since_meal >= 4` is assigned to "eat".
- **Combat:** Warriors in the Cave attack the Dragon every step (unless rotating home to eat). Farmers in the Cave are sent back to the Village — they are weak attackers and better used for wheat.
- **Economy:** Farmers stay in the Village and farm. Villagers not eating/farming may be used for spawning: we keep spawning warriors (2 per spawn, 12 wheat) while the warrior count is below a target, and spawn farmers if the farmer population gets too low and wheat allows. Spawned villagers are fed, so they start fresh.
- The attack continues every step so the Dragon never gets to regenerate, and its low HP pool means a steady stream of warriors kills it quickly within the 30-step limit.

```py
from generated_adaptations.base_classes.dragon import DragonHuntAdaptation


class SmartAdaptation(DragonHuntAdaptation):
    def assign_in_village(self, components, environment, group_ids, step: int):
        wheat = environment.farm.wheat
        warriors = [w for w in environment.warriors if w.hp > 0]
        farmers = [f for f in environment.farmers if f.hp > 0]
        n_warriors = len(warriors)
        n_farmers = len(farmers)

        eating = []
        available = []
        for c in components:
            if c.steps_since_meal >= 4:
                eating.append(c)
            else:
                available.append(c)

        farmers_present = sum(1 for f in farmers if f.location == "Village")
        warriors_present = sum(1 for w in warriors if w.location == "Village")

        # Spawning: prefer warriors while below target; keep farmer base alive.
        spawn_warriors = []
        spawn_farmers = []
        budget = wheat - len(eating)  # reserve wheat for meals

        # Keep at least 2 farmers farming so the economy keeps going.
        if n_farmers < 4 and budget >= 20 + 10:
            need = 2
            while need > 0 and available:
                spawn_farmers.append(available.pop(0))
                need -= 1
            budget -= 10

        if n_warriors < 8:
            while budget >= 24 and len(available) >= 2:
                spawn_warriors.extend([available.pop(0), available.pop(0)])
                budget -= 12

        assigned_spawn_w = set(id(c) for c in spawn_warriors)
        assigned_spawn_f = set(id(c) for c in spawn_farmers)
        assigned_eat = set(id(c) for c in eating)

        for c in components:
            cid = id(c)
            if cid in assigned_eat:
                environment.assign_group(c, "eat")
            elif cid in assigned_spawn_w:
                environment.assign_group(c, "spawn warrior")
            elif cid in assigned_spawn_f:
                environment.assign_group(c, "spawn farmer")
            else:
                environment.assign_group(c, "farm")

    def assign_in_cave(self, components, environment, group_ids, step: int):
        for c in components:
            if c.steps_since_meal >= 4:
                # Go home to eat: travel 1 step, arrive hungry, eat next step.
                environment.assign_group(c, "village")
            elif c.role == "Farmer":
                # Farmers are poor attackers; send them back to farm.
                environment.assign_group(c, "village")
            else:
                environment.assign_group(c, "attack")
```