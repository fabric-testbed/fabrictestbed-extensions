import json 

dashboard_file = "test_dashboard.json"
with open(dashboard_file) as f:
    data = json.load(f)

panels = []
for p in data["panels"]:
    if p["type"] == "row":
        for sp in p["panels"]:
            print(f'{sp["title"]} {sp["id"]}')  
            panels.append( {"name":sp["title"], "id":sp["id"]})  
    else:
        print(f'{p["title"]} {p["id"]}')
        panels.append( {"name":p["title"], "id":p["id"]})

print(panels)
print(len(panels))