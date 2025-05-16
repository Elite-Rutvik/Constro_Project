import os
import sys

# Add parent directory to system path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from flask import Flask, request, jsonify, send_from_directory
from demo_last_saved import Casting, Shape, optimize_panels, print_results
import io
import re
import json
import tempfile
import fitz  # PyMuPDF
import cv2
import numpy as np
from google import generativeai as genai

# Import PaddleOCR if available, otherwise provide an error message
try:
    from paddleocr import PaddleOCR
    PADDLE_OCR_AVAILABLE = True
except ImportError:
    PADDLE_OCR_AVAILABLE = False
    print("Warning: PaddleOCR is not installed. PDF processing will not work.")

STANDARD_PANEL_SIZES = [100, 200, 300, 400, 500, 600]
GEMINI_API_KEY = "AIzaSyAFCHmz7n8PVvM2fjd3KVd1FBv5kPCIyQk"  # Consider using environment variables for this

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

@app.route('/extract-pdf', methods=['POST'])
def extract_pdf():
    if not PADDLE_OCR_AVAILABLE:
        return jsonify({'error': 'PaddleOCR is not installed on the server'}), 500
    
    try:
        # Check if file exists in request
        if 'pdfFile' not in request.files:
            return jsonify({'error': 'No file part'}), 400
            
        pdf_file = request.files['pdfFile']
        if pdf_file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        # Create temporary file to store the uploaded PDF
        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        pdf_file.save(temp_pdf.name)
        temp_pdf.close()
        
        # Process the PDF
        MIN_AREA = 5000
        
        try:
            doc = fitz.open(temp_pdf.name)
            page = doc[0]  # Assuming we're processing only the first page
            
            # Extract drawings
            drawings = page.get_drawings()
            
            # Define color matching function
            def is_target_color(color, target=(1.0, 1.0, 0.49803900718688965), tol=0.05):
                """Check if color is within tolerance of target color"""
                if color is None:
                    return False
                return all(abs(c - t) < tol for c, t in zip(color, target))
            
            # Find target rectangles
            target_rectangles = []
            for drawing in drawings:
                stroke_color = drawing.get("color")
                if not is_target_color(stroke_color):
                    continue
                for item in drawing["items"]:
                    if item[0] == "re":
                        rect = item[1]
                        area = rect.width * rect.height
                        if area >= MIN_AREA:
                            target_rectangles.append(rect)
            
            # Process with more lenient color matching if needed
            if len(target_rectangles) == 0:
                for drawing in drawings:
                    stroke_color = drawing.get("color")
                    if stroke_color and any(c > 0.9 for c in stroke_color):  # Any bright color
                        for item in drawing["items"]:
                            if item[0] == "re":
                                rect = item[1]
                                area = rect.width * rect.height
                                if area >= MIN_AREA:
                                    target_rectangles.append(rect)
            
            # Last resort: get largest rectangles regardless of color
            if len(target_rectangles) == 0:
                all_rectangles = []
                for drawing in drawings:
                    for item in drawing["items"]:
                        if item[0] == "re":
                            rect = item[1]
                            area = rect.width * rect.height
                            if area >= MIN_AREA:
                                all_rectangles.append(rect)
                
                all_rectangles = sorted(all_rectangles, key=lambda r: r.width * r.height, reverse=True)
                target_rectangles = all_rectangles[:4] if len(all_rectangles) >= 4 else all_rectangles
            
            # Sort and limit number of rectangles
            target_rectangles = sorted(target_rectangles, key=lambda r: r.width * r.height, reverse=True)
            if len(target_rectangles) > 4:  # Limit to top 4 largest rectangles
                target_rectangles = target_rectangles[:4]
            
            # If no rectangles found at all
            if len(target_rectangles) == 0:
                doc.close()
                os.unlink(temp_pdf.name)
                return jsonify({'error': 'Could not identify casting areas in the PDF. Please check the PDF format or try manual input.'}), 400
            
            # Initialize OCR - handle environment variable to avoid OpenMP error
            os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
            try:
                # Use minimal configuration to avoid errors
                ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            except Exception as e:
                doc.close()
                os.unlink(temp_pdf.name)
                return jsonify({'error': f'OCR initialization failed: {str(e)}. Please try manual input.'}), 500
            
            # Process each rectangle - directly in memory without saving to files
            casting_data = ""
            dpi = 300
            
            for idx, rect in enumerate(target_rectangles):
                try:
                    # Extract image from PDF as pixmap
                    pix = page.get_pixmap(clip=rect, dpi=dpi)
                    
                    # Convert pixmap to numpy array for OCR processing
                    from io import BytesIO
                    from PIL import Image
                    
                    # Convert the pixmap to a PIL Image
                    imgbytes = BytesIO(pix.tobytes("png"))
                    img = Image.open(imgbytes)
                    
                    # Convert to numpy array (what PaddleOCR expects)
                    img_array = np.array(img)
                    
                    # Process image with OCR directly
                    results = ocr.ocr(img_array, cls=True)
                    
                    pillar_name = ""
                    casting_output = []
                    
                    if results and len(results) > 0:
                        for line in results:
                            for word_info in line:
                                _, (text, _) = word_info
                                
                                if any(key in text for key in ['SW', 'LSW', 'LIFT']):
                                    pillar_name = text.strip().replace('\n', '')
                                elif 'X' in text.upper() and pillar_name:
                                    dimension = text.strip().replace('\n', '')
                                    casting_output.append(f"{pillar_name} : {dimension}")
                                    pillar_name = ""
                        
                        if casting_output:
                            casting_data += f"Casting {idx + 1} :\n"
                            for line in casting_output:
                                casting_data += f"{line}\n"
                            casting_data += "\n"
                    
                except Exception as e:
                    # Continue to the next rectangle on error
                    continue
            
            # Close PDF and clean up temp file
            doc.close()
            os.unlink(temp_pdf.name)
            
            # If no casting data was extracted
            if not casting_data:
                return jsonify({'error': 'Could not extract casting data from the PDF. Please try manual input or a different PDF.'}), 400
            
            # Process with Gemini API
            genai.configure(api_key=GEMINI_API_KEY)
            
            # Create prompt for Gemini 
            prompt = f"""
            You are a highly accurate JSON generator.

            You will be given casting data in the following format:
            Casting N :
            SHAPE_NAME : WIDTHxHEIGHT

            Your task is to convert this to a JSON with this structure:

            {{
              "casting_1": {{
                "SW2": {{
                  "side_1": 4750,
                  "side_2": 250
                }}
              }},
              "casting_2": {{
                "SW3": {{
                  "side_1": 1200,
                  "side_2": 600
                }}
              }}
            }}

            Rules:
            - Use the shape name (e.g., SW2, LSW4) as keys.
            - Parse the sizes into integers: width → side_1, height → side_2.
            - Use JSON syntax only — no explanations, comments, or extra text.

            Now convert the following data into JSON:

            {casting_data}
            """
            
            # Generate content with Gemini
            try:
                model = genai.GenerativeModel('gemini-2.0-flash')
                response = model.generate_content(prompt)
                raw_response = response.text
                cleaned_response = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_response.strip())
                
                # Parse JSON response
                json_data = json.loads(cleaned_response)
                
                # Return the processed data without saving locally
                return jsonify(json_data)
                
            except Exception as e:
                print(f"Error with Gemini processing: {str(e)}")
                # Return dummy data as fallback
                return jsonify({'error': 'Gemini processing failed. Please try manual input.'}), 500
            
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
            os.unlink(temp_pdf.name)
            raise e

    except Exception as e:
        import traceback
        print(f"Unhandled error in extract-pdf: {str(e)}")
        print(traceback.format_exc())
        
        # Return dummy data as fallback
        return jsonify({'error': 'An unexpected error occurred. Please try again later.'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
