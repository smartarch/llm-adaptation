You play a computer game. The goal is to kill a Dragon as fast as possible.
The Dragon lives in a Cave near a Village. The player controls villagers. The villagers can either be in the Village and work on a farm (and produce wheat) or they can go to the Cave, where they can attack the Dragon.
There are two types of villagers - farmers and warriors. Farmers produce more wheat when they work on a farm, and warriors deal more damage to the Dragon. Farmers start with 4 HP, produce 5 wheat when farming, and deal 1 damage when attacking. Warriors start with 6 HP, produce 2 wheat when farming, and deal 3 damage when attacking.
To spawn a new villager, at least two villagers must be in the "spawn" group and some wheat is consumed (12 for warriors, 10 for farmers).
When the Dragon is attacked, it can attack back. With 40% probability, it will cause 1 damage to every villager in the Cave, and with 20% probability, it will eat one random villager in the Cave. Dead villagers are removed from the game. If all the villagers die, you lose the game.
The Dragon starts with 50 HP and you win the game when it dies. If you don't kill the Dragon within 30 steps, you lose the game.


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

The `group_ids` argument is a list of all valid group names.

For each component, the following attributes are available (note that the attributes are read-only and they do not update when a component is assigned to a group):
- `role`: Role ("Farmer" or "Warrior")
- `hp`: Health
---
In `assign_in_cave`, your goal is to divide the Villagers in the Cave (`components`) into the following groups:
- A group named "attack": Attack the Dragon
- A group named "cave": Stay in the Cave
- A group named "village": Go to the Village

The `group_ids` argument is a list of all valid group names.

For each component, the following attributes are available (note that the attributes are read-only and they do not update when a component is assigned to a group):
- `role`: Role ("Farmer" or "Warrior")
- `hp`: Health
---

Further, you can access the following beyond-control components, which are only observable and cannot be assigned to groups.

The Dragon (accessible via `environment.dragon`) with the following attributes (note that the attributes are read-only and they do not update when a component is assigned to a group):
- `hp`: Health
The Farm (accessible via `environment.farm`) with the following attributes (note that the attributes are read-only and they do not update when a component is assigned to a group):
- `wheat`: Current wheat amount

---
All Warriors should go to the Cave, and then attack the Dragon. All Farmers should stay in Village and farm or spawn new villagers (both Farmers and Warriors are necessary).

The adaptation strategy must adhere to the following functional requirements:

- All warriors should go to the Cave to attack the Dragon.
- All farmers should stay in the Village.
- At least a few new farmers should be spawned to increase the chance of killing the dragon.
- At least a few new warriors should be spawned to increase the chance of killing the dragon.
- The Dragon should be attacked.
- The Dragon should be attacked at least once in the first 15 steps of the game.
- All warriors should attack the Dragon after moving to the Cave.
- At least half of the warriors should be in the Cave most of the time so they can attack the Dragon.

Think step by step. First, reason about the task and analyze the problem. Then, describe the adaptation strategy. After that, write the Python code for the adaptation strategy.
