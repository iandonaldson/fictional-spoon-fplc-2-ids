"""
AKTA Data Extraction Script using PyCORN

Extracts chromatography data from AKTA UNICORN 6 zip files and saves to JSON format.

Usage:
    python extract_akta.py <input_zip_file> [output_dir]
    python extract_akta.py --all [output_dir]
"""

import sys
sys.path.insert(0, '/tmp/PyCORN')

import json
import os
from pathlib import Path
from datetime import datetime
from pycorn import PcUni6


def extract_akta_file(zip_path, output_dir=None):
    """
    Extract data from a single AKTA zip file using PyCORN
    
    Parameters:
    -----------
    zip_path : str
        Path to AKTA .zip file
    output_dir : str, optional
        Output directory for JSON file. Defaults to .tmp/akta_extracted/
        
    Returns:
    --------
    dict : Extracted data structure
    """
    
    print(f"\n{'='*70}")
    print(f"Extracting: {os.path.basename(zip_path)}")
    print(f"{'='*70}")
    
    # Set default output directory
    if output_dir is None:
        output_dir = ".tmp/akta_extracted"
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Load data with PyCORN
    print("Loading file...")
    data = PcUni6(zip_path)
    data.load(print_log=False)
    
    # Get date before cleaning up (Result.xml will be removed)
    file_date = None
    try:
        file_date = data.date
    except (KeyError, AttributeError):
        pass
    
    data.load_all_xml()
    
    # Extract metadata
    print("Extracting metadata...")
    result = {
        "metadata": {
            "source_file": os.path.basename(zip_path),
            "extraction_date": datetime.now().isoformat(),
            "pycorn_version": "0.20",
            "file_date": file_date,
        },
        "chromatograms": {}
    }
    
    # Get chromatogram keys
    chrom_keys = [k for k in data.keys() 
                  if k.startswith('Chrom.') 
                  and not k.endswith('.Xml') 
                  and not k.endswith('_dict')]
    
    print(f"Found {len(chrom_keys)} chromatogram(s)")
    
    # Extract each chromatogram
    for chrom_key in chrom_keys:
        print(f"\nProcessing: {chrom_key}")
        chrom_data = data[chrom_key]
        
        chrom_result = {
            "curves": {},
            "events": {}
        }
        
        # Classify data types
        curve_count = 0
        event_count = 0
        
        for key, value in chrom_data.items():
            if isinstance(value, dict):
                data_type = value.get('data_type', 'unknown')
                data_name = value.get('data_name', key)
                
                # Store based on type
                if data_type in ['UV', 'Conduction', 'Pressure', 'Temperature', 'pH', 'Other']:
                    # Sensor/curve data
                    curve_info = {
                        "data_type": data_type,
                        "data_name": data_name,
                        "unit": value.get('unit', ''),
                        "run_name": value.get('run_name', ''),
                        "data_points": len(value.get('data', [])),
                    }
                    
                    # Save first/last few points as sample
                    if 'data' in value and len(value['data']) > 0:
                        curve_info['data_sample_first'] = value['data'][:3]
                        curve_info['data_sample_last'] = value['data'][-3:]
                        curve_info['data'] = value['data']  # Full data
                    
                    chrom_result['curves'][key] = curve_info
                    curve_count += 1
                    print(f"  ✓ Curve: {data_name} ({data_type}, {curve_info['data_points']} points)")
                    
                elif data_type == 'annotation':
                    # Event data (fractions, injections, logbook)
                    event_info = {
                        "data_type": data_type,
                        "data_name": data_name,
                        "event_count": len(value.get('data', [])),
                    }
                    
                    # Save sample events
                    if 'data' in value and len(value['data']) > 0:
                        event_info['data_sample'] = value['data'][:5]
                        event_info['data'] = value['data']  # Full data
                    
                    chrom_result['events'][key] = event_info
                    event_count += 1
                    print(f"  ✓ Event: {data_name} ({event_info['event_count']} events)")
        
        result['chromatograms'][chrom_key] = chrom_result
        print(f"\n  Summary: {curve_count} curves, {event_count} event types")
    
    # Save to JSON
    base_name = Path(zip_path).stem
    output_file = os.path.join(output_dir, f"{base_name}_extracted.json")
    
    print(f"\nSaving to: {output_file}")
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    # Also save a summary without full data
    summary = {
        "metadata": result["metadata"],
        "chromatograms": {}
    }
    
    for chrom_key, chrom_data in result['chromatograms'].items():
        summary['chromatograms'][chrom_key] = {
            "curves": {k: {key: val for key, val in v.items() if key != 'data'} 
                      for k, v in chrom_data['curves'].items()},
            "events": {k: {key: val for key, val in v.items() if key != 'data'} 
                      for k, v in chrom_data['events'].items()}
        }
    
    summary_file = os.path.join(output_dir, f"{base_name}_summary.json")
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"✓ Extraction complete!")
    print(f"  - Full data: {output_file}")
    print(f"  - Summary:   {summary_file}")
    
    return result


def extract_all_akta_files(data_dir="data/akta", output_dir=None):
    """
    Extract all AKTA zip files from a directory
    
    Parameters:
    -----------
    data_dir : str
        Directory containing AKTA .zip files
    output_dir : str, optional
        Output directory for JSON files
    """
    
    # Convert to absolute path if relative
    data_dir = os.path.abspath(data_dir)
    
    # Find all zip files
    zip_files = list(Path(data_dir).glob("*.zip"))
    
    if not zip_files:
        print(f"No .zip files found in {data_dir}")
        return
    
    print(f"\nFound {len(zip_files)} AKTA file(s) to extract")
    print(f"Output directory: {output_dir or '.tmp/akta_extracted'}")
    
    results = []
    for zip_file in sorted(zip_files):
        try:
            result = extract_akta_file(str(zip_file), output_dir)
            results.append(result)
        except Exception as e:
            print(f"\n✗ ERROR processing {zip_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*70}")
    print(f"EXTRACTION COMPLETE: {len(results)}/{len(zip_files)} files successful")
    print(f"{'='*70}")
    
    return results


def main():
    """Main entry point"""
    
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExamples:")
        print("  python extract_akta.py data/akta/sample.zip")
        print("  python extract_akta.py --all")
        print("  python extract_akta.py --all .tmp/output")
        sys.exit(1)
    
    if sys.argv[1] == '--all':
        # Default to project data directory
        data_dir = "/workspaces/fictional-spoon-fplc-2-ids/data/akta"
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        extract_all_akta_files(data_dir=data_dir, output_dir=output_dir)
    else:
        zip_file = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        extract_akta_file(zip_file, output_dir)


if __name__ == "__main__":
    main()
