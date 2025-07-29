import abc

from base_classes.adaptation import Adaptation
from dragon.simulation import DragonHuntSimulation, Map, VALID_IN_VILLAGE, VALID_IN_CAVE


class DragonHuntAdaptation(Adaptation, abc.ABC):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abc.abstractmethod
    def assign_in_village(self, components, environment, group_ids, step: int):
        pass

    @abc.abstractmethod
    def assign_in_cave(self, components, environment, group_ids, step: int):
        pass

    def adapt(self, simulation: "DragonHuntSimulation", step: int):
        # TODO: replace this with loading from the DSL and automatic check of user constraints and missing assignments
        self.assign_in_village(simulation.get_villagers_in(Map.VILLAGE), simulation, VALID_IN_VILLAGE, step)
        self.assign_in_cave(simulation.get_villagers_in(Map.CAVE), simulation, VALID_IN_CAVE, step)
