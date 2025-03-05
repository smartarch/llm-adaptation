from pathlib import Path

import numpy as np

from farm.components.drone import DroneState, Drone
from farm.components.field import Field


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


# state


def getStateDrone(drone: "Drone", simulation, include_battery=True):
    """drone.state (one-hot), drone.battery, drone.location (x, y)"""
    drone_state = np.zeros(len(DroneState))
    drone_state[DroneState.get_index(drone.state)] = 1
    x = drone.location.x / simulation.mapWidth
    y = drone.location.y / simulation.mapHeight
    target_field = [1 if drone.target == field else 0 for field in simulation.fields]
    if include_battery:
        return [*drone_state, drone.battery, x, y, *target_field]
    else:
        return [*drone_state, x, y, *target_field]


def getStateField(field: "Field"):
    return [field.threat_level, field.remaining_drones_for_full_protection / len(field.protectionPlaces)]


# action


def droneActionsCount(config):
    actionCount = 1  # idle
    if "noCharging" not in config or not config["noCharging"]:
        actionCount += 1  # charging
    actionCount += len(config["fields"])  # protect
    return actionCount


def epsilonGreedy(q_values, epsilon: EpsilonSchedule, step):
    if np.random.uniform() >= epsilon(step):
        action = np.argmax(q_values)  # greedy
    else:
        action = np.random.randint(len(q_values))
    return action


def performDroneAction(drone, action, simulation, charging=True):
    if not charging and action >= 1:
        action += 1  # skip the charging action and move to protecting
    if action == 0:  # idle
        drone.assignTarget(None)
    elif action == 1:  # charging
        drone.assignTarget(simulation.charger)
    else:  # protecting
        field_idx = action - 2
        drone.assignTarget(simulation.fields[field_idx])


# reward shaping


def getRewardDroneStateConsistence(reward_data, reward_shaping: dict, drone):
    old_state = reward_data["drone_states"][drone]
    old_target = reward_data["drone_targets"][drone]
    if (drone.state != DroneState.TERMINATED
            and old_state == drone.state
            and old_target == drone.target):
        return reward_shaping.get("reward_state_consistence", 0)
    else:
        return 0


def getRewardDroneCharging(reward_shaping: dict, drone):
    if drone.battery < reward_shaping.get("reward_drone_charging_battery", 0):
        if drone.state == DroneState.CHARGING:
            return reward_shaping.get("reward_drone_charging", 0)
        if drone.state == DroneState.MOVING_TO_CHARGER:
            return reward_shaping.get("reward_drone_moving_to_charger", 0)
    return 0


def getRewardDroneProtecting(reward_shaping: dict, drone):
    reward = 0
    if drone.battery > reward_shaping.get("reward_drone_protecting_battery", 0):
        if drone.state == DroneState.PROTECTING:
            if drone.target.isFullyProtected and reward_shaping.get("reward_drone_protecting_full", 0) > 0:
                reward = reward_shaping.get("reward_drone_protecting_full", 0)
            else:
                reward = reward_shaping.get("reward_drone_protecting", 0)
        elif drone.state == DroneState.MOVING_TO_FIELD:
            reward = reward_shaping.get("reward_drone_moving_to_field", 0)

    if reward_shaping.get("protecting_reward_threat_level", False) and drone.target is not None:
        reward *= drone.target.threat_level
    return reward


def getRewardData(simulation):
    """Get data necessary to compute the reward in the next step."""
    return {
        "damage": simulation.total_damage,
        "drone_states": {drone: drone.state for drone in simulation.drones},
        "drone_targets": {drone: drone.target for drone in simulation.drones},
    }


def initializeRewardData(config):
    return {  # necessary to compute the reward in the next step
        "damage": 0,
        "drone_states": [None] * config["drones"],
        "drone_targets": [None] * config["drones"],
    }
