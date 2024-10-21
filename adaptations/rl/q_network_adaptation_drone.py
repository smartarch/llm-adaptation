import numpy as np

from adaptations.rl.q_network_adaptation import QNetworkAdaptation
from adaptations.rl.replay_buffer import Transition
from components.drone import DroneState


class QNetworkAdaptationDrone(QNetworkAdaptation):

    def getState(self, simulation, drone):
        return np.concatenate([
            self.getStateDrone(drone, simulation),
            *[self.getStateField(field) for field in simulation.fields],
        ])

    @staticmethod
    def stateSize(config):
        # Drone: state (one-hot), battery, location (x, y), target field (one-hot)
        # Field: threat level, drone for full protection
        return len(DroneState) + 1 + 2 + len(config["fields"]) \
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

            action = self.selectDroneAction(q_values, step)
            self.performDroneAction(drone, action, simulation)
            self.last_action[drone] = action

    def actionSize(self, config):
        return self.DroneActions

    def getReward(self, simulation, drone):
        current_damage = simulation.total_damage
        damage = current_damage - self.reward_data["damage"]

        drone_state_consistence = self.getRewardDroneStateConsistence(drone)
        drone_charging = self.getRewardDroneCharging(drone)
        drone_protecting = self.getRewardDroneProtecting(drone)

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
