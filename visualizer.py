from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from base_classes.components2d import Point2D
from components.bird import BirdState
from components.drone import DroneState

if TYPE_CHECKING:
    from simulation import SmartFarmSimulation

COLORS = {
    'field': [228, 255, 122],
    'field_damaged': [228, 122, 122],
    'charger': [204, 204, 0],
    'text': (0, 0, 0),
    'line': [255, 0, 0],
}
DRONE_COLORS = {
    DroneState.IDLE: [0, 0, 255],
    # DroneState.PROTECTING: [0, 180, 180],
    # DroneState.MOVING_TO_FIELD: [0, 130, 255],
    # 'slow': [83, 0, 179],
    # DroneState.WAITING_FOR_CHARGING: [0, 153, 70],
    # DroneState.MOVING_TO_CHARGER: [0, 153, 70],
    DroneState.CHARGING: [0, 153, 0],
    # DroneState.TERMINATED: [60, 60, 60],
}
BIRD_COLORS = {
    BirdState.IDLE: [255, 189, 212],
    BirdState.FLYING_RANDOMLY: [255, 189, 212],
    BirdState.MOVING_TO_FIELD: [252, 84, 0],
    BirdState.EATING: [153, 0, 0],
    BirdState.FLEEING_OUTSIDE: [199, 18, 166],
    BirdState.FLEEING_WITHIN_FIELD: [199, 18, 166],
}

SIZES = {
    'drone': 6,
    'drone_slow': 6,
    'bird': 4,
    'field': 10,
    'charger': 10,
}

LEGEND_SIZE = 260
LOWER_EXTRA = 50
TEXT_MARGIN = 20


