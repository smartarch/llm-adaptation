from base_classes.components import Component
from DSL.dsl_utils import EnsembleInstance


class ResolvedEnsemble(EnsembleInstance):

    def __init__(self, ensemble_instance: EnsembleInstance, members: list[Component]):
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

    def __contains__(self, item):
        return item in self.components
