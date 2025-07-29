import abc

from base_classes.adaptation import DSLAdaptation


class FarmAdaptation(DSLAdaptation, abc.ABC):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abc.abstractmethod
    def assign_drones(self, components, environment, group_ids, step: int):
        pass
