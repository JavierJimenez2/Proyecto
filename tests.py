import json

json_file = './refs/100\\oric_100.json'

with open(json_file, 'r') as f:
    data = json.load(f)

print(data)
