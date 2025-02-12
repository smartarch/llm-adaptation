import abc

from base_classes.components import Component


class Simulation(abc.ABC):

    def __init__(self, adapt: callable, config: dict):
        self.config = config
        self.adapt = adapt
        self.components: list[Component] = []
        self.beyond_control_components: list[Component] = []

        self.visualizer = None
        self.stats = None

    def run_simulation(self, steps: int):
        for step in range(1, steps + 1):
            print(f"Step: {step}")

            self.simulation_step(step)

            if self.stats:
                self.stats.write_row(step)
            if self.visualizer:
                self.visualizer.drawComponents(step)

            if self.should_stop():
                break

    def simulation_step(self, step):
        self.adapt(self, step)

        for component in self.components + self.beyond_control_components:
            component.actuate()

    def should_stop(self):
        return False

    def add_visualizer(self, visualizer):
        self.visualizer = visualizer

    def add_stats(self, stats):
        self.stats = stats

    @staticmethod
    def get_globals():
        """Returns the classes and global functions as a dictionary that can be used in `eval`."""
        return {}

    @abc.abstractmethod
    def assign_group(self, component: Component, group_id: str):
        pass
