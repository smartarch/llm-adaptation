def simulation_class(example):
    if example == "farm":
        from farm.simulation import SmartFarmSimulation as Simulation
    elif example == "dragon":
        from dragon.simulation import DragonHuntSimulation as Simulation
    else:
        raise ValueError(f"Unknown example: {example}")
    return Simulation


def simulation_configs(example):
    if example == "farm":
        configs = ["farm/configs/default.yaml", "generated_adaptations/configs/generated.yaml", "farm/configs/config_no_battery.yaml"]
    elif example == "dragon":
        configs = ["dragon/configs/default.yaml", "generated_adaptations/configs/generated.yaml"]
    else:
        raise ValueError(f"Unknown example: {example}")
    return configs


def adaptation_config(adaptation_name, example):
    if example == "farm":
        class_name = "SmartFarmAdaptation"
    elif example == "dragon":
        class_name = "SmartAdaptation"
    else:
        raise ValueError(f"Unknown example: {example}")

    return {
        "name": adaptation_name,
        "log_dir.append": f"/{adaptation_name}",
        "adaptation_name": f"generated_adaptations.{example}.{adaptation_name.replace('/', '.')}.{class_name}",
    }
