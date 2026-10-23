from dragon.components.villagers import Warrior


def remove_warriors(simulation):
    """Arrange the simulation to a state without warriors."""
    simulation.components = [c for c in simulation.components if not isinstance(c, Warrior)]
    return simulation


def hungry_villagers(simulation):
    """Arrange the simulation to a state where the villagers are hungry to a different extent."""
    interval = simulation.meal_interval or 8
    for i, villager in enumerate(simulation.components):
        villager.steps_since_meal = (3 * i + 2) % (interval - 1)  # e.g. 2, 5, 1 for interval 8 (all can still eat in time)
    return simulation
