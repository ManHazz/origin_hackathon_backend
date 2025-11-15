def normalize_scores(data, value_key="score"):
    if not data:
        return data

    values = [item[value_key] for item in data]

    minimum_value = min(values)
    maximum_value = max(values)

    if minimum_value == maximum_value:
        return [
            {**item, value_key: 100}
            for item in data
        ]

    normalized = []
    for item in data:
        normalized_value = int((item[value_key] - minimum_value) / (maximum_value - minimum_value) * 100)
        normalized.append({**item, value_key: normalized_value})
    
    return normalized
