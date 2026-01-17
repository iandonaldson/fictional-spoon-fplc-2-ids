"""
AKTA to IDS Converter

Converts extracted AKTA data (from extract_akta.py) to IDS (Intermediary Data Schema) format.

Usage:
    python akta_to_ids.py <extracted_json_file> [output_file]
    python akta_to_ids.py --all <extracted_dir> [output_dir]
    python akta_to_ids.py --csv <ids_file> [output_csv]
"""

import sys
import json
import os
import csv
from pathlib import Path
from datetime import datetime


def convert_akta_to_ids(extracted_file, output_file=None):
    """
    Convert extracted AKTA data to IDS format
    
    Parameters:
    -----------
    extracted_file : str
        Path to extracted JSON file from extract_akta.py
    output_file : str, optional
        Output path for IDS file. Defaults to <input>.ids.json
    """
    
    print(f"\nConverting: {os.path.basename(extracted_file)}")
    
    # Load extracted data
    with open(extracted_file, 'r') as f:
        akta_data = json.load(f)
    
    # Determine output file
    if output_file is None:
        base = Path(extracted_file).stem.replace('_extracted', '')
        output_file = str(Path(extracted_file).parent / f"{base}.ids.json")
    
    # Build IDS structure
    ids_data = {
        "schema_version": "1.0.0",
        
        "metadata": {
            "source_format": "AKTA-UNICORN-6",
            "file_name": akta_data['metadata']['source_file'],
            "extraction_timestamp": akta_data['metadata']['extraction_date'],
            "extraction_tool": f"PyCORN-{akta_data['metadata'].get('pycorn_version', '0.20')}"
        },
        
        "run_info": {
            "run_timestamp": akta_data['metadata'].get('file_date'),
            "run_name": None,  # Extract from chromatogram if available
            "run_id": None,
            "instrument": {
                "type": "AKTA",
                "serial_number": None,
                "software_version": "UNICORN 6+"
            },
            "column": {
                "name": None,
                "type": None,
                "volume_ml": None,
                "length_cm": None,
                "diameter_cm": None
            },
            "method": {
                "name": None,
                "description": None,
                "file_path": None
            },
            "sample": {
                "name": None,
                "volume_ml": None,
                "concentration": None
            }
        },
        
        "data": {
            "sensors": [],
            "events": [],
            "peaks": [],
            "fractions": []
        },
        
        "custom_data": {}
    }
    
    # Process each chromatogram
    for chrom_key, chrom_data in akta_data['chromatograms'].items():
        
        # Extract run_name from first curve if available
        if ids_data['run_info']['run_name'] is None:
            for curve_data in chrom_data['curves'].values():
                if 'run_name' in curve_data:
                    ids_data['run_info']['run_name'] = curve_data['run_name']
                    break
        
        # Convert curves to sensor_data
        for curve_key, curve_info in chrom_data['curves'].items():
            sensor = {
                "sensor_id": curve_key.lower().replace(' ', '_'),
                "sensor_type": map_sensor_type(curve_info['data_type']),
                "sensor_name": curve_info['data_name'],
                "unit": curve_info.get('unit', ''),
                "x_axis_type": "volume",
                "x_axis_unit": "ml",
                "data_points": curve_info['data']
            }
            
            # Add wavelength for UV sensors
            if sensor['sensor_type'] == 'UV' and '_' in curve_info['data_name']:
                try:
                    # Extract wavelength from names like "UV 1_280" or "UV_280"
                    parts = curve_info['data_name'].split('_')
                    wavelength = int(parts[-1])
                    if wavelength > 0:
                        sensor['wavelength_nm'] = wavelength
                except (ValueError, IndexError):
                    pass
            
            # Calculate sampling rate if data points are evenly spaced
            if len(curve_info['data']) > 1:
                intervals = []
                for i in range(1, min(100, len(curve_info['data']))):
                    interval = curve_info['data'][i][0] - curve_info['data'][i-1][0]
                    if interval > 0:
                        intervals.append(interval)
                
                if intervals:
                    avg_interval = sum(intervals) / len(intervals)
                    if avg_interval > 0:
                        # Convert from ml interval to Hz (assuming ml/min flow rate of 1)
                        # This is approximate - actual sampling rate depends on flow rate
                        sensor['sampling_rate_hz'] = None  # Leave as null for now
            
            ids_data['data']['sensors'].append(sensor)
        
        # Convert events
        event_counter = 0
        for event_key, event_info in chrom_data['events'].items():
            event_type = map_event_type(event_info['data_name'])
            
            # Process each event in the list
            for event_data in event_info.get('data', []):
                event_counter += 1
                position_vol, description = event_data
                
                event = {
                    "event_id": f"event_{event_counter}",
                    "event_type": event_type,
                    "event_name": event_info['data_name'],
                    "position": {
                        "volume_ml": position_vol,
                        "time_min": None,  # Would need flow rate to calculate
                        "timestamp": None
                    },
                    "description": description if isinstance(description, str) else str(description)
                }
                
                ids_data['data']['events'].append(event)
    
    # Save IDS file
    print(f"  → Saving to: {output_file}")
    with open(output_file, 'w') as f:
        json.dump(ids_data, f, indent=2)
    
    # Validate against schema if available
    schema_path = "/workspaces/fictional-spoon-fplc-2-ids/directives/ids_schema.json"
    if os.path.exists(schema_path):
        try:
            import jsonschema
            with open(schema_path, 'r') as f:
                schema = json.load(f)
            jsonschema.validate(instance=ids_data, schema=schema)
            print("  ✓ Validated against IDS schema")
        except ImportError:
            print("  ⚠ jsonschema not installed, skipping validation")
        except jsonschema.ValidationError as e:
            print(f"  ✗ Validation error: {e.message}")
    
    return ids_data


def map_sensor_type(akta_type):
    """Map AKTA data types to IDS sensor types"""
    mapping = {
        'UV': 'UV',
        'Conduction': 'Conductivity',
        'Pressure': 'Pressure',
        'Temperature': 'Temperature',
        'pH': 'pH',
        'Other': 'Other'
    }
    return mapping.get(akta_type, 'Other')


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
            return 'other'  # Generic fraction event
    elif 'log' in name_lower:
        return 'logbook'
    elif 'alarm' in name_lower or 'warning' in name_lower:
        return 'alarm'
    elif 'mark' in name_lower:
        return 'mark'
    else:
        return 'other'


def convert_all(extracted_dir, output_dir=None):
    """Convert all extracted files in a directory"""
    
    extracted_dir = Path(extracted_dir)
    
    # Find all extracted JSON files (not summaries)
    extracted_files = list(extracted_dir.glob("*_extracted.json"))
    
    if not extracted_files:
        print(f"No extracted files found in {extracted_dir}")
        return
    
    print(f"\nConverting {len(extracted_files)} file(s) to IDS format")
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    for extracted_file in sorted(extracted_files):
        try:
            if output_dir:
                base = extracted_file.stem.replace('_extracted', '')
                output_file = str(Path(output_dir) / f"{base}.ids.json")
            else:
                output_file = None
            
            convert_akta_to_ids(str(extracted_file), output_file)
        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n✓ Conversion complete")


def export_ids_to_csv(ids_file, output_csv=None):
    """
    Export IDS data to CSV format
    
    Creates a wide-format CSV with columns:
    - x_value (volume or time)
    - sensor_1_name, sensor_2_name, ... (one column per sensor)
    
    Parameters:
    -----------
    ids_file : str
        Path to IDS JSON file
    output_csv : str, optional
        Output CSV path. Defaults to <input>.csv
    """
    
    print(f"\nExporting to CSV: {os.path.basename(ids_file)}")
    
    # Load IDS data
    with open(ids_file, 'r') as f:
        ids_data = json.load(f)
    
    # Determine output file
    if output_csv is None:
        output_csv = str(Path(ids_file).with_suffix('.csv'))
    
    # Build unified x-axis (use first sensor's x values as reference)
    if not ids_data['data']['sensors']:
        print("  ⚠ No sensor data to export")
        return
    
    # Get x-axis from first sensor
    reference_sensor = ids_data['data']['sensors'][0]
    x_axis_type = reference_sensor['x_axis_type']
    x_axis_unit = reference_sensor['x_axis_unit']
    
    # Create index of all x-values across all sensors
    all_x_values = set()
    for sensor in ids_data['data']['sensors']:
        for x, y in sensor['data_points']:
            all_x_values.add(x)
    
    x_values_sorted = sorted(all_x_values)
    
    # Build CSV data structure
    csv_data = []
    for x_val in x_values_sorted:
        row = {f'x_{x_axis_type}_{x_axis_unit}': x_val}
        
        # Add each sensor's y-value at this x (or None if not present)
        for sensor in ids_data['data']['sensors']:
            sensor_name = sensor['sensor_name']
            unit = sensor['unit']
            col_name = f"{sensor_name}_{unit}"
            
            # Find y-value for this x
            y_val = None
            for x, y in sensor['data_points']:
                if abs(x - x_val) < 1e-9:  # Floating point comparison
                    y_val = y
                    break
            
            row[col_name] = y_val
        
        csv_data.append(row)
    
    # Write CSV
    if csv_data:
        fieldnames = list(csv_data[0].keys())
        with open(output_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
        
        print(f"  → {output_csv}")
        print(f"  ✓ {len(csv_data)} rows, {len(fieldnames)} columns")
    else:
        print("  ⚠ No data to write")


def main():
    """Main entry point"""
    
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExamples:")
        print("  python akta_to_ids.py .tmp/akta_extracted/sample_extracted.json")
        print("  python akta_to_ids.py --all .tmp/akta_extracted")
        print("  python akta_to_ids.py --all .tmp/akta_extracted .tmp/ids_output")
        print("  python akta_to_ids.py --csv sample.ids.json")
        print("  python akta_to_ids.py --csv sample.ids.json output.csv")
        sys.exit(1)
    
    if sys.argv[1] == '--all':
        extracted_dir = sys.argv[2] if len(sys.argv) > 2 else ".tmp/akta_extracted"
        output_dir = sys.argv[3] if len(sys.argv) > 3 else None
        convert_all(extracted_dir, output_dir)
    elif sys.argv[1] == '--csv':
        ids_file = sys.argv[2] if len(sys.argv) > 2 else None
        output_csv = sys.argv[3] if len(sys.argv) > 3 else None
        if not ids_file:
            print("Error: --csv requires an IDS file path")
            sys.exit(1)
        export_ids_to_csv(ids_file, output_csv)
    else:
        extracted_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        convert_akta_to_ids(extracted_file, output_file)


if __name__ == "__main__":
    main()
