import argparse
import random
import yaml
import math


def generate_fields(num_fields, map_width, map_height, min_size=4, max_size=12, margin=2):
    # Only allow sizes that are 0 or 3 mod 4
    valid_sizes = [s for s in range(min_size, max_size + 1) if s % 8 == 0 or s % 8 == 7]
    fields = []
    attempts = 0
    while len(fields) < num_fields and attempts < num_fields * 10000:
        width = random.choice(valid_sizes)
        height = random.choice(valid_sizes)
        left = random.randint(margin, int(map_width - width - margin))
        top = random.randint(margin, int(map_height - height - margin))
        right = left + width
        bottom = top + height

        # Check for overlap
        overlap = False
        for f in fields:
            if not (right + margin < f[1] or left - margin > f[3] or
                    bottom + margin < f[0] or top - margin > f[2]):
                overlap = True
                break
        if not overlap:
            fields.append([top, left, bottom, right])
        attempts += 1
    if len(fields) < num_fields:
        raise RuntimeError("Could not place all fields without overlap. Try increasing map size or reducing field count.")
    return fields


def main(scale):
    base_birds = 80
    base_fields = 4
    map_width = int(50 * math.sqrt(scale))
    map_height = int(50 * math.sqrt(scale))

    # Estimate number of fields (keep similar density)
    num_fields = base_fields * scale
    min_field_size = 7
    max_field_size = 24
    print("Field size range:", min_field_size, max_field_size)

    fields = generate_fields(num_fields, map_width, map_height, min_field_size, max_field_size)

    # Compute total field area
    total_field_area = sum((f[2] - f[0]) * (f[3] - f[1]) for f in fields)
    drones = round(0.6 * total_field_area / 56)  # assuming drone can cover 8x7 area
    birds = base_birds * scale

    # Area ratio check
    area_ratio = drones / (total_field_area / 56)
    print(f"Total field area: {total_field_area}")
    print(f"Area/Map ratio (should be ~0.3): {total_field_area/(map_width * map_height):.2f}")
    print(f"Drones: {drones}")
    print(f"Drones/field ratio (should be ~0.6): {area_ratio:.2f}")

    config = {
        'drones': drones,
        'birds': birds,
        'fields': fields,
        'mapWidth': map_width,
        'mapHeight': map_height
    }

    print()
    print(yaml.dump(config, default_flow_style=None))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--scale', type=int, default=1, help='Scale factor for the simulation')
    args = parser.parse_args()

    main(args.scale)
    # main(323)
