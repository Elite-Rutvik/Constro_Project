import numpy as np
from typing import List, Dict, Tuple
import itertools
import json
import os
import time
from tqdm import tqdm  # For progress bars

# Constants
MIN_PANEL_SIZE = 100
MAX_PANEL_SIZE = 600
STANDARD_PANEL_SIZES = [100, 200, 300, 400, 500, 600]  # Standard panel sizes in increments of 100

# Cache for storing previously computed panel combinations
panel_combinations_cache = {}

class Shape:
    def __init__(self, name: str, sides: List[int]):
        self.name = name
        self.sides = sides  # lengths of each side
        self.panel_layout = [[] for _ in range(len(sides))]  # will store panel sizes for each side
    
    def get_total_length(self) -> int:
        return sum(self.sides)
    
    def __str__(self) -> str:
        return f"Shape: {self.name}, Sides: {self.sides}"

class Casting:
    def __init__(self, name: str):
        self.name = name
        self.shapes = []
    
    def add_shape(self, shape: Shape) -> None:
        self.shapes.append(shape)
    
    def get_total_length(self) -> int:
        return sum(shape.get_total_length() for shape in self.shapes)
    
    def __str__(self) -> str:
        return f"Casting: {self.name}, Shapes: {len(self.shapes)}"

def analyze_castings(castings: List[Casting]) -> Dict:
    """
    Analyze all castings to identify common dimensions and optimal panel sizes.
    Returns information about preferred panel sizes for optimization.
    """
    length_counts = {}
    common_divisors = {}
    
    print("Analyzing casting dimensions...")
    
    # Collect all side lengths from all castings
    all_lengths = []
    for casting in castings:
        for shape in casting.shapes:
            all_lengths.extend(shape.sides)
    
    # Count frequency of each length
    for length in all_lengths:
        length_counts[length] = length_counts.get(length, 0) + 1
    
    # Find common divisors that work across multiple lengths
    for panel_size in sorted(STANDARD_PANEL_SIZES, reverse=True):  # Start with largest panels
        divisible_count = 0
        total_panels = 0
        
        for length in all_lengths:
            # If length is divisible by panel_size or has a small remainder
            if length % panel_size == 0:
                divisible_count += 1
                total_panels += length // panel_size
            elif length % panel_size <= MIN_PANEL_SIZE and length >= panel_size:
                # Almost divisible (has small remainder)
                divisible_count += 0.5
                total_panels += length // panel_size
        
        efficiency = divisible_count / len(all_lengths) if all_lengths else 0
        common_divisors[panel_size] = {
            "efficiency": efficiency,
            "divisible_count": divisible_count,
            "total_panels": total_panels
        }
    
    # Identify the most efficient panel sizes (that work well across castings)
    panel_efficiency = sorted(
        [(size, data["efficiency"], data["total_panels"]) 
         for size, data in common_divisors.items()],
        key=lambda x: (-x[1], x[2])  # Sort by efficiency (desc), then by total panels (asc)
    )
    
    preferred_sizes = [size for size, efficiency, _ in panel_efficiency if efficiency > 0.3]
    
    # If we don't have enough preferred sizes, add the largest ones
    if len(preferred_sizes) < 2:
        for size in sorted(STANDARD_PANEL_SIZES, reverse=True):
            if size not in preferred_sizes:
                preferred_sizes.append(size)
            if len(preferred_sizes) >= 3:
                break
    
    # Print analysis results
    print("\nPanel size analysis:")
    for size, efficiency, total_panels in panel_efficiency:
        print(f"  {size}mm: {efficiency:.2f} efficiency ({total_panels} total panels needed)")
    
    return {
        "length_counts": length_counts,
        "preferred_sizes": preferred_sizes,
        "panel_efficiency": panel_efficiency
    }

def get_possible_panels(length: int) -> List[List[int]]:
    """
    Generate optimal panel combinations for a given length.
    Ensures all panels are within the valid size range (MIN_PANEL_SIZE to MAX_PANEL_SIZE).
    """
    # Check cache first
    if length in panel_combinations_cache:
        return panel_combinations_cache[length]
    
    valid_panels = []
    standard_sizes = sorted(STANDARD_PANEL_SIZES, reverse=True)  # Start with largest panels
    
    # If length is smaller than the minimum panel size, handle this edge case
    if length < MIN_PANEL_SIZE:
        # For very small lengths, we have to use the minimum size
        valid_panels.append([MIN_PANEL_SIZE])
        panel_combinations_cache[length] = valid_panels
        return valid_panels
    
    # APPROACH 1: Maximize use of maximum-sized standard panels (600mm)
    if length >= MAX_PANEL_SIZE:
        # Calculate how many maximum-sized panels we can use
        num_max_panels = length // MAX_PANEL_SIZE
        remaining = length - (num_max_panels * MAX_PANEL_SIZE)
        
        if remaining == 0:
            # Perfect fit with max-sized panels
            valid_panels.append([MAX_PANEL_SIZE] * num_max_panels)
        elif remaining >= MIN_PANEL_SIZE:
            # If remainder is at least the minimum size, add it as a panel
            valid_panels.append([MAX_PANEL_SIZE] * num_max_panels + [remaining])
        else:
            # Remainder is too small - adjust by using one fewer max panel
            # and adding standard panels that sum to (MAX_PANEL_SIZE + remaining)
            adjusted_length = MAX_PANEL_SIZE + remaining
            
            # Try standard panels to fill the adjusted length
            for r in range(1, 3):  # Try up to 2 standard panels
                for combo in itertools.combinations_with_replacement(standard_sizes, r):
                    if sum(combo) == adjusted_length and all(p >= MIN_PANEL_SIZE for p in combo):
                        valid_panels.append([MAX_PANEL_SIZE] * (num_max_panels - 1) + list(combo))
            
            # If no standard combination, try a custom panel if it's large enough
            if not any(p for p in valid_panels if sum(p) == length) and adjusted_length >= MIN_PANEL_SIZE:
                valid_panels.append([MAX_PANEL_SIZE] * (num_max_panels - 1) + [adjusted_length])
    
    # APPROACH 2: Use combinations of standard panels only
    for r in range(1, min(8, length // MIN_PANEL_SIZE + 1)):  # Dynamic limit based on length
        for combo in itertools.combinations_with_replacement(standard_sizes, r):
            if sum(combo) == length:
                valid_panels.append(list(combo))
    
    # APPROACH 3: Try with 1-3 standard panel sizes in varied quantities
    for size1 in standard_sizes:
        if size1 <= length:
            max_count1 = min(length // size1, 8)  # Limit to reasonable count
            
            for count1 in range(1, max_count1 + 1):
                remaining1 = length - (size1 * count1)
                
                if remaining1 == 0:
                    # Perfect fit with this panel size
                    valid_panels.append([size1] * count1)
                elif remaining1 >= MIN_PANEL_SIZE:
                    # Try adding a second panel size
                    for size2 in standard_sizes:
                        if size2 <= remaining1:
                            if remaining1 % size2 == 0:
                                # Perfect fit with two panel sizes
                                count2 = remaining1 // size2
                                valid_panels.append([size1] * count1 + [size2] * count2)
                            # If not a perfect fit, check if remainder is at least the minimum size
                            elif remaining1 > size2 and (remaining1 % size2) >= MIN_PANEL_SIZE:
                                count2 = remaining1 // size2
                                last_panel = remaining1 - (size2 * count2)
                                if last_panel >= MIN_PANEL_SIZE:
                                    valid_panels.append([size1] * count1 + [size2] * count2 + [last_panel])
    
    # APPROACH 4: For smaller lengths, try as a single panel
    if length <= MAX_PANEL_SIZE and length >= MIN_PANEL_SIZE:
        if length in STANDARD_PANEL_SIZES:
            valid_panels.append([length])  # Use standard size if exact match
        else:
            valid_panels.append([length])  # Use a custom panel within size limits
    
    # Filter out any invalid panel combinations (outside size limits)
    valid_panels = [
        combo for combo in valid_panels 
        if all(MIN_PANEL_SIZE <= p <= MAX_PANEL_SIZE for p in combo) and sum(combo) == length
    ]
    
    # Remove duplicates
    verified_panels = []
    seen = set()
    for combo in valid_panels:
        # Convert to tuple for hashing (use sorted to catch permutations)
        combo_tuple = tuple(sorted(combo))
        
        if combo_tuple not in seen:
            verified_panels.append(combo)
            seen.add(combo_tuple)
    
    # Sort by optimization criteria
    sorted_panels = sorted(
        verified_panels,
        key=lambda x: (
            # Primary criteria: prefer all standard panels (no custom)
            sum(0 if p in STANDARD_PANEL_SIZES else 1 for p in x),
            
            # Secondary criteria: fewer total panels
            len(x),
            
            # Tertiary criteria: prefer larger panels on average
            -sum(p for p in x) / len(x) if x else 0,
            
            # Quaternary criteria: prefer more of the largest standard panels
            -sum(1 for p in x if p == MAX_PANEL_SIZE)
        )
    )
    
    # If we still don't have any valid panels, create a fallback
    if not sorted_panels and length > 0:
        if length < MIN_PANEL_SIZE:
            # For very small lengths, we have to use the minimum size
            sorted_panels = [[MIN_PANEL_SIZE]]
        elif length <= MAX_PANEL_SIZE:
            # Single panel if within size limits
            sorted_panels = [[length]]
        else:
            # For long lengths, use max-sized panels plus one more
            max_count = length // MAX_PANEL_SIZE
            remaining = length % MAX_PANEL_SIZE
            
            if remaining >= MIN_PANEL_SIZE:
                # Remainder is valid as a panel
                sorted_panels = [[MAX_PANEL_SIZE] * max_count + [remaining]]
            else:
                # Use fewer max panels and redistribute
                adjusted = [MAX_PANEL_SIZE] * (max_count - 1)
                remaining_length = MAX_PANEL_SIZE + remaining
                
                # Try to split the remaining length into valid-sized panels
                for size in sorted(standard_sizes, reverse=True):
                    if remaining_length >= size + MIN_PANEL_SIZE:
                        final_remainder = remaining_length - size
                        if final_remainder >= MIN_PANEL_SIZE:
                            sorted_panels = [adjusted + [size, final_remainder]]
                            break
                
                # If no valid split found, use minimum panels
                if not sorted_panels:
                    # Last resort: use max_count-1 panels of MAX_PANEL_SIZE and adjust
                    if (max_count-1) * MAX_PANEL_SIZE >= length - MIN_PANEL_SIZE:
                        remaining = length - (max_count-1) * MAX_PANEL_SIZE
                        sorted_panels = [[MAX_PANEL_SIZE] * (max_count-1) + [remaining]]
                    else:
                        # Ultimate fallback: use all MIN_PANEL_SIZE panels
                        min_count = (length + MIN_PANEL_SIZE - 1) // MIN_PANEL_SIZE  # Ceiling division
                        sorted_panels = [[MIN_PANEL_SIZE] * min_count]
    
    # Cache the results
    panel_combinations_cache[length] = sorted_panels
    return sorted_panels

def optimize_panels(castings: List[Casting], primary_idx: int) -> Dict:
    """
    Optimize panel layout to ensure 100% reuse between castings.
    Uses a pre-planning approach to ensure all panels from primary casting
    can be reused in secondary castings.
    """
    print("\nOptimizing panel layouts...")
    start_time = time.time()
    primary = castings[primary_idx]
    other_castings = [c for i, c in enumerate(castings) if i != primary_idx]
    
    # First step: Generate a "reuse plan" - what panels will we need for all castings
    all_sides = []  # All side lengths across all castings
    
    # Collect all side lengths
    print("\nStep 1/4: Collecting all side lengths across castings...")
    for casting in castings:
        for shape in casting.shapes:
            all_sides.extend(shape.sides)
    
    # Create a frequency map of side lengths
    side_frequency = {}
    for length in all_sides:
        side_frequency[length] = side_frequency.get(length, 0) + 1
    
    # Second step: Create a "panel bank" - pool of panels that will work for all castings
    print("\nStep 2/4: Creating a panel plan that ensures 100% reuse...")
    
    # For each unique side length, generate panel combinations
    panel_options = {}
    for length in set(all_sides):
        panel_options[length] = get_possible_panels(length)
    
    # Third step: Select the best panel combination for each side length
    # to ensure we can achieve 100% reuse
    print("\nStep 3/4: Selecting optimal panel combinations...")
    
    # First, identify which panel sizes appear most frequently across all castings
    panel_bank = {}  # Will store our pool of panels
    
    # Choose panel layouts for each side length - start with most frequent sides
    selected_layouts = {}
    for length, freq in sorted(side_frequency.items(), key=lambda x: -x[1]):
        if length not in selected_layouts and length in panel_options:
            # Choose a layout that maximizes use of standard panels
            layouts = panel_options[length]
            if layouts:
                selected_layouts[length] = layouts[0]  # Best layout for this length
                
                # Update panel bank with this layout
                for panel in layouts[0]:
                    panel_bank[panel] = panel_bank.get(panel, 0) + freq
    
    # Fourth step: Apply the selected layouts to all castings
    print("\nStep 4/4: Applying panel layouts to all castings...")
    
    # Apply to primary casting
    panel_counts = {}  # Will track panel usage in primary casting
    
    for shape in primary.shapes:
        for side_idx, side_length in enumerate(shape.sides):
            if side_length in selected_layouts:
                shape.panel_layout[side_idx] = selected_layouts[side_length].copy()
                
                # Update panel counts for primary casting
                for panel in shape.panel_layout[side_idx]:
                    panel_counts[panel] = panel_counts.get(panel, 0) + 1
    
    # Apply the same layouts to secondary castings
    for casting in other_castings:
        for shape in casting.shapes:
            for side_idx, side_length in enumerate(shape.sides):
                if side_length in selected_layouts:
                    shape.panel_layout[side_idx] = selected_layouts[side_length].copy()
    
    elapsed_time = time.time() - start_time
    print(f"\nOptimization completed in {elapsed_time:.2f} seconds.")
    
    return panel_counts

def print_results(castings: List[Casting], primary_idx: int) -> None:
    """Print the optimized panel layouts for all castings with detailed reuse analysis."""
    print(f"\nResults (Primary Casting: {castings[primary_idx].name})\n")
    
    # Track panel usage by casting
    primary_panels = {}  # Panels used in primary casting
    secondary_panels = {} # Panels used in secondary castings
    all_panels = {}       # All panels across all castings
    custom_panels = {}    # Custom panel sizes
    standard_panels = {}  # Standard panel sizes
    
    # First, analyze primary casting panels
    primary_casting = castings[primary_idx]
    for shape in primary_casting.shapes:
        for side_idx, panels in enumerate(shape.panel_layout):
            for panel in panels:
                primary_panels[panel] = primary_panels.get(panel, 0) + 1
                all_panels[panel] = all_panels.get(panel, 0) + 1
                if panel in STANDARD_PANEL_SIZES:
                    standard_panels[panel] = standard_panels.get(panel, 0) + 1
                else:
                    custom_panels[panel] = custom_panels.get(panel, 0) + 1
    
    # Analyze secondary castings separately
    for i, casting in enumerate(castings):
        if i == primary_idx:
            continue  # Skip primary casting
            
        # Track panels for this secondary casting
        for shape in casting.shapes:
            for side_idx, panels in enumerate(shape.panel_layout):
                for panel in panels:
                    secondary_panels[panel] = secondary_panels.get(panel, 0) + 1
                    all_panels[panel] = all_panels.get(panel, 0) + 1
                    if panel in STANDARD_PANEL_SIZES:
                        standard_panels[panel] = standard_panels.get(panel, 0) + 1
                    else:
                        custom_panels[panel] = custom_panels.get(panel, 0) + 1
    
    # Print results for each casting
    for i, casting in enumerate(castings):
        print(f"{'*' * 20} {casting.name} {'*' * 20}")
        print("PRIMARY" if i == primary_idx else "SECONDARY")
        
        for shape in casting.shapes:
            print(f"\n  Shape: {shape.name}")
            
            for side_idx, side_length in enumerate(shape.sides):
                panels = shape.panel_layout[side_idx]
                print(f"    Side {side_idx+1} (Length: {side_length}): {panels}")
    
    # Print summary statistics
    print("\n" + "=" * 50)
    print("PANEL USAGE SUMMARY")
    print("=" * 50)
    print(f"Total panel types used: {len(all_panels)}")
    print(f"Standard panel types: {len(standard_panels)}")
    print(f"Custom panel types: {len(custom_panels)}")
    
    print("\nStandard panels:")
    for size, count in sorted(standard_panels.items()):
        print(f"  Size {size}mm: {count} panels")
    
    print("\nCustom panels:")
    for size, count in sorted(custom_panels.items()):
        print(f"  Size {size}mm: {count} panels")
    
    # Calculate and display new panels needed for secondary castings
    print("\n" + "=" * 50)
    print("SECONDARY CASTING PANEL REQUIREMENTS")
    print("=" * 50)
    
    # Determine which panels from secondary castings exceed what's available from primary
    new_panels_needed = {}
    for panel, count in secondary_panels.items():
        available = primary_panels.get(panel, 0)
        if count > available:
            new_panels_needed[panel] = count - available
    
    if new_panels_needed:
        print("New panels needed for secondary castings:")
        for size, count in sorted(new_panels_needed.items()):
            panel_type = "standard" if size in STANDARD_PANEL_SIZES else "custom"
            print(f"  Size {size}mm ({panel_type}): {count} new panels")
        
        # Calculate costs based on panel count
        standard_count = sum(count for size, count in new_panels_needed.items() if size in STANDARD_PANEL_SIZES)
        custom_count = sum(count for size, count in new_panels_needed.items() if size not in STANDARD_PANEL_SIZES)
        total_count = standard_count + custom_count
        
        print(f"\nTotal new panels needed: {total_count}")
        print(f"  Standard panels: {standard_count}")
        print(f"  Custom panels: {custom_count}")
    else:
        print("No additional panels needed - all secondary panels can be reused from primary casting!")
        
    # Calculate reuse efficiency
    total_secondary_panel_count = sum(secondary_panels.values())
    reused_panel_count = total_secondary_panel_count - sum(new_panels_needed.values())
    if total_secondary_panel_count > 0:
        reuse_percentage = (reused_panel_count / total_secondary_panel_count) * 100
        print(f"\nPanel reuse efficiency: {reuse_percentage:.1f}% ({reused_panel_count} of {total_secondary_panel_count} panels reused)")

def load_castings_from_json(json_file_path: str) -> List[Casting]:
    """Load casting data from a JSON file and create Casting objects."""
    try:
        print(f"Loading data from {json_file_path}...")
        with open(json_file_path, 'r') as f:
            data = json.load(f)
        
        castings = []
        for casting_name, shapes_data in data.items():
            print(f"  Processing casting: {casting_name}")
            casting = Casting(casting_name)
            
            for shape_name, sides_data in shapes_data.items():
                # Extract side lengths from the sides data
                sides = [length for _, length in sides_data.items()]
                shape = Shape(shape_name, sides)
                casting.add_shape(shape)
                print(f"    Added shape: {shape_name} with {len(sides)} sides")
            
            castings.append(casting)
        
        print(f"Successfully loaded {len(castings)} castings.")
        return castings
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return []

def main():
    print("Formwork Panel Optimization System")
    print("==================================")
    
    # Determine data input method
    print("\nSelect data input method:")
    print("1. Load from JSON file")
    print("2. Manual input")
    
    choice = input("Enter your choice (1/2): ")
    
    castings = []
    if choice == "1":
        # Default path or let user specify
        default_json = os.path.join(os.path.dirname(__file__), "castings_simple.json")
        if os.path.exists(default_json):
            json_path = default_json
        else:
            json_path = input("Enter path to JSON file: ")
        
        castings = load_castings_from_json(json_path)
        if not castings:
            print("Failed to load castings from JSON. Exiting.")
            return
        
        # Print loaded castings for verification
        print("\nLoaded castings:")
        for i, casting in enumerate(castings):
            print(f"{i+1}. {casting.name} with {len(casting.shapes)} shapes")
            for j, shape in enumerate(casting.shapes):
                print(f"   - Shape {j+1}: {shape.name} with {len(shape.sides)} sides")
                print(f"     Side lengths: {shape.sides}")
    
    else:
        # Original manual input code
        num_castings = int(input("\nEnter number of castings: "))
        
        # Input castings and shapes
        for c in range(num_castings):
            casting_name = input(f"\nEnter name for Casting {c+1}: ")
            casting = Casting(casting_name)
            
            num_shapes = int(input(f"Enter number of shapes for {casting_name}: "))
            
            for s in range(num_shapes):
                shape_name = input(f"  Enter name for Shape {s+1}: ")
                num_sides = int(input(f"  Enter number of sides for {shape_name}: "))
                
                sides = []
                for side in range(num_sides):
                    length = int(input(f"    Enter length for Side {side+1}: "))
                    sides.append(length)
                
                shape = Shape(shape_name, sides)
                casting.add_shape(shape)
            
            castings.append(casting)
    
    if not castings:
        print("No castings defined. Exiting.")
        return
    
    print("\nPanel Sizes Available: 100mm to 600mm in 100mm increments")
    print("Custom sizes will be used as needed to complete layouts")
    
    # Select primary casting
    print("\nSelect primary casting (to be built first):")
    for i, casting in enumerate(castings):
        print(f"{i+1}. {casting.name}")
    
    primary_idx = int(input("Enter number: ")) - 1
    
    # Run optimization
    print("\nStarting optimization process. This may take some time...")
    optimize_panels(castings, primary_idx)
    
    # Display results
    print_results(castings, primary_idx)

if __name__ == "__main__":
    main()

