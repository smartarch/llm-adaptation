import math
from generated_adaptations.base_classes.farm import FarmAdaptation


class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Identify fields that currently need protection (threat > 0 and a valid group exists)
        active_fields = []
        for f in environment.fields:
            gid = f"protecting {f.id}"
            if f.threat_level > 0 and gid in group_ids:
                active_fields.append(f)

        # Highest threat first; tie-break by field id for deterministic ordering
        active_fields.sort(key=lambda f: (-f.threat_level, f.id))

        # Map field id -> group id
        gid_by_field_id = {f.id: f"protecting {f.id}" for f in environment.fields}

        # Squared Euclidean distance from a drone to the centre of a field
        def dist_sq(comp, field):
            cx, cy = comp.location.x, comp.location.y
            fx = (field.left + field.right) / 2.0
            fy = (field.top + field.bottom) / 2.0
            return (cx - fx) ** 2 + (cy - fy) ** 2

        assigned = set()
        assignment = {}
        active_ids = {f.id for f in active_fields}

        for idx, field in enumerate(active_fields):
            required = field.drones_for_full_protection
            if required <= 0:
                continue

            gid = gid_by_field_id[field.id]

            # Drones not yet assigned in this round
            candidates = [c for c in components if c not in assigned]
            if not candidates:
                break

            # Drones already targeting this field
            current = [c for c in candidates if c.target_id == field.id]
            others = [c for c in candidates if c.target_id != field.id]

            # Keep up to `required` current drones, preferring the closest ones
            current.sort(key=lambda c: dist_sq(c, field))
            selected = current[:required]

            need = required - len(selected)
            if need > 0:
                if idx == 0:
                    # Highest threat field: pick absolutely closest available drones
                    others.sort(key=lambda c: dist_sq(c, field))
                else:
                    # Lower threat fields: prefer idle drones, penalise reassignment
                    # from another active field to avoid unnecessary churn.
                    def cost(c):
                        d = dist_sq(c, field)
                        if c.target_id is None or c.target_id not in active_ids:
                            return d
                        else:
                            return d + 1e9

                    others.sort(key=cost)

                selected.extend(others[:need])

            # Assign selected drones to this field
            for c in selected:
                assignment[c] = gid
                assigned.add(c)

        # Any remaining drones are idle
        for c in components:
            if c not in assigned:
                assignment[c] = "idle"

        # Explicitly re-assign every drone (even if it stays in the same group)
        for c in components:
            environment.assign_group(c, assignment[c])