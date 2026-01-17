"""
AKTA to IDS Converter v1.0

Converts extracted AKTA data (from extract_akta.py) to IDS v1.0.0 format.

Usage:
    python akta_to_ids_v1.py <extracted_json_file> [output_file] [--csv]
    python akta_to_ids_v1.py --all <extracted_dir> [output_dir] [--csv]
    
Options:
    --csv    Also export CSV versions of the curves and events data
"""

import sys
import json
import os
import csv
from pathlib import Path
from datetime import datetime


def convert_akta_to_ids(extracted_file, output_file=None, schema_path=None, export_csv=False):
    """
    Convert extracted AKTA data to IDS v1.0.0 format
    
    Parameters:
    -----------
    extracted_file : str
        Path to extracted JSON file from extract_akta.py
    output_file : str, optional
        Output path for IDS file. Defaults to <input>.ids.json
    schema_path : str, optional
        Path to IDS schema for validation
    export_csv : bool, optional
        If True, also export CSV versions of curves and events
    """
    
    print(f"\nConverting: {os.path.basename(extracted_file)}")
    
    # Load extracted data
    with open(extracted_file, 'r') as f:
        akta_data = json.load(f)
    
    # Determine output file
    if output_file is None:
        base = Path(extracted_file).stem.replace('_extracted', '')
        output_dir = Path('output')
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = str(output_dir / f"{base}.ids.json")
    
    # Build IDS structure
    ids_data = {
        "schema_version": "1.0.0",
        
        "metadata": {
            "source_format": "AKTA-UNICORN-6",
            "source_file": akta_data['metadata']['source_file'],
            "extraction_timestamp": akta_data['metadata']['extraction_date'],
            "extraction_tool": f"PyCORN-{akta_data['metadata'].get('pycorn_version', '0.20')}"
        },
        
        "run_info": {
            "run_timestamp": akta_data['metadata'].get('file_date'),
            "run_name": None,
            "run_id": None,
            "instrument": {
                "manufacturer": "GE Healthcare",
                "model": "AKTA",
                "software_version": "UNICORN 6+"
            },
            "method": {},
            "column": {},
            "sample": {},
            "operator": None,
            "notes": None
        },
        
        "data": {
            "curves": [],
            "events": [],
            "peaks": []
        }
    }
    
    # Process each chromatogram
    for chrom_key, chrom_data in akta_data['chromatograms'].items():
        
        # Extract run_name from first curve if available
        if ids_data['run_info']['run_name'] is None:
            for curve_data in chrom_data['curves'].values():
                if 'run_name' in curve_data:
                    ids_data['run_info']['run_name'] = curve_data['run_name']
                    break
        
        # Convert curves to IDS curves
        for curve_key, curve_info in chrom_data['curves'].items():
            # Map AKTA data type to IDS curve type
            curve_type = map_curve_type(curve_info['data_type'])
            
            # Create curve object
            curve = {
                "curve_id": curve_key.lower().replace(' ', '_'),
                "curve_type": curve_type,
                "curve_name": curve_info['data_name'],
                "unit": curve_info.get('unit') or '',  # Empty string if None
                "x_axis": {
                    "type": "volume",
                    "unit": "ml"
                },
                "data": curve_info['data']
            }
            
            # Add sampling rate if we can calculate it
            if len(curve_info['data']) > 1:
                intervals = []
                for i in range(1, min(100, len(curve_info['data']))):
                    interval = curve_info['data'][i][0] - curve_info['data'][i-1][0]
                    if interval > 0:
                        intervals.append(interval)
                
                if intervals:
                    avg_interval = sum(intervals) / len(intervals)
                    if avg_interval > 0:
                        curve['sampling_rate'] = 1.0 / avg_interval  # points per ml
            
            # Add metadata for UV curves (wavelength)
            if curve_type == 'UV':
                wavelength = extract_wavelength(curve_info['data_name'])
                if wavelength is not None:
                    curve['metadata'] = {"wavelength_nm": wavelength}
            
            ids_data['data']['curves'].append(curve)
        
        # Convert events
        event_counter = 0
        for event_key, event_info in chrom_data['events'].items():
            event_type = map_event_type(event_info['data_name'])
            
            # Process each event in the list
            for event_data in event_info.get('data', []):
                event_counter += 1
                position_vol, description = event_data
                
                event = {
                    "event_id": f"event_{event_counter:03d}",
                    "event_type": event_type,
                    "event_name": event_info['data_name'],
                    "position": {
                        "value": position_vol,
                        "unit": "ml"
                    },
                    "text": description if isinstance(description, str) else str(description)
                }
                
                ids_data['data']['events'].append(event)
    
    # Save IDS file
    print(f"  → Saving to: {output_file}")
    with open(output_file, 'w') as f:
        json.dump(ids_data, f, indent=2)
    
    # Validate against schema if available
    if schema_path is None:
        schema_path = "/workspaces/fictional-spoon-fplc-2-ids/directives/ids_schema_v1.json"
    
    if os.path.exists(schema_path):
        try:
            import jsonschema
            with open(schema_path, 'r') as f:
                schema = json.load(f)
            jsonschema.validate(instance=ids_data, schema=schema)
            print("  ✓ Validated against IDS schema v1.0.0")
        except ImportError:
            print("  ⚠ jsonschema not installed, skipping validation")
        except jsonschema.ValidationError as e:
            print(f"  ✗ Validation error: {e.message}")
            print(f"    Path: {' > '.join(str(p) for p in e.path)}")
    
    # Export CSV files if requested
    if export_csv:
        csv_output_dir = Path(output_file).parent
        base_name = Path(output_file).stem.replace('.ids', '')
        export_curves_to_csv(ids_data, csv_output_dir, base_name)
        export_events_to_csv(ids_data, csv_output_dir, base_name)
    
    return ids_data


def export_curves_to_csv(ids_data, output_dir, base_name):
    """
    Export all curves to CSV files
    
    Creates one CSV file per curve with columns: volume, value
    
    Parameters:
    -----------
    ids_data : dict
        IDS format data
    output_dir : Path
        Directory to save CSV files
    base_name : str
        Base name for CSV files
    """
    curves_exported = 0
    
    for curve in ids_data['data']['curves']:
        # Create filename from curve_id, sanitizing invalid characters
        safe_curve_id = curve['curve_id'].replace('/', '_').replace('\\', '_')
        csv_filename = f"{base_name}_{safe_curve_id}.csv"
        csv_path = output_dir / csv_filename
        
        # Write curve data to CSV
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header with metadata
            writer.writerow([f"# Curve: {curve['curve_name']}"])
            writer.writerow([f"# Type: {curve['curve_type']}"])
            writer.writerow([f"# Unit: {curve['unit']}"])
            if 'metadata' in curve:
                for key, value in curve['metadata'].items():
                    writer.writerow([f"# {key}: {value}"])
            writer.writerow([])  # Blank line
            
            # Column headers
            x_unit = curve['x_axis']['unit']
            writer.writerow([f"Volume ({x_unit})", f"Value ({curve['unit']})"])
            
            # Data points
            for x, y in curve['data']:
                writer.writerow([x, y])
        
        curves_exported += 1
    
    print(f"  → Exported {curves_exported} curves to CSV")


def export_events_to_csv(ids_data, output_dir, base_name):
    """
    Export all events to a single CSV file
    
    Parameters:
    -----------
    ids_data : dict
        IDS format data
    output_dir : Path
        Directory to save CSV file
    base_name : str
        Base name for CSV file
    """
    events = ids_data['data']['events']
    
    if not events:
        return
    
    csv_filename = f"{base_name}_events.csv"
    csv_path = output_dir / csv_filename
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(['Event ID', 'Event Type', 'Event Name', 'Position (ml)', 'Description'])
        
        # Data
        for event in events:
            writer.writerow([
                event['event_id'],
                event['event_type'],
                event['event_name'],
                event['position']['value'],
                event['text']
            ])
    
    print(f"  → Exported {len(events)} events to CSV")


def map_curve_type(akta_type):
    """Map AKTA data types to IDS curve types"""
    mapping = {
        'UV': 'UV',
        'Conduction': 'Conductivity',
        'Pressure': 'Pressure',
        'Temperature': 'Temperature',
        'pH': 'pH',
        'Other': 'Other'
    }
    return mapping.get(akta_type, 'Other')


def extract_wavelength(curve_name):
    """Extract wavelength from UV curve name (e.g., 'UV 1_280' → 280)"""
    try:
        # Try patterns like "UV 1_280" or "UV_280"
        parts = curve_name.split('_')
        for part in reversed(parts):
            try:
                wavelength = int(part)
                if 0 <= wavelength <= 1000:  # Reasonable UV wavelength range
                    return wavelength
            except ValueError:
                continue
    except Exception:
        pass
    return None


def map_event_type(event_name):
    """Map AKTA event names to IDS event types"""
    name_lower = event_name.lower()
    
    if 'injection' in name_lower or 'inject' in name_lower:
        return 'injection'
    elif 'fraction' in name_lower:
        if 'start' in name_lower:
            return 'fraction_start'
        elif 'end' in name_lower:
            return 'fraction_end'
        else:
            return 'other'
    elif 'log' in name_lower:
        return 'user_mark'  # logbook entries are user marks
    elif 'alarm' in name_lower or 'warning' in name_lower:
        return 'alarm'
    elif 'mark' in name_lower:
        return 'user_mark'
    elif 'phase' in name_lower or 'method' in name_lower:
        return 'method_step'
    else:
        return 'other'


def convert_all(extracted_dir, output_dir=None, export_csv=False):
    """Convert all extracted files in a directory"""
    
    extracted_dir = Path(extracted_dir)
    
    # Find all extracted JSON files (not summaries)
    extracted_files = list(extracted_dir.glob("*_extracted.json"))
    
    if not extracted_files:
        print(f"No extracted files found in {extracted_dir}")
        return
    
    print(f"\n{'='*80}")
    print(f"Converting {len(extracted_files)} file(s) to IDS v1.0.0 format")
    if export_csv:
        print(f"CSV export: enabled")
    print(f"{'='*80}")
    
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    for extracted_file in sorted(extracted_files):
        try:
            if output_dir:
                base = extracted_file.stem.replace('_extracted', '')
                output_file = str(output_dir / f"{base}.ids.json")
            else:
                output_file = None
            
            convert_akta_to_ids(str(extracted_file), output_file, export_csv=export_csv)
            success_count += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print(f"✓ Conversion complete: {success_count}/{len(extracted_files)} files successful")
    print(f"{'='*80}\n")


def main():
    """Main entry point"""
    
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExamples:")
        print("  python akta_to_ids_v1.py .tmp/akta_extracted/sample_extracted.json")
        print("  python akta_to_ids_v1.py .tmp/akta_extracted/sample_extracted.json --csv")
        print("  python akta_to_ids_v1.py --all .tmp/akta_extracted")
        print("  python akta_to_ids_v1.py --all .tmp/akta_extracted output --csv")
        sys.exit(1)
    
    # Check for --csv flag
    export_csv = '--csv' in sys.argv
    args = [arg for arg in sys.argv[1:] if arg != '--csv']
    
    if len(args) > 0 and args[0] == '--all':
        extracted_dir = args[1] if len(args) > 1 else ".tmp/akta_extracted"
        output_dir = args[2] if len(args) > 2 else "output"
        convert_all(extracted_dir, output_dir, export_csv=export_csv)
    else:
        if len(args) == 0:
            print("Error: No input file specified")
            sys.exit(1)
        extracted_file = args[0]
        output_file = args[1] if len(args) > 1 else None
        convert_akta_to_ids(extracted_file, output_file, export_csv=export_csv)


if __name__ == "__main__":
    main()
