import random
from enum import Enum
from math import isclose

from base_classes.components import Component
from base_classes.components2d import MovingComponent2D


class BirdState(Enum):
    IDLE = 0
    MOVING_TO_FIELD = 1
    EATING = 3
    FLEEING_WITHIN_FIELD = 4
    FLEEING_OUTSIDE = 5
    FLYING_RANDOMLY = 6


class BirdFieldProbabilityGenerator(Component):

    def __init__(self, simulation, birdFieldProbabilities, birdCohesion=0.5):
        super().__init__(simulation)

        for step, probabilities in birdFieldProbabilities.items():
            assert isclose(sum(probabilities), 1), f"Probabilities for step {step} must sum to 1"
            assert len(probabilities) == len(self.simulation.fields), f"Number of probabilities for step {step} must match number of fields"
        self.birdFieldProbabilities = birdFieldProbabilities
        self.step = 0
        self.birdCohesion = birdCohesion

    def actuate(self):
        self.step += 1

    def __call__(self):
        return self.interpolateProbabilities(
            self.computeStepProbabilities(),
            self.birdDistributionInFields(),
            t=self.birdCohesion)

    def computeStepProbabilities(self):
        for step in reversed(self.birdFieldProbabilities):
            if self.step >= step:
                return self.birdFieldProbabilities[step]

    @staticmethod
    def interpolateProbabilities(probabilities1, probabilities2, t=0.5):
        return [(1 - t) * p1 + t * p2 for p1, p2 in zip(probabilities1, probabilities2)]

    def birdDistributionInFields(self):
        threatLevels = [field.threat_level() for field in self.simulation.fields]
        sumThreatLevels = sum(threatLevels)
        if sumThreatLevels == 0:
            return [1 / len(threatLevels) for _ in threatLevels]
        return [level / sumThreatLevels for level in threatLevels]


class Bird(MovingComponent2D):

    BirdSpeed = 1
    IdleToAttackProb = 0.2
    AttackToAttackProb = 0.6  # keep eating in the same field
    MaxFleeInSameField = 3
    WaitBeforeEat = 2  # steps to wait before damage is dealt
    NearbyBirdsToEat = 2  # number of other eating birds nearby to deal damage (otherwise just fly away)
    NearbyBirdsRadius = 3

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
        self.fleeCounter = 0
        self.eatWaitCounter = 0
        super().__init__(simulation, location, Bird.BirdSpeed)

    def actuate(self):
        if self.state == BirdState.IDLE:
            if random.random() < Bird.IdleToAttackProb:
                self.attackNewField()
        elif self.state in (BirdState.MOVING_TO_FIELD, BirdState.FLYING_RANDOMLY):
            if self.isScared():
                self.flee()
            else:
                self.flyToTarget()
        elif self.state in (BirdState.FLEEING_WITHIN_FIELD, BirdState.FLEEING_OUTSIDE):
            self.flyToTarget()
        elif self.state == BirdState.EATING:
            if self.isScared():
                self.flee()
            else:
                if self.eatWaitCounter > 0:
                    self.eatWaitCounter -= 1
                else:
                    if self.areThereNearbyEatingBirds():
                        self.damage()
                    else:
                        self.afterEating()

    def areThereNearbyEatingBirds(self):
        if Bird.NearbyBirdsToEat == 0:
            return True
        nearbyEatingBirds = 0
        for bird in self.simulation.birds:
            if bird != self and bird.location.distance(self.location) < Bird.NearbyBirdsRadius and bird.state == BirdState.EATING:
                nearbyEatingBirds += 1
        return nearbyEatingBirds >= Bird.NearbyBirdsToEat

    def isScared(self):
        """Returns true if bird is scared by a drone."""
        for drone in self.simulation.drones:
            if drone.protectsPoint(self.location):
                return True
        return False

    def flee(self):
        """Flee from the drones and fly away to an empty place. If there is an unprotected crop in the same field, fly there."""
        if self.field is not None and self.fleeCounter < Bird.MaxFleeInSameField:
            self.fleeCounter += 1
            self.attackSameField(True)
        else:
            self.flyRandomly(BirdState.FLEEING_OUTSIDE)

    def attackNewField(self):
        self.field = random.choices(self.simulation.fields, weights=self.simulation.fieldProbabilityGenerator())[0]
        self.fleeCounter = 0
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
        self.afterEating()

    def afterEating(self):
        if random.random() < Bird.AttackToAttackProb:
            self.attackSameField(False)
        else:
            self.flyRandomly(BirdState.FLYING_RANDOMLY)

    def flyToTarget(self):
        if self.move(self.target):
            if self.state in (BirdState.MOVING_TO_FIELD, BirdState.FLEEING_WITHIN_FIELD):
                self.state = BirdState.EATING
                self.eatWaitCounter = Bird.WaitBeforeEat
            else:
                self.state = BirdState.IDLE

    def __repr__(self):
        return f"{self.id}({self.state})"
