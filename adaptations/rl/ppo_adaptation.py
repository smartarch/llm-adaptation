from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from adaptations.rl.ppo_network import PPONetwork
from adaptations.rl.rl_common import getRewardDroneStateConsistence, getRewardDroneCharging, \
    getRewardDroneProtecting, performDroneAction, getStateDrone, getStateField, getRewardData, DroneActions, \
    initializeRewardData
from base_classes.adaptation import Adaptation
from components.drone import DroneState

if TYPE_CHECKING:
    from simulation import SmartFarmSimulation
    from components.drone import Drone


class PPOAdaptation(Adaptation):

    Actions = np.arange(DroneActions)

    def __init__(self, config: dict,
                 adapt_every=1,
                 batch_size=64, epochs=5, save_path=None,
                 gamma=0.97, trace_lambda=0.95,
                 reward_shaping=None,
                 **ppo_network_args):

        self.network = PPONetwork(self.stateSize(config), DroneActions, **ppo_network_args)
        self.save_path = Path(save_path)
        if self.save_path.exists():  # load saved network
            print("Loading PPO network from", self.save_path)
            self.network.load_weights(self.save_path / "ppo_network.weights.h5")
        else:
            print("Creating new PPO network")

        self.adapt_every = adapt_every
        self.batch_size = batch_size
        self.epochs = epochs
        self.gamma = gamma
        self.trace_lambda = trace_lambda

        # Collect experience (list of steps for each drone)
        self.states = defaultdict(list)
        self.actions = defaultdict(list)
        self.action_probs = defaultdict(list)
        self.rewards = defaultdict(list)
        self.values = defaultdict(list)

        self.reward_data = initializeRewardData(config)
        self.reward_shaping = reward_shaping if reward_shaping is not None else defaultdict(float)

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        # save reward for last step
        if len(self.states) > 0:
            self.addTransition(simulation)

        # save data for reward computation
        self.reward_data = getRewardData(simulation)

        # select actions and perform adaptation
        self.selectActions(simulation, step)

    def getState(self, simulation):
        return np.array(
            [self.getStateDrone(simulation, drone)
             for drone in notTerminatedDrones(simulation)]
        )

    @staticmethod
    def getStateDrone(simulation, drone):
        return np.concatenate([
            getStateDrone(drone, simulation),
            *[getStateField(field) for field in simulation.fields],
        ])

    @staticmethod
    def stateSize(config):
        # Drone: state (one-hot), battery, location (x, y), target field (one-hot)
        # Field: threat level, drone for full protection
        return len(DroneState) + 1 + 2 + len(config["fields"]) \
            + 2 * len(config["fields"])

    def getReward(self, simulation, drone):
        current_damage = simulation.total_damage
        damage = current_damage - self.reward_data["damage"]

        drone_state_consistence = getRewardDroneStateConsistence(self.reward_data, self.reward_shaping, drone)
        drone_charging = getRewardDroneCharging(self.reward_shaping, drone)
        drone_protecting = getRewardDroneProtecting(self.reward_shaping, drone)

        reward = -damage + drone_state_consistence + drone_charging + drone_protecting
        print(f"Reward = {reward:.2f} (damage = {-damage}, drone_state_consistence = {drone_state_consistence:.2f}, drones_charging = {drone_charging:.2f}, drone_protecting = {drone_protecting:.2f})")
        return reward

    def selectActions(self, simulation, step):
        """Selects an action for each drone using the predicted policy."""
        # note that state is actually a list of states (one per non-terminated drone)
        state = self.getState(simulation)
        if len(state) == 0:  # all drones are terminated, nothing to do
            return

        policy, value = self.network.predict(state)

        if (step - 1) % self.adapt_every == 0:
            action = [np.random.choice(self.Actions, p=p) for p in policy]
        else:
            action = self.actions[-1]  # repeat last action
        action_prob = [p[a] for p, a in zip(policy, action)]

        for drone, a, ap, v, s in zip(notTerminatedDrones(simulation), action, action_prob, value, state):
            performDroneAction(drone, a, simulation)

            self.states[drone].append(s)
            self.actions[drone].append(a)
            self.action_probs[drone].append(ap)
            self.values[drone].append(v)

    def addTransition(self, simulation):
        for drone in notTerminatedDrones(simulation):
            self.rewards[drone].append(self.getReward(simulation, drone))

    def computeAdvantages(self, drone):
        """Computes the advantages using lambda-return."""
        rewards = self.rewards[drone]
        values = self.values[drone]
        steps = len(rewards)

        advantages = np.zeros(steps + 1)
        for t in range(steps - 1, -1, -1):
            td_error = rewards[t] - values[t] + self.gamma * values[t + 1]
            advantage = td_error + self.gamma * self.trace_lambda * advantages[t + 1]
            advantages[t] = advantage

        advantages = advantages[:-1]
        return advantages

    def train(self, simulation):
        print("Training PPO... ")

        advantages = [self.computeAdvantages(drone) for drone in simulation.drones]
        values = [self.values[drone][:-1] for drone in simulation.drones]
        returns = [advantage + value for advantage, value in zip(advantages, values)]

        # concatenate the experience for all drones and train the network
        history = self.network.fit(
            concatenateDict(self.states),
            {"actions": concatenateDict(self.actions),
             "action_probs": concatenateDict(self.action_probs),
             "advantages": np.concatenate(advantages),
             "returns": np.concatenate(returns)},
            batch_size=self.batch_size, epochs=self.epochs, verbose=0,
        )
        print(f"Training metrics: ", end="")
        for metric in history.history:
            print(f"{metric}: {history.history[metric][-1]:.2f}, ", end="")
        # TODO: save metrics to a file to visualize them
        print()

    def end(self, simulation):
        # save the last reward (we also need to add reward to terminated drones for their last action)
        self.addTransition(simulation)
        for drone in terminatedDrones(simulation):
            self.rewards[drone].append(0)  # TODO: this should probably be a negative number instead of 0
        # add values for next state (0 for terminated drones)
        state = self.getState(simulation)
        if len(state) > 0:
            values = self.network.predict(self.getState(simulation))[1]
            for drone, value in zip(notTerminatedDrones(simulation), values):
                self.values[drone].append(value)
        for drone in terminatedDrones(simulation):
            self.values[drone].append(0)

        self.train(simulation)

        print("Saving PPO network... ", end="")
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.network.save_weights(self.save_path / "ppo_network.weights.h5")
        print("Done")


def notTerminatedDrones(simulation):
    return filter(lambda d: d.state != DroneState.TERMINATED, simulation.drones)


def terminatedDrones(simulation):
    return filter(lambda d: d.state == DroneState.TERMINATED, simulation.drones)


def concatenateDict(data: dict["Drone", list[float | np.ndarray]]):
    # noinspection PyTypeChecker
    return np.concatenate(list(data.values()))
