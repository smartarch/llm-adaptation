import numpy as np

from farm.adaptations.rl.q_network_adaptation import QNetworkAdaptation
from farm.adaptations.rl.replay_buffer import Transition
from farm.adaptations.rl.rl_common import getRewardDroneStateConsistence, getRewardDroneCharging, getRewardDroneProtecting, \
    getStateDrone, getStateField, performDroneAction, epsilonGreedy
from farm.components.drone import DroneState


class QNetworkAdaptationDrone(QNetworkAdaptation):

    def getState(self, simulation, drone):
        return np.concatenate([
            getStateDrone(drone, simulation, self.drone_state_battery),
            *[getStateField(field) for field in simulation.fields],
        ])

    def stateSize(self, config):
        # Drone: state (one-hot), battery (optional), location (x, y), target field (one-hot)
        # Field: threat level, drone for full protection
        return len(DroneState) + (1 if self.drone_state_battery else 0) + 2 + len(config["fields"]) \
            + 2 * len(config["fields"])

    def selectActions(self, simulation, step):
        """Selects an action for each drone using the predictions by a Q-network and epsilon-greedy algorithm."""
        self.last_action = {}
        self.last_state = {}
        for i, drone in enumerate(simulation.drones):
            if drone.state == DroneState.TERMINATED:
                continue

            state = self.getState(simulation, drone)
            q_values = self.q_network.predict_one(state)
            self.last_state[drone] = state

            print(f"Q-values: {[f'{q:.2g}' for q in q_values]}")

            action = epsilonGreedy(q_values, self.epsilon, step)
            performDroneAction(drone, action, simulation, self.charging)
            self.last_action[drone] = action

    def actionSize(self, config):
        return self.droneActionsCount

    def getReward(self, simulation, drone):
        current_damage = simulation.total_damage
        damage = current_damage - self.reward_data["damage"]

        drone_state_consistence = getRewardDroneStateConsistence(self.reward_data, self.reward_shaping, drone)
        drone_charging = getRewardDroneCharging(self.reward_shaping, drone)
        drone_protecting = getRewardDroneProtecting(self.reward_shaping, drone)

        reward = -damage + drone_state_consistence + drone_charging + drone_protecting
        print(f"Reward = {reward:.2f} (damage = {-damage}, drone_state_consistence = {drone_state_consistence:.2f}, drones_charging = {drone_charging:.2f}, drone_protecting = {drone_protecting:.2f})")
        return reward

    def addTransition(self, simulation):
        for drone in self.last_state:  # only not-terminated drones
            state = self.last_state[drone]
            action = self.last_action[drone]
            reward = self.getReward(simulation, drone)
            next_state = self.getState(simulation, drone)
            self.replay_buffer.append(Transition(state, action, reward, next_state))
