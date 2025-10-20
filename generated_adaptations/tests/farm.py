def arrange(simulation, protecting_drones, arrange_steps):
    """Arrange the simulation to a specific state by randomly assigning and simulating a number of steps."""
    simulation.random_assign_and_simulate(protecting_drones, arrange_steps)
    return simulation
