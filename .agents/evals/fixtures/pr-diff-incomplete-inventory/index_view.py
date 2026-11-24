def labels_for(catalog, indexed):
    return {item: indexed[item] for item in catalog if item in indexed}
