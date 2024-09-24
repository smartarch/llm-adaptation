import random
from enum import Enum

from base_classes.components2d import MovingComponent2D


class BirdState(Enum):
    IDLE = 0
    MOVING_TO_FIELD = 1
    EATING = 3
    FLEEING_WITHIN_FIELD = 4
    FLEEING_OUTSIDE = 5
    FLYING_RANDOMLY = 6


class Bird(MovingComponent2D):

    BirdSpeed = 1
    IdleToAttackProb = 0.2
    AttackToAttackProb = 0.5  # keep eating in the same field

    def __init__(self, simulation, location):
        """
        Parameters
        ----------
        location : Point2D
            initial location.
        """
        self.state = BirdState.IDLE
        self.field = None
        self.target = None
        self.ateThisTimeStep = False
        super().__init__(simulation, location, Bird.BirdSpeed)

    def actuate(self):
        if self.state == BirdState.IDLE:
            if random.random() < Bird.IdleToAttackProb:
                self.attackNewField()
        elif self.state in (BirdState.MOVING_TO_FIELD, BirdState.FLEEING_WITHIN_FIELD,
                            BirdState.FLEEING_OUTSIDE, BirdState.FLYING_RANDOMLY):
            self.flyToTarget()
        elif self.state == BirdState.EATING:
            if self.isScared():
                self.flee()
            else:
                self.damage()

    def isScared(self):
        """Returns true if bird is scared by a drone."""
        for drone in self.simulation.drones:
            if drone.protectsPoint(self.location):
                return True
        return False

    def flee(self):
        """Flee from the drones and fly away to an empty place. If there is an unprotected crop in the same field, fly there."""
        if self.field is not None:
            self.attackSameField(True)
        else:
            self.flyRandomly(BirdState.FLEEING_OUTSIDE)

    def attackNewField(self):
        self.field = random.choice(self.simulation.fields)
        self.target = self.field.randomUndamagedCrop()
        if self.target is not None:
            self.state = BirdState.MOVING_TO_FIELD
        else:
            self.state = BirdState.IDLE

    def attackSameField(self, fleeing):
        self.target = self.field.randomUnprotectedCrop()
        if self.target is not None:
            self.state = BirdState.FLEEING_WITHIN_FIELD if fleeing else BirdState.MOVING_TO_FIELD
        else:
            self.flyRandomly(BirdState.FLEEING_OUTSIDE if fleeing else BirdState.FLYING_RANDOMLY)

    def flyRandomly(self, newState):
        self.target = self.simulation.randomPoint()
        self.state = newState

    def damage(self):
        self.field.eatCrop(self.location)

        if random.random() < Bird.AttackToAttackProb:
            self.attackSameField(False)
        else:
            self.flyRandomly(BirdState.FLYING_RANDOMLY)

    def flyToTarget(self):
        if self.move(self.target):
            if self.state in (BirdState.MOVING_TO_FIELD, BirdState.FLEEING_WITHIN_FIELD):
                self.state = BirdState.EATING
            else:
                self.state = BirdState.IDLE

    def __repr__(self):
        return f"{self.id}({self.state})"
