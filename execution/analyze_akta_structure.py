"""
AKTA Data Structure Analysis Script

Analyzes extracted AKTA data to understand the structure and design the IDS schema.

Usage:
    python analyze_akta_structure.py <extracted_json_dir>
"""

import sys
import json
import os
from pathlib import Path
from collections import defaultdict, Counter


def analyze_data_structure(json_dir=".tmp/akta_extracted"):
    """
    Analyze extracted AKTA data files to understand structure
    
    Parameters:
    -----------
    json_dir : str
        Directory containing extracted JSON files
    """
    
    print(f"\n{'='*70}")
    print(f"AKTA Data Structure Analysis")
    print(f"{'='*70}")
    
    # Find all summary JSON files
    summary_files = list(Path(json_dir).glob("*_summary.json"))
    
    if not summary_files:
        print(f"\nNo summary files found in {json_dir}")
        print("Run extract_akta.py first to extract data.")
        return
    
    print(f"\nAnalyzing {len(summary_files)} file(s)...")
    
    # Collect statistics
    all_curve_types = Counter()
    all_event_types = Counter()
    curve_details = defaultdict(list)
    event_details = defaultdict(list)
    file_dates = []
    
    # Analyze each file
    for summary_file in sorted(summary_files):
        print(f"\n  Processing: {summary_file.name}")
        
        with open(summary_file, 'r') as f:
            data = json.load(f)
        
        # Collect metadata
        if data['metadata'].get('file_date'):
            file_dates.append(data['metadata']['file_date'])
        
        # Analyze chromatograms
        for chrom_key, chrom_data in data['chromatograms'].items():
            
            # Analyze curves
            for curve_key, curve_info in chrom_data['curves'].items():
                curve_type = curve_info['data_type']
                curve_name = curve_info['data_name']
                all_curve_types[curve_type] += 1
                
                curve_details[curve_type].append({
                    'name': curve_name,
                    'unit': curve_info.get('unit', ''),
                    'points': curve_info.get('data_points', 0),
                    'file': summary_file.stem
                })
            
            # Analyze events
            for event_key, event_info in chrom_data['events'].items():
                event_name = event_info['data_name']
                all_event_types[event_name] += 1
                
                event_details[event_name].append({
                    'count': event_info.get('event_count', 0),
                    'file': summary_file.stem
                })
    
    # Print analysis
    print(f"\n{'='*70}")
    print(f"ANALYSIS RESULTS")
    print(f"{'='*70}")
    
    print(f"\n1. CURVE/SENSOR DATA TYPES")
    print(f"   {'-'*66}")
    for curve_type, count in all_curve_types.most_common():
        print(f"   {curve_type:20s} : {count} occurrences")
        
        # Show examples
        examples = curve_details[curve_type][:3]
        for ex in examples:
            unit = ex['unit'] or ''
            print(f"      - {ex['name']:25s} ({unit:10s}) {ex['points']:6d} points")
    
    print(f"\n2. EVENT DATA TYPES")
    print(f"   {'-'*66}")
    for event_name, count in all_event_types.most_common():
        print(f"   {event_name:30s} : {count} occurrences")
        
        # Show examples
        examples = event_details[event_name][:3]
        for ex in examples:
            print(f"      - {ex['count']} events in {ex['file']}")
    
    print(f"\n3. DATA POINT STATISTICS")
    print(f"   {'-'*66}")
    
    # Calculate statistics per curve type
    for curve_type in sorted(all_curve_types.keys()):
        points_list = [d['points'] for d in curve_details[curve_type]]
        if points_list:
            min_points = min(points_list)
            max_points = max(points_list)
            avg_points = sum(points_list) / len(points_list)
            print(f"   {curve_type:20s} : {min_points:6d} - {max_points:6d} points (avg: {avg_points:7.0f})")
    
    # Generate IDS schema recommendations
    print(f"\n{'='*70}")
    print(f"IDS SCHEMA RECOMMENDATIONS")
    print(f"{'='*70}")
    
    print(f"""
Based on the analysis, the IDS (Intermediary Data Schema) should include:

1. METADATA SECTION:
   - source_format: "AKTA-UNICORN-6"
   - file_name: original filename
   - extraction_date: ISO timestamp
   - run_date: chromatography run date
   - instrument_type: "AKTA"
   - software_version: "UNICORN 6+"

2. RUN PARAMETERS:
   - run_name: from PyCORN
   - column_volume: if available
   - method: method information

3. SENSOR DATA (time-series curves):
   Structure: List of curve objects, each with:
   - curve_id: unique identifier
   - curve_type: {', '.join(f'"{t}"' for t in sorted(all_curve_types.keys()))}
   - curve_name: descriptive name
   - unit: measurement unit
   - data: array of [volume/time, value] pairs

4. EVENTS (discrete annotations):
   Structure: List of event objects, each with:
   - event_type: {', '.join(f'"{t}"' for t in sorted(all_event_types.keys()))}
   - event_time/volume: position
   - event_text: description

5. PEAKS (if detected):
   - peak_id, retention_time/volume, height, area, etc.

Next step: Create JSON schema definition (ids_schema.json)
""")
    
    # Save analysis report
    report_file = os.path.join(json_dir, "analysis_report.json")
    report = {
        "analysis_date": str(Path(summary_files[0]).stat().st_mtime),
        "files_analyzed": len(summary_files),
        "curve_types": dict(all_curve_types),
        "event_types": dict(all_event_types),
        "curve_details": {k: v for k, v in curve_details.items()},
        "event_details": {k: v for k, v in event_details.items()},
    }
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n✓ Analysis report saved to: {report_file}")
    

def main():
    """Main entry point"""
    
    json_dir = sys.argv[1] if len(sys.argv) > 1 else ".tmp/akta_extracted"
    analyze_data_structure(json_dir)


if __name__ == "__main__":
    main()