class Visualizer:

    def __init__(self, simulation: "SmartFarmSimulation"):
        self.simulation = simulation

        self.cellSize = SIZES['field']
        self.width = simulation.mapWidth * self.cellSize + LEGEND_SIZE  # 150 for legends
        self.height = simulation.mapHeight * self.cellSize + LOWER_EXTRA

        try:
            self.font = ImageFont.truetype("consolas.ttf", 11)
        except OSError:
            self.font = ImageFont.load_default()

        self.images: list[Image] = []
        self.grid = {}

    def _drawRectangle(self, canvas: np.ndarray, point, component, color=None):
        if color is None:
            color = COLORS[component]
        startY = int(point.y * self.cellSize)
        endY = startY + SIZES[component]
        startX = int(point.x * self.cellSize)
        endX = startX + SIZES[component]
        canvas[startX:endX, startY:endY] = color
        return startX + (endX - startX) / 2, startY + (endY - startY) / 2

    def _drawCircle(self, drawObject, rectangelMap, fill=None, outline='blue'):
        x1 = rectangelMap[0] * self.cellSize
        y1 = rectangelMap[1] * self.cellSize
        x2 = rectangelMap[2] * self.cellSize
        y2 = rectangelMap[3] * self.cellSize

        drawObject.ellipse((x1, y1, x2, y2), fill=fill, outline=outline)

    def drawFields(self):
        self.background = np.zeros(
            (self.height,
             self.width, 3))  # 3 for RGB and H for unsigned short
        self.background.fill(255)

        for field in self.simulation.fields:
            filedPoints = [Point2D(x, y) for x in range(field.left, field.right + 1) for y in range(field.top, field.bottom + 1)]
            self.grid[field] = filedPoints
            for point in filedPoints:
                self._drawRectangle(self.background, point, 'field')
        # draw a line
        legendStartPoint = self.width - LEGEND_SIZE
        for i in range(self.height):
            self.background[i][legendStartPoint] = COLORS['line']

    def _getLegends(self):
        return "LEGEND"
        totalDamage = sum(field.damage for field in self.world.fields)
        totalCrop = sum(field.allCrops for field in self.world.fields)
        activeChargers = list(filter(lambda c: c.active, self.world.chargers))
        text = f"Step: {self.world.experiment.currentTimeStep + 1}"
        text = f"{text}\nalive drones: {len([drone for drone in self.world.drones if drone.state != DroneState.TERMINATED])} - Damage: {totalDamage}/{totalCrop}"
        text = f"{text}\nchargers: {len(activeChargers)} - total capacity: {sum(c.capacity for c in self.world.chargers)}"
        text = f"{text}\nbirds: {len(self.world.birds)}"
        text = f"{text}\nCharging Rate: {sum(len(charger.chargingDrones) for charger in activeChargers)} (drones at) {ENVIRONMENT.currentChargingRate:0.3f}"
        text = f"{text}\nMAX Charging Available: {ENVIRONMENT.totalAvailableChargingEnergy:0.3f}"
        text = f"{text}\nCharger Queues:"

        for charger in self.world.chargers:
            accepted = set(charger.acceptedDrones)
            waiting = set(charger.waitingDrones)
            potential = set(charger.potentialDrones)

            text = f"{text}\n-{charger.id}, C:{len(charger.chargingDrones)}, A:{len(accepted)}, W:{len(waiting - accepted)}, P:{len(potential - waiting - accepted)}"

            for drone in charger.chargingDrones:
                text = f"{text}\n--{drone.id}, b:{drone.battery:.2f} - C, t:{drone.timeToDoneCharging():.0f}"
            for drone in charger.acceptedDrones:
                text = f"{text}\n--{drone.id}, b:{drone.battery:.2f} - A, t:{drone.timeToDoneCharging():.0f}"
            for drone in waiting - accepted:
                text = f"{text}\n--{drone.id}, b:{drone.battery:.2f} - W, t:{drone.timeToDoneCharging():.0f}"
            for drone in potential - waiting - accepted:
                text = f"{text}\n--{drone.id}, b:{drone.battery:.2f} - P, t:{drone.timeToDoneCharging():.0f}"

        text = f"{text}\nDead Drones:"
        for drone in self.world.drones:
            if drone.state == DroneState.TERMINATED:
                text = f"{text}\n-{drone.id}"

        return text

    def _drawLegends(self, draw):

        legendStartPoint = self.width - LEGEND_SIZE
        text = self._getLegends()
        draw.text((legendStartPoint + TEXT_MARGIN, TEXT_MARGIN), text, COLORS['text'], font=self.font)
        return draw

    def _drawDamage(self, array):
        for field in self.simulation.fields:
            for crop in field.damagedThisStep:
                # damage = field.crops[crop.x - field.left, crop.y - field.top]
                # color = plt.colormaps["Wistia"](damage / 3)[:3]
                # color = tuple(int(c * 255) for c in color)
                self._drawRectangle(array, crop, 'field', color=COLORS['field_damaged'])
            field.damagedThisStep.clear()

    def drawComponents(self, iteration=0):

        self._drawDamage(self.background)

        array = np.array(self.background, copy=True)

        for bird in self.simulation.birds:
            birdColor = BIRD_COLORS[bird.state]
            self.grid[bird] = self._drawRectangle(array, bird.location, 'bird', birdColor)

        for drone in self.simulation.drones:
            droneColor = DRONE_COLORS[drone.state]
            # if drone.state == DroneState.PROTECTING and drone.speed < ENVIRONMENT.droneSpeed:
            #     droneColor = DRONE_COLORS['slow']
            self.grid[drone] = self._drawRectangle(array, drone.location, 'drone', droneColor)

        # for charger in self.simulation.chargers:
        #     self.grid[charger] = self.drawRectangle(array, charger.location, 'charger' if charger.active else 'charger_failed')

        image = Image.fromarray(array.astype(np.uint8), 'RGB')
        draw = ImageDraw.Draw(image)

        # for drone in self.simulation.drones:
        #     if drone.state == DroneState.TERMINATED:
        #         continue
        #
        #     self.drawCircle(draw, drone.protectRadius())
        #     draw.text((self.grid[drone]), f"\n{drone.id}\nbattery:{drone.battery:.2f}", COLORS['text'], font=self.font)
        #
        # for charger in self.world.chargers:
        #     draw.text((self.grid[charger]), f"{charger.id}", COLORS['text'], font=self.font)

        draw = self._drawLegends(draw)
        self.images.append(image)

    def createAnimation(self, filename):
        self.images[0].save(filename, save_all=True, append_images=self.images[1:])
