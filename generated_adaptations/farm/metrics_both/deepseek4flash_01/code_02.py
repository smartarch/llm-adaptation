import math
from generated_adaptations.base_classes.farm import FarmAdaptation

class SmartFarmAdaptation(FarmAdaptation):
    def assign_drones(self, components, environment, group_ids, step: int):
        # Active fields with threat > 0, sorted by threat descending
        active_fields = [f for f in environment.fields if f.threat_level > 0]
        active_fields.sort(key=lambda f: f.threat_level, reverse=True)
        
        def dist_to_field(drone, field):
            cx = (field.left + field.right) / 2.0
            cy = (field.top + field.bottom) / 2.0
            return math.hypot(drone.location.x - cx, drone.location.y - cy)
        
        unassigned = list(components)
        assignment = {}  # drone -> group_id
        
        for i, field in enumerate(active_fields):
            if not unassigned:
                break
            required = field.drones_for_full_protection
            group_id = f"protecting {field.id}"
            if group_id not in group_ids:
                continue
            
            # Separate drones already assigned to this field
            existing = []
            others = []
            for d in unassigned:
                if d.state in ("moving_to_field", "protecting") and d.target_id == field.id:
                    existing.append(d)
                else:
                    others.append(d)
            
            if len(existing) >= required:
                # Already fully protected: keep the required closest existing drones
                existing.sort(key=lambda d: dist_to_field(d, field))
                selected = existing[:required]
            else:
                # Not fully protected: need to assign more
                remaining = len(unassigned)
                total_assign = required if remaining >= required else remaining
                
                if i == 0:
                    # Highest threat field: pick the closest total_assign drones from all unassigned
                    if remaining <= required:
                        selected = unassigned[:]
                    else:
                        unassigned.sort(key=lambda d: dist_to_field(d, field))
                        selected = unassigned[:total_assign]
                else:
                    # Other fields: prefer existing drones, then fill with closest others
                    existing.sort(key=lambda d: dist_to_field(d, field))
                    others.sort(key=lambda d: dist_to_field(d, field))
                    if len(existing) >= total_assign:
                        selected = existing[:total_assign]
                    else:
                        selected = existing + others[:total_assign - len(existing)]
            
            # Assign selected drones to this field
            for drone in selected:
                assignment[drone] = group_id
            # Remove selected from unassigned pool
            unassigned = [d for d in unassigned if d not in selected]
        
        # Remaining drones are idle
        for drone in unassigned:
            assignment[drone] = "idle"
        
        # Execute all assignments
        for drone in components:
            group = assignment.get(drone, "idle")
            environment.assign_group(drone, group)