import math


class SmartFarmAdaptation(FarmAdaptation):

    def assign_drones(self, components, environment, group_id, step):
        # Get all fields that have a threat
        fields_with_threat = []
        for f in environment.fields:
            if f.threat_level > 0 and f.drones_for_full_protection > 0:
                fields_with_threat.append(f)

        # Sort by threat descending
        fields_with_threat.sort(key=lambda f: f.threat_level, reverse=True)

        if not fields_with_threat:
            for d in components:
                d.group = group_id
            return

        # Track which drones are still available
        available = list(range(len(components)))

        for f in fields_with_threat:
            if not available:
                break

            cx = (f.left + f.right) / 2.0
            cy = (f.top + f.bottom) / 2.0

            # Sort available drones by distance to this field
            available.sort(
                key=lambda di: (components[di].location.x - cx) ** 2
                              + (components[di].location.y - cy) ** 2
            )

            # Assign closest N drones
            count = min(f.drones_for_full_protection, len(available))
            for i in range(count):
                di = available[i]
                components[di].group = str(f)
            available = available[count:]

        # All remaining drones go to idle
        for di in available:
            components[di].group = group_id