from index_view import labels_for


def missing_labels(catalog, indexed):
    labels = labels_for(catalog, indexed)
    return [item for item in catalog if not labels.get(item)]
