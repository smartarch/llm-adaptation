from dragon.components.villagers import Warrior


def remove_warriors(simulation):
    """Arrange the simulation to a state without warriors."""
    simulation.components = [c for c in simulation.components if not isinstance(c, Warrior)]
    return simulation


def set_initial_wheat(simulation, wheat: int):
    """Arrange the simulation to start with a different amount of wheat (everything else as in the config)."""
    simulation.farm.wheat = wheat
    return simulation
