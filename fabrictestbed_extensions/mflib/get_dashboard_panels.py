import json 
import argparse


parser = argparse.ArgumentParser(description="Get dictionary of panel titles & ids from grafana dashboard json. Prints dictionary. Optionally write dictionary to file.")
parser.add_argument('-i', '--input_file', required=True, help="Input Grafana dashboard JSON filename.")
parser.add_argument('-o', '--output_file', help="Output filename for parsed panel info JSON.")



def read_panel_dict(dashboard_filename):
    with open(dashboard_filename) as f:
        data = json.load(f)

    panels = []
    for p in data["panels"]:
        if p["type"] == "row":
            for sp in p["panels"]:
                #print(f'{sp["title"]} {sp["id"]}')  
                panels.append( {"name":sp["title"], "id":sp["id"]})  
        else:
            #print(f'{p["title"]} {p["id"]}')
            panels.append( {"name":p["title"], "id":p["id"]})
    
    print(f"Found {len(panels)} panels.")
    return panels 

def write_panel_file(panel_dict, panel_filename):
    with open(panel_filename, "w") as of:
        json.dump( panel_dict, of)

    
if __name__ == "__main__":
    args = parser.parse_args()
   
    panels = read_panel_dict(args.input_file)
    print(panels)
    if args.output_file:
        write_panel_file(panels, args.output_file)
