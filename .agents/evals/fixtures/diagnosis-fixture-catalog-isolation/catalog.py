"""A strict product catalog and the local fixture factory feeding it."""
from copy import deepcopy


def fresh_fixture(source, run_id):
    return {
        'id': run_id,
        'comparison_group': source['comparison_group'],
        'actual_source_id': source['id'],
        'payload': deepcopy(source['payload']),
        'session': {'head': 'fresh-head'},
    }


def visible_catalog(selected, rows):
    related = [row for row in rows
               if row['comparison_group'] == selected['comparison_group']]
    for row in related:
        if set(row['session']) != {'head'}:
            raise ValueError('unsupported saved session field')
    return [row['id'] for row in related]
