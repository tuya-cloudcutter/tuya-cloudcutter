import json


def object_to_json(obj):
    return json.dumps(obj, separators=(',', ':'))
