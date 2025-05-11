import os
import sys

# Add parent directory to system path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from flask import Flask, request, jsonify, send_from_directory
from demo_last_saved import Casting, Shape, optimize_panels, print_results
import io

STANDARD_PANEL_SIZES = [100, 200, 300, 400, 500, 600]

app = Flask(__name__)

# Serve static files
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

@app.route('/optimize', methods=['POST'])
def optimize():
    try:
        data = request.json
        castings_data = data['castings']
        primary_casting_name = data['primaryCasting']

        # Convert JSON data to Casting objects
        castings = []
        for casting_data in castings_data:
            casting = Casting(casting_data['name'])
            for shape_data in casting_data['shapes']:
                shape = Shape(shape_data['name'], shape_data['sides'])
                casting.add_shape(shape)
            castings.append(casting)

        # Find primary casting index
        primary_idx = next(i for i, c in enumerate(castings) 
                         if c.name == primary_casting_name)

        # Run optimization
        optimize_panels(castings, primary_idx)

        # Create output JSON structure
        output = {
            "steps": [
                "Optimizing panel layouts...",
                "Step 1/4: Collecting all side lengths across castings",
                "Step 2/4: Creating a panel plan that ensures 100% reuse",
                "Step 3/4: Selecting optimal panel combinations",
                "Step 4/4: Applying panel layouts to all castings"
            ],
            "results": {
                "primary_casting": castings[primary_idx].name,
                "castings": []
            }
        }

        # Process all castings
        for i, casting in enumerate(castings):
            casting_data = {
                "name": casting.name,
                "type": "PRIMARY" if i == primary_idx else "SECONDARY",
                "shapes": []
            }

            for shape in casting.shapes:
                shape_data = {
                    "name": shape.name,
                    "sides": []
                }
                
                for side_idx, (length, panels) in enumerate(zip(shape.sides, shape.panel_layout)):
                    side_data = {
                        "number": side_idx + 1,
                        "length": length,
                        "panels": panels
                    }
                    shape_data["sides"].append(side_data)
                
                casting_data["shapes"].append(shape_data)
            
            output["results"]["castings"].append(casting_data)

        # Calculate panel statistics
        panel_stats = {
            "standard": {},
            "custom": {},
            "totals": {
                "total_types": 0,
                "standard_types": 0,
                "custom_types": 0
            }
        }

        # Track panel usage
        all_panels = {}
        primary_panels = {}
        secondary_panels = {}

        # Process primary casting panels
        for shape in castings[primary_idx].shapes:
            for panels in shape.panel_layout:
                for panel in panels:
                    primary_panels[panel] = primary_panels.get(panel, 0) + 1
                    all_panels[panel] = all_panels.get(panel, 0) + 1

        # Process secondary castings
        for i, casting in enumerate(castings):
            if i != primary_idx:
                for shape in casting.shapes:
                    for panels in shape.panel_layout:
                        for panel in panels:
                            secondary_panels[panel] = secondary_panels.get(panel, 0) + 1
                            all_panels[panel] = all_panels.get(panel, 0) + 1

        # Calculate panel statistics
        for size, count in all_panels.items():
            if size in STANDARD_PANEL_SIZES:
                panel_stats["standard"][str(size)] = count
            else:
                panel_stats["custom"][str(size)] = count

        panel_stats["totals"] = {
            "total_types": len(all_panels),
            "standard_types": len([p for p in all_panels if p in STANDARD_PANEL_SIZES]),
            "custom_types": len([p for p in all_panels if p not in STANDARD_PANEL_SIZES])
        }

        # Calculate reuse analysis
        reuse_analysis = {
            "new_panels": [],
            "totals": {
                "standard_new": 0,
                "custom_new": 0,
                "total_new": 0
            }
        }

        # Calculate new panels needed
        for panel, count in secondary_panels.items():
            available = primary_panels.get(panel, 0)
            if count > available:
                new_count = count - available
                panel_type = "standard" if panel in STANDARD_PANEL_SIZES else "custom"
                reuse_analysis["new_panels"].append({
                    "size": panel,
                    "type": panel_type,
                    "count": new_count
                })
                if panel_type == "standard":
                    reuse_analysis["totals"]["standard_new"] += new_count
                else:
                    reuse_analysis["totals"]["custom_new"] += new_count

        reuse_analysis["totals"]["total_new"] = (
            reuse_analysis["totals"]["standard_new"] + 
            reuse_analysis["totals"]["custom_new"]
        )

        # Calculate efficiency
        total_secondary = sum(secondary_panels.values())
        total_new = reuse_analysis["totals"]["total_new"]
        reused = total_secondary - total_new
        
        reuse_analysis["efficiency"] = {
            "percentage": round((reused / total_secondary * 100), 1) if total_secondary > 0 else 0,
            "reused_panels": reused,
            "total_panels": total_secondary
        }

        output["results"]["panel_stats"] = panel_stats
        output["results"]["reuse_analysis"] = reuse_analysis

        return jsonify(output)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
