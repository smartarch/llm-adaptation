import pickle
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from adaptations.rl.q_network import DoubleQNetwork
from adaptations.rl.replay_buffer import ReplayBuffer, Transition
from adaptations.rl.rl_common import EpsilonSchedule, getRewardDroneStateConsistence, getRewardDroneCharging, \
    getRewardDroneProtecting, performDroneAction, getStateDrone, getStateField, getRewardData, epsilonGreedy, \
    initializeRewardData, droneActionsCount
from base_classes.adaptation import Adaptation
from components.drone import DroneState

if TYPE_CHECKING:
    from simulation import SmartFarmSimulation


class QNetworkAdaptation(Adaptation):

    def __init__(self, config: dict,
                 replay_buffer_size=10_000,
                 adapt_every=1,
                 epsilon=0.1, epsilon_final=None, epsilon_final_steps=None,
                 batch_size=64, train_every=1, target_update_every=1, save_path=None,
                 reward_shaping=None,
                 drone_state_battery=True,
                 **q_network_args):

        self.drone_state_battery = drone_state_battery
        self.droneActionsCount = droneActionsCount(config)
        self.charging = ("no_charging" not in config or not config["no_charging"])

        self.save_path = Path(save_path)
        if self.save_path.exists():  # load saved Q-network and replay buffer
            print("Loading Q-network and replay buffer from", self.save_path)
            self.replay_buffer = pickle.load(open(self.save_path / "replay_buffer.pkl", "rb"))
            self.q_network = DoubleQNetwork(self.stateSize(config), self.actionSize(config), batch_size=batch_size, **q_network_args, load_path=self.save_path)
            self.epsilon = EpsilonSchedule(epsilon, epsilon_final, epsilon_final_steps, load_path=self.save_path)
        else:
            print("Creating new Q-network and replay buffer")
            self.q_network = DoubleQNetwork(self.stateSize(config), self.actionSize(config), batch_size=batch_size, **q_network_args)
            self.replay_buffer = ReplayBuffer(replay_buffer_size)
            self.epsilon = EpsilonSchedule(epsilon, epsilon_final, epsilon_final_steps)

        self.batch_size = batch_size
        self.train_every = train_every
        self.target_update_every = target_update_every
        self.adapt_every = adapt_every

        self.last_state = None
        self.last_action = None
        self.reward_data = initializeRewardData(config)
        self.reward_shaping = reward_shaping if reward_shaping is not None else defaultdict(float)

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        # save last transition
        if self.last_state is not None:
            self.addTransition(simulation)

        # training
        if step % self.train_every == 0:
            self.train()
        if step % self.target_update_every == 0:
            self.q_network.update_target_network()

        # save data for reward computation
        self.reward_data = getRewardData(simulation)

        if (step - 1) % self.adapt_every != 0:
            return

        # select actions and perform adaptation
        self.selectActions(simulation, step)

    def getState(self, simulation):
        return np.concatenate([
            *[getStateDrone(drone, simulation, self.drone_state_battery) for drone in simulation.drones],
            *[getStateField(field) for field in simulation.fields],
        ])

    def stateSize(self, config):
        # Drone: state (one-hot), battery (optional), location (x, y), target field (one-hot)
        # Field: threat level, drone for full protection
        return (len(DroneState) + (1 if self.drone_state_battery else 0) + 2 + len(config["fields"])) * config["drones"] \
            + 2 * len(config["fields"])

    def getReward(self, simulation):
        current_damage = simulation.total_damage
        damage = current_damage - self.reward_data["damage"]

        drones_state_consistence = 0
        drones_charging = 0
        drones_protecting = 0

        for drone in simulation.drones:
            drones_state_consistence += getRewardDroneStateConsistence(self.reward_data, self.reward_shaping, drone)
            drones_charging += getRewardDroneCharging(self.reward_shaping, drone)
            drones_protecting += getRewardDroneProtecting(self.reward_shaping, drone)

        reward = -damage + drones_state_consistence + drones_charging + drones_protecting
        print(f"Reward = {reward:.2f} (damage = {-damage}, drones_state_consistence = {drones_state_consistence:.2f}, drones_charging = {drones_charging:.2f}, drones_protecting = {drones_protecting:.2f})")
        return reward

    def selectActions(self, simulation, step):
        """Selects an action for each drone using the predictions by a Q-network and epsilon-greedy algorithm."""
        state = self.getState(simulation)
        q_values = self.q_network.predict_one(state)
        self.last_state = state

        self.last_action = []
        for i, drone in enumerate(simulation.drones):
            if drone.state == DroneState.TERMINATED:
                continue
            action = epsilonGreedy(q_values[self.droneActionsCount * i: self.droneActionsCount * (i + 1)], self.epsilon, step)
            performDroneAction(drone, action, simulation, self.charging)
            self.last_action.append(action + i * self.droneActionsCount)

    def actionSize(self, config):
        return self.droneActionsCount * config["drones"]

    def addTransition(self, simulation):
        state = self.last_state
        action = self.last_action
        reward = self.getReward(simulation)
        next_state = self.getState(simulation)
        self.replay_buffer.append(Transition(state, action, reward, next_state))

    def train(self):
        if len(self.replay_buffer) < self.batch_size:
            return

        print("Training Q-network... ", end="")
        batch = self.replay_buffer.sample(self.batch_size)
        self.q_network.train(batch)
        print("Done")

    def end(self, simulation):
        print("Saving Q-network... ", end="")
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.q_network.save(self.save_path)
        pickle.dump(self.replay_buffer, open(self.save_path / "replay_buffer.pkl", "wb"))
        self.epsilon.save(self.save_path)
        print("Done")
