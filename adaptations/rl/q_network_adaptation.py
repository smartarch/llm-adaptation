import pickle
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from adaptations.rl.q_network import DoubleQNetwork
from adaptations.rl.replay_buffer import ReplayBuffer, Transition
from base_classes.adaptation import Adaptation
from components.drone import DroneState, Drone
from components.field import Field

if TYPE_CHECKING:
    from simulation import SmartFarmSimulation


class QNetworkAdaptation(Adaptation):

    DroneActions = 5
    DroneState = len(DroneState) + 1 + 2
    FieldState = 1

    def __init__(self, config: dict, replay_buffer_size=10_000, epsilon=0.1, batch_size=64, train_every=1, target_update_every=1, save_path=None, **q_network_args):

        self.save_path = Path(save_path)
        if self.save_path.exists():  # load saved Q-network and replay buffer
            print("Loading Q-network and replay buffer from", self.save_path)
            self.replay_buffer = pickle.load(open(self.save_path / "replay_buffer.pkl", "rb"))
            self.q_network = DoubleQNetwork(self.stateSize(config), self.actionSize(config), batch_size=batch_size, **q_network_args, load_path=self.save_path)
        else:
            print("Creating new Q-network and replay buffer")
            self.q_network = DoubleQNetwork(self.stateSize(config), self.actionSize(config), batch_size=batch_size, **q_network_args)
            self.replay_buffer = ReplayBuffer(replay_buffer_size)

        self.epsilon = epsilon
        self.batch_size = batch_size
        self.train_every = train_every
        self.target_update_every = target_update_every

        self.last_state = None
        self.last_action = None
        self.last_damage = 0

    def adapt(self, simulation: "SmartFarmSimulation", step: int):
        # save last transition
        if self.last_state is not None:
            self.addTransition(simulation)

        # training
        if step % self.train_every == 0:
            self.train()
        if step % self.target_update_every == 0:
            self.q_network.update_target_network()

        # select actions and perform adaptation
        self.selectActions(simulation)

        # update last damage for reward computation
        self.last_damage = simulation.total_damage

    def getState(self, simulation):
        return np.concatenate([
            *[self.getStateDrone(drone, simulation) for drone in simulation.drones],
            *[self.getStateField(field) for field in simulation.fields],
        ])

    def stateSize(self, config):
        return self.DroneState * config["drones"] + self.FieldState * len(config["fields"])

    @staticmethod
    def getStateDrone(drone: "Drone", simulation):
        """drone.state (one-hot), drone.battery, drone.location (x, y)"""
        drone_state = np.zeros(len(DroneState))
        drone_state[drone.state.value] = 1
        x = drone.location.x / simulation.mapWidth
        y = drone.location.y / simulation.mapHeight
        return [*drone_state, drone.battery, x, y]

    @staticmethod
    def getStateField(field: "Field"):
        return [field.threat_level()]

    def getReward(self, simulation):
        current_damage = simulation.total_damage
        damage = current_damage - self.last_damage
        return -damage

    def selectActions(self, simulation):
        """Selects an action for each drone using the predictions by a Q-network and epsilon-greedy algorithm."""
        state = self.getState(simulation)
        q_values = self.q_network.predict_one(state)
        self.last_state = state

        self.last_action = []
        for i, drone in enumerate(simulation.drones):
            if drone.state == DroneState.TERMINATED:
                continue
            action = self.selectDroneAction(q_values[self.DroneActions * i: self.DroneActions * (i + 1)])
            self.performDroneAction(drone, action, simulation)
            self.last_action.append(action + i * self.DroneActions)

    def actionSize(self, config):
        return self.DroneActions * config["drones"]

    def selectDroneAction(self, q_values):
        epsilon = self.epsilon
        # TODO:
        # epsilon = np.interp(self.dispatched_jobs, [0, self.epsilon_final_after_jobs],
        #                     [self.epsilon_initial, self.epsilon_final])
        if np.random.uniform() >= epsilon:
            action = np.argmax(q_values)  # greedy
        else:
            action = np.random.randint(len(q_values))
        return action

    @staticmethod
    def performDroneAction(drone, action, simulation):
        if action == 0:  # idle
            drone.assignTarget(None)
        elif action == 1:  # charging
            drone.assignTarget(simulation.charger)
        else:  # protecting
            field_idx = action - 2
            drone.assignTarget(simulation.fields[field_idx])

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

    def end(self):
        print("Saving Q-network... ", end="")
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.q_network.save(self.save_path)
        pickle.dump(self.replay_buffer, open(self.save_path / "replay_buffer.pkl", "wb"))
        print("Done")
