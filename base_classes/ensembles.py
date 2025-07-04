from base_classes.components import Component


class Ensemble:

    def __init__(self, ensemble_config: dict, members: list[Component]):
        self.name = ensemble_config["name"]
        self.__dict__.update(ensemble_config)
        self.components = members

    @property
    def count(self):
        return len(self.components)

    def __len__(self):
        return self.count

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Ensemble(name={self.name}, count={self.count})"
