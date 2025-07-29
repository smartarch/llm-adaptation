from DSL.dsl_utils import EnsembleInstance
from base_classes.components import Component


class ResolvedEnsemble:

    def __init__(self, ensemble_instance: EnsembleInstance, members: list[Component]):
        self.name = ensemble_instance.name
        self.__dict__.update(ensemble_instance.__dict__)
        self.ensemble_instance = ensemble_instance
        self.components = members

    @property
    def count(self):
        return len(self.components)

    def __len__(self):
        return self.count

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"ResolvedEnsemble(name={self.name}, count={self.count})"
