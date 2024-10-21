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


class EpsilonSchedule:

    def __init__(self, epsilon_start, epsilon_final=None, epsilon_final_steps=None, load_path=None):
        self.epsilon_start = epsilon_start
        self.epsilon_final = epsilon_final
        self.epsilon_final_steps = epsilon_final_steps

        self.initial_step = 0
        if load_path is not None:
            try:
                with open(load_path / "epsilon_step.txt", "r") as f:
                    self.initial_step = int(f.read())
                    print(f"Loaded epsilon step: {self.initial_step}")
            except FileNotFoundError:
                print("Epsilon step file not found")
        self.current_step = self.initial_step

    def __call__(self, step) -> float:
        if self.epsilon_final is None:
            return self.epsilon_start

        self.current_step = self.initial_step + step
        return float(np.interp(self.current_step, [0, self.epsilon_final_steps], [self.epsilon_start, self.epsilon_final]))

    def save(self, save_path: Path):
        with open(save_path / "epsilon_step.txt", "w") as f:
            f.write(str(self.current_step))


class QNetworkAdaptation(Adaptation):

    DroneActions = 5

    def __init__(self, config: dict,
                 replay_buffer_size=10_000,
                 epsilon=0.1, epsilon_final=None, epsilon_final_steps=None,
                 batch_size=64, train_every=1, target_update_every=1, save_path=None,
                 reward_state_consistence=0,
                 reward_drone_charging=0, reward_drone_charging_battery=0,
                 reward_drone_protecting=0, reward_drone_protecting_battery=0,
                 **q_network_args):

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

        self.last_state = None
        self.last_action = None
        self.reward_data = {  # necessary to compute the reward in the next step
            "damage": 0,
            "drone_states": [None] * config["drones"],
            "drone_targets": [None] * config["drones"],
        }
        self.reward_state_consistence = reward_state_consistence
        self.reward_drone_charging = reward_drone_charging
        self.reward_drone_charging_battery = reward_drone_charging_battery
        self.reward_drone_protecting = reward_drone_protecting
        self.reward_drone_protecting_battery = reward_drone_protecting_battery

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
        self.reward_data = self.getRewardData(simulation)

        # select actions and perform adaptation
        self.selectActions(simulation, step)

    def getState(self, simulation):
        return np.concatenate([
            *[self.getStateDrone(drone, simulation) for drone in simulation.drones],
            *[self.getStateField(field) for field in simulation.fields],
        ])

    @staticmethod
    def stateSize(config):
        # Drone: state (one-hot), battery, location (x, y), target field (one-hot)
        # Field: threat level, drone for full protection
        return (len(DroneState) + 1 + 2 + len(config["fields"])) * config["drones"] \
            + 2 * len(config["fields"])

    @staticmethod
    def getStateDrone(drone: "Drone", simulation):
        """drone.state (one-hot), drone.battery, drone.location (x, y)"""
        drone_state = np.zeros(len(DroneState))
        drone_state[drone.state.value] = 1
        x = drone.location.x / simulation.mapWidth
        y = drone.location.y / simulation.mapHeight
        target_field = [1 if drone.target == field else 0 for field in simulation.fields]
        return [*drone_state, drone.battery, x, y, *target_field]

    @staticmethod
    def getStateField(field: "Field"):
        return [field.threat_level(), field.drones_for_full_protection() / len(field.protectionPlaces)]

    def getReward(self, simulation):
        current_damage = simulation.total_damage
        damage = current_damage - self.reward_data["damage"]

        drones_state_consistence = 0
        drones_charging = 0
        drones_protecting = 0

        for drone in simulation.drones:
            drones_state_consistence += self.getRewardDroneStateConsistence(drone)
            drones_charging += self.getRewardDroneCharging(drone)
            drones_protecting += self.getRewardDroneProtecting(drone)

        reward = -damage + drones_state_consistence + drones_charging + drones_protecting
        print(f"Reward = {reward:.2f} (damage = {-damage}, drones_state_consistence = {drones_state_consistence:.2f}, drones_charging = {drones_charging:.2f}, drones_protecting = {drones_protecting:.2f})")
        return reward

    def getRewardDroneStateConsistence(self, drone):
        old_state = self.reward_data["drone_states"][drone]
        old_target = self.reward_data["drone_targets"][drone]
        if (drone.state != DroneState.TERMINATED
                and old_state == drone.state
                and old_target == drone.target):
            return self.reward_state_consistence
        else:
            return 0

    def getRewardDroneCharging(self, drone):
        if (drone.state in (DroneState.CHARGING, DroneState.MOVING_TO_CHARGER)
                and drone.battery < self.reward_drone_charging_battery):
            return self.reward_drone_charging
        else:
            return 0

    def getRewardDroneProtecting(self, drone):
        if (drone.state in (DroneState.PROTECTING, DroneState.MOVING_TO_FIELD)
                and drone.battery > self.reward_drone_protecting_battery):
            return self.reward_drone_protecting
        else:
            return 0

    @staticmethod
    def getRewardData(simulation):
        """Get data necessary to compute the reward in the next step."""
        return {
            "damage": simulation.total_damage,
            "drone_states": {drone: drone.state for drone in simulation.drones},
            "drone_targets": {drone: drone.target for drone in simulation.drones},
        }

    def selectActions(self, simulation, step):
        """Selects an action for each drone using the predictions by a Q-network and epsilon-greedy algorithm."""
        state = self.getState(simulation)
        q_values = self.q_network.predict_one(state)
        self.last_state = state

        self.last_action = []
        for i, drone in enumerate(simulation.drones):
            if drone.state == DroneState.TERMINATED:
                continue
            action = self.selectDroneAction(q_values[self.DroneActions * i: self.DroneActions * (i + 1)], step)
            self.performDroneAction(drone, action, simulation)
            self.last_action.append(action + i * self.DroneActions)

    def actionSize(self, config):
        return self.DroneActions * config["drones"]

    def selectDroneAction(self, q_values, step):
        if np.random.uniform() >= self.epsilon(step):
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
        self.epsilon.save(self.save_path)
        print("Done")
