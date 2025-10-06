def simulation_class(example):
    if example == "farm":
        from farm.simulation import SmartFarmSimulation as Simulation
    elif example == "dragon":
        from dragon.simulation import DragonHuntSimulation as Simulation
    else:
        raise ValueError(f"Unknown example: {example}")
    return Simulation


def simulation_configs(example, variant):
    if example == "farm":
        configs = ["farm/configs/default.yaml", "generated_adaptations/configs/generated.yaml", "farm/configs/config_no_battery.yaml", "DSL/drones.yaml"]
    elif example == "dragon":
        configs = ["dragon/configs/default.yaml", "generated_adaptations/configs/generated.yaml", "DSL/dragon.yaml"]
        if variant == "constraints":
            configs.append("DSL/dragon_constraints.yaml")
    else:
        raise ValueError(f"Unknown example: {example}")
    return configs


# TODO: can we load this from the DSL?
def adaptation_class_name(example):
    if example == "farm":
        return "SmartFarmAdaptation"
    elif example == "dragon":
        return "SmartAdaptation"
    else:
        raise ValueError(f"Unknown example: {example}")


# TODO: can we load this from the DSL?
def adaptation_class(example):
    if example == "farm":
        from generated_adaptations.base_classes.farm import FarmAdaptation
        return FarmAdaptation, "generated_adaptations.base_classes.farm.FarmAdaptation"
    elif example == "dragon":
        from generated_adaptations.base_classes.dragon import DragonHuntAdaptation
        return DragonHuntAdaptation, "generated_adaptations.base_classes.dragon.DragonHuntAdaptation"
    else:
        raise ValueError(f"Unknown example: {example}")


def adaptation_config(adaptation_name, example, variant):
    class_name = adaptation_class_name(example)
    return {
        "name": f"{variant}/{adaptation_name}",
        "log_dir.append": f"/{variant}/{adaptation_name}",
        "adaptation_name": f"generated_adaptations.{example}.{variant}.{adaptation_name.replace('/', '.')}.{class_name}",
    }


def reset_component_counters(example):
    def reset_component_counter(cls):
        cls._count = 0

    if example == "farm":
        from farm.components.drone import Drone
        from farm.components.field import Field
        components = [Drone, Field]
    elif example == "dragon":
        from dragon.components.villagers import Villager, Farmer, Warrior
        components = [Villager, Farmer, Warrior]
    else:
        raise ValueError(f"Unknown example: {example}")

    for component in components:
        reset_component_counter(component)
