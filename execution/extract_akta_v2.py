"""
AKTA Data Extraction Script v2 - Enhanced with full metadata preservation

Extracts chromatography data from AKTA UNICORN 6 zip files with complete metadata capture.
Each sample is extracted into its own folder with all raw files preserved.

Usage:
    python extract_akta_v2.py <input_zip_file> [output_base_dir]
    python extract_akta_v2.py --all [output_base_dir]
"""

import sys
import json
import os
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from pycorn import pc_uni6
import xml.etree.ElementTree as ET


def extract_xml_from_metadata_file(metadata_zip_path):
    """
    Extract XML content from AKTA metadata ZIP files
    
    Parameters:
    -----------
    metadata_zip_path : str
        Path to metadata ZIP file (e.g., InstrumentConfigurationData)
    
    Returns:
    --------
    dict : Parsed XML content or None if not parseable
    """
    try:
        with zipfile.ZipFile(metadata_zip_path, 'r') as zf:
            # Look for 'Xml' file in the archive
            if 'Xml' in zf.namelist():
                xml_content = zf.read('Xml').decode('utf-8', errors='ignore')
                # Try to parse XML
                root = ET.fromstring(xml_content)
                return {
                    'xml_text': xml_content,
                    'root_tag': root.tag,
                    'parsed': True
                }
    except Exception as e:
        pass
    
    return None


def extract_akta_file_enhanced(zip_path, output_base_dir=None):
    """
    Extract data from a single AKTA zip file with full metadata preservation
    
    Each sample gets its own folder containing:
    - All raw files from the .zip
    - *_extracted.json with curve/event data
    - *_summary.json with metadata summary
    - *_metadata.json with parsed metadata from non-XML files
    
    Parameters:
    -----------
    zip_path : str
        Path to AKTA .zip file
    output_base_dir : str, optional
        Base output directory. Defaults to .tmp/akta_extracted_v2/
        
    Returns:
    --------
    dict : Extracted data structure
    """
    
    print(f"\n{'='*80}")
    print(f"Extracting: {os.path.basename(zip_path)}")
    print(f"{'='*80}")
    
    # Set default output directory
    if output_base_dir is None:
        output_base_dir = ".tmp/akta_extracted_v2"
    
    # Create sample-specific folder
    base_name = Path(zip_path).stem
    sample_dir = Path(output_base_dir) / base_name
    sample_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Sample directory: {sample_dir}")
    
    # Step 1: Extract all raw files from the zip
    print("\n[1/4] Extracting raw files...")
    raw_files_dir = sample_dir / "raw_files"
    raw_files_dir.mkdir(exist_ok=True)
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(raw_files_dir)
        file_list = zf.namelist()
        print(f"  ✓ Extracted {len(file_list)} files to raw_files/")
    
    # Step 2: Extract metadata from special files
    print("\n[2/4] Parsing metadata files...")
    metadata = {}
    
    metadata_files = [
        'InstrumentConfigurationData',
        'MethodData',
        'CalibrationSettingData',
        'ColumnIndividualData',
        'ColumnTypeData',
        'SystemData',
        'SystemSettingData',
        'StrategyData'
    ]
    
    for mf in metadata_files:
        mf_path = raw_files_dir / mf
        if mf_path.exists():
            xml_data = extract_xml_from_metadata_file(mf_path)
            if xml_data:
                metadata[mf] = xml_data
                print(f"  ✓ Parsed {mf}")
    
    # Step 3: Load data with PyCORN
    print("\n[3/4] Loading chromatogram data with PyCORN...")
    data = pc_uni6(zip_path)
    data.load()
    
    # Get date before cleaning up
    file_date = None
    try:
        file_date = data.date
    except (KeyError, AttributeError):
        pass
    
    data.xml_parse()
    
    # Extract chromatogram data
    result = {
        "metadata": {
            "source_file": os.path.basename(zip_path),
            "extraction_date": datetime.now().isoformat(),
            "pycorn_version": "0.20",
            "file_date": file_date,
            "raw_files_count": len(file_list),
            "metadata_files_parsed": list(metadata.keys())
        },
        "chromatograms": {}
    }
    
    # After xml_parse(), sensor and event data is at root level
    # Collect curve (sensor) data and event data
    curves = {}
    events = {}
    
    print(f"  Processing parsed data...")
    
    for key, value in data.items():
        if isinstance(value, dict) and 'data_type' in value:
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
                
                curves[key] = curve_info
                
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
                
                events[key] = event_info
    
    # Store in a single chromatogram entry
    result['chromatograms']['Chromatogram.1'] = {
        "curves": curves,
        "events": events
    }
    
    print(f"    Curves: {len(curves)}, Events: {len(events)} event types")
    
    # Step 4: Save JSON files
    print("\n[4/4] Saving JSON files...")
    
    # Save full extracted data
    extracted_file = sample_dir / f"{base_name}_extracted.json"
    with open(extracted_file, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"  ✓ {extracted_file.name}")
    
    # Save summary without full data arrays
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
    
    summary_file = sample_dir / f"{base_name}_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"  ✓ {summary_file.name}")
    
    # Save parsed metadata
    if metadata:
        metadata_file = sample_dir / f"{base_name}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"  ✓ {metadata_file.name}")
    
    print(f"\n{'='*80}")
    print(f"✓ Extraction complete for {base_name}")
    print(f"  Location: {sample_dir}")
    print(f"  Files: raw_files/ + {len(list(sample_dir.glob('*.json')))} JSON files")
    print(f"{'='*80}")
    
    return result


def extract_all_akta_files(data_dir="data/akta", output_base_dir=None):
    """
    Extract all AKTA zip files from a directory
    
    Parameters:
    -----------
    data_dir : str
        Directory containing AKTA .zip files
    output_base_dir : str, optional
        Base output directory for all samples
    """
    
    # Convert to absolute path
    data_dir = os.path.abspath(data_dir)
    
    # Find all zip files
    zip_files = list(Path(data_dir).glob("*.zip"))
    
    if not zip_files:
        print(f"No .zip files found in {data_dir}")
        return
    
    print(f"\n{'='*80}")
    print(f"AKTA Data Extraction v2 - Enhanced with full metadata preservation")
    print(f"{'='*80}")
    print(f"Found {len(zip_files)} AKTA file(s) to extract")
    print(f"Output base directory: {output_base_dir or '.tmp/akta_extracted_v2'}")
    print(f"{'='*80}")
    
    results = []
    for i, zip_file in enumerate(sorted(zip_files), 1):
        print(f"\n[{i}/{len(zip_files)}] Processing: {zip_file.name}")
        try:
            result = extract_akta_file_enhanced(str(zip_file), output_base_dir)
            results.append(result)
        except Exception as e:
            print(f"\n✗ ERROR processing {zip_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*80}")
    print(f"Success: {len(results)}/{len(zip_files)} files")
    print(f"Output location: {output_base_dir or '.tmp/akta_extracted_v2'}/")
    print(f"{'='*80}\n")
    
    return results


def main():
    """Main entry point"""
    
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExamples:")
        print("  python extract_akta_v2.py data/akta/sample.zip")
        print("  python extract_akta_v2.py --all")
        print("  python extract_akta_v2.py --all .tmp/custom_output")
        sys.exit(1)
    
    if sys.argv[1] == '--all':
        # Default to project data directory
        data_dir = "/workspaces/fictional-spoon-fplc-2-ids/data/akta"
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        extract_all_akta_files(data_dir=data_dir, output_base_dir=output_dir)
    else:
        zip_file = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None
        extract_akta_file_enhanced(zip_file, output_dir)


if __name__ == "__main__":
    main()
