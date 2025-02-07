import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulation import Simulation


class ComponentMeta(abc.ABCMeta):
    """
    Metaclass for Component. Uses a counter to automatically generate the component ID.
    """

    def __new__(mcs, name, bases, namespace):
        namespace['_count'] = 0  # initialize the counter
        return super().__new__(mcs, name, bases, namespace)


class Component(metaclass=ComponentMeta):
    """
    Base class for all components.

    Attributes
    ----------
    id : str
        Identifier of the component. Generated automatically.
    """
    id: str
    _count = 0  # Number of components of each type

    def __init__(self, simulation: "Simulation"):
        # generate the ID
        cls = type(self)
        cls._count += 1
        self.id = "%s_%d" % (cls.__name__, cls._count)
        self.simulation = simulation

    def actuate(self):
        """
        Behavior of the component which is executed once per time step. Should be developed by the framework user.
        """
        pass

    def __repr__(self) -> str:
        return self.id
