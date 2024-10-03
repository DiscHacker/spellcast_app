AVERAGE_SCORES = [32.7, 57.5, 74, 86]
AVERAGE_NET_GEM_PROFITS = [2.8, 1, -0.8, -2.6]

def get_gem_value(gem_count: int):
    value = 0
    for swap_count in range(1, 4):
        gem_threshold = swap_count * 3
        if gem_count >= gem_threshold:
            value += AVERAGE_SCORES[swap_count] - AVERAGE_SCORES[swap_count - 1]
        elif gem_count > gem_threshold - 3:
            value += ((AVERAGE_SCORES[swap_count] - AVERAGE_SCORES[swap_count - 1]) / 3) * (gem_count % 3)
    return round(value, 1)

GEM_VALUE_LOOKUP = [get_gem_value(i) for i in range(11)]

def gem_value(gem_count: float):
    gem_count = int(gem_count)  # Convert to integer
    if gem_count >= len(GEM_VALUE_LOOKUP):
        return GEM_VALUE_LOOKUP[-1]
    return GEM_VALUE_LOOKUP[gem_count]