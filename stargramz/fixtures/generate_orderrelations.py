import json
from collections import OrderedDict
from pprint import pprint

with open('stargramz/fixtures/occasions.json') as f:
    occasions = json.load(f)

with open('stargramz/fixtures/relations.json') as f:
    relations = json.load(f)

relations_dict = {}


for r in relations:
    relations_dict[r['fields']['title']] = r


ordered_relations = [
    'Friend',
    'Mother',
    'Father',
    'Daughter',
    'Son',
    'Sister',
    'Brother',
    'Wife',
    'Husband',
    'Grandmother',
    'Grandfather',
    'Girlfriend',
    'Boyfriend',
    'Aunt',
    'Uncle',
    'Niece',
    'Nephew',
    'Cousin',
    'Coworker',
]

output = []
pk = 1

for occ in occasions:
    order = 1
    for rel in ordered_relations:
        item = OrderedDict([
            ("model", "stargramz.orderrelationship"),
            ("pk", pk),
            ("fields",
                OrderedDict([
                    ("order", order),
                    ("occasion_id", occ['pk']),
                    ("relation_id", relations_dict[rel]['pk'])
                ])
            )
        ])
        output.append(item)
        order += 1
        pk += 1

with open('stargramz/fixtures/orderrelations.json', 'w') as f:
    f.write(json.dumps(output, indent=2))

