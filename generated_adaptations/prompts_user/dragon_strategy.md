You play a computer game. The goal is to kill a Dragon as fast as possible.
The Dragon lives in a Cave near a Village. The player controls villagers. The villagers can either be in the Village and work on a farm (and produce wheat) or they can go to the Cave, where they can attack the Dragon. Moving between the Village and the Cave takes one step.
There are two types of villagers - farmers and warriors. Farmers produce more wheat when they work on a farm, and warriors deal more damage to the Dragon. Farmers start with 4 HP, produce 5 wheat when farming, and deal 1 damage when attacking. Warriors start with 6 HP, produce 2 wheat when farming, and deal 3 damage when attacking.
To spawn a new villager, at least two villagers must be in the "spawn" group and some wheat is consumed (12 for warriors, 10 for farmers).
Villagers need to eat regularly, and food is available only in the Village: a villager in the "eat" group eats a meal, which consumes 1 wheat. A villager that does not eat for 6 consecutive steps starves: they lose 1 HP in each step until they eat, and they are too weak to deal any damage to the Dragon. New villagers are spawned fed.
When the Dragon is attacked, it can attack back. With 40% probability, it will cause 1 damage to every villager in the Cave, and with 20% probability, it will eat one random villager in the Cave. Dead villagers are removed from the game. If all the villagers die, you lose the game.
After the Dragon is attacked for the first time, it regenerates 5 HP in each step in which nobody attacks it.
The Dragon starts with 100 HP and you win the game when it dies. If you don't kill the Dragon within 30 steps, you lose the game.


Suggest an adaptation strategy. The goal is to assign the components into groups. Note that each component must be assigned to exactly one group. If a component is supposed to remain in the same group (continue performing the same action), it must always be explicitly re-assigned to that group.

The strategy must be written in Python and it must be a class named `SmartAdaptation` derived from this base class (which can be imported from `generated_adaptations.base_classes.dragon`):
```
class DragonHuntAdaptation(abc.ABC):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abc.abstractmethod
    def assign_in_village(self, components, environment, group_ids, step: int):
        pass

    @abc.abstractmethod
    def assign_in_cave(self, components, environment, group_ids, step: int):
        pass

```
To perform the group assignments, use the `environment.assign_group(component, group_id)` method. The `group_id` must be exactly as listed below.

---
In `assign_in_village`, your goal is to divide the Villagers in the Village (`components`) into the following groups:
- A group named "farm": Stay in the Village and work on the farm
- A group named "cave": Go to the Cave
- A group named "spawn farmer": For every two villagers assigned to this group and 10 wheat, a new Farmer is spawned.
- A group named "spawn warrior": For every two villagers assigned to this group and 12 wheat, a new Warrior is spawned.
- A group named "eat": Eat a meal (consumes 1 wheat)

The `group_ids` argument is a list of all valid group names.

For each component, the following attributes are available (note that the attributes are read-only and they do not update when a component is assigned to a group):
- `role`: Role ("Farmer" or "Warrior")
- `hp`: Health
- `steps_since_meal`: Steps since last meal (number of consecutive steps in which the villager did not eat)
---
In `assign_in_cave`, your goal is to divide the Villagers in the Cave (`components`) into the following groups:
- A group named "attack": Attack the Dragon
- A group named "cave": Stay in the Cave
- A group named "village": Go to the Village

The `group_ids` argument is a list of all valid group names.

For each component, the following attributes are available (note that the attributes are read-only and they do not update when a component is assigned to a group):
- `role`: Role ("Farmer" or "Warrior")
- `hp`: Health
- `steps_since_meal`: Steps since last meal (number of consecutive steps in which the villager did not eat)
---

Further, you can access the following beyond-control components, which are only observable and cannot be assigned to groups.

The Dragon (accessible via `environment.dragon`) with the following attributes (note that the attributes are read-only and they do not update when a component is assigned to a group):
- `hp`: Health
The Farm (accessible via `environment.farm`) with the following attributes (note that the attributes are read-only and they do not update when a component is assigned to a group):
- `wheat`: Current wheat amount
The list of all Warriors (both in the Village and in the Cave, accessible via `environment.warriors`; only for observation, the villagers are assigned to groups via `components` in the method for their location) with the following attributes (note that the attributes are read-only and they do not update when a component is assigned to a group):
- `hp`: Health
- `steps_since_meal`: Steps since last meal (number of consecutive steps in which the villager did not eat)
- `location`: Location ("Village" or "Cave")
The list of all Farmers (both in the Village and in the Cave, accessible via `environment.farmers`; only for observation, the villagers are assigned to groups via `components` in the method for their location) with the following attributes (note that the attributes are read-only and they do not update when a component is assigned to a group):
- `hp`: Health
- `steps_since_meal`: Steps since last meal (number of consecutive steps in which the villager did not eat)
- `location`: Location ("Village" or "Cave")

---
To win the game, the Dragon must be killed within 30 steps. All Warriors should go to the Cave and then attack the Dragon at least twice before they return to eat. All Farmers should stay in the Village. Every villager must eat at least once in every 6 consecutive steps. Plan the meals in advance so that no villager starves - Warriors need one step to get back to the Village and it might be necessary to keep wheat in reserve for future meals. If there is enough wheat to spawn a new villager and still keep a wheat reserve for meals in the next step, the Farmers in the Village should spawn a new villager (both Farmers and Warriors are necessary to win the game), otherwise, they should farm wheat. If no Warriors are alive, a new one should be spawned within 5 steps.
