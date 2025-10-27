from dragon.components.villagers import Warrior


def remove_warriors(simulation):
    """Arrange the simulation to a state without warriors."""
    simulation.components = [c for c in simulation.components if not isinstance(c, Warrior)]
    return simulation
