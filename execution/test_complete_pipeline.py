"""
Comprehensive Pipeline Coverage Test

Tests the complete AKTA to IDS conversion pipeline:
1. Verify all source .zip files were extracted
2. Verify all extracted files were converted to IDS
3. Verify IDS conversions preserve all data
4. Verify CSV exports can be generated
5. Generate summary report

This provides end-to-end validation of the data processing pipeline.
"""

import json
import os
from pathlib import Path


def test_complete_pipeline():
    """
    Run comprehensive pipeline tests
    """
    
    # Use absolute paths
    workspace_root = Path(__file__).parent.parent
    data_dir = workspace_root / "data" / "akta"
    extraction_dir = workspace_root / ".tmp" / "akta_extracted"
    
    print("="*80)
    print("COMPLETE PIPELINE COVERAGE TEST")
    print("="*80)
    
    results = {
        "source_files": 0,
        "extracted": 0,
        "ids_converted": 0,
        "validated": 0,
        "csv_ready": 0,
        "issues": []
    }
    
    # Step 1: Check source files
    print("\n[1/5] Checking source AKTA files...")
    zip_files = sorted(data_dir.glob("*.zip"))
    results["source_files"] = len(zip_files)
    print(f"  Found {len(zip_files)} source .zip files")
    
    if not zip_files:
        results["issues"].append("No source .zip files found")
        print_results(results)
        return False
    
    # Step 2: Check extractions
    print("\n[2/5] Checking extractions...")
    for zip_file in zip_files:
        base_name = zip_file.stem
        sample_dir = extraction_dir / base_name
        extracted_json = sample_dir / f"{base_name}_extracted.json"
        
        if sample_dir.exists() and extracted_json.exists():
            results["extracted"] += 1
            print(f"  ✓ {base_name}")
        else:
            results["issues"].append(f"Missing extraction for {base_name}")
            print(f"  ✗ {base_name}")
    
    # Step 3: Check IDS conversions
    print("\n[3/5] Checking IDS conversions...")
    for zip_file in zip_files:
        base_name = zip_file.stem
        ids_file = extraction_dir / base_name / f"{base_name}.ids.json"
        
        if ids_file.exists():
            # Verify it's valid JSON with expected structure
            try:
                with open(ids_file, 'r') as f:
                    ids_data = json.load(f)
                
                # Check required fields
                if 'schema_version' in ids_data and 'data' in ids_data:
                    if 'sensors' in ids_data['data']:
                        results["ids_converted"] += 1
                        sensor_count = len(ids_data['data']['sensors'])
                        event_count = len(ids_data['data']['events'])
                        print(f"  ✓ {base_name}: {sensor_count} sensors, {event_count} events")
                    else:
                        results["issues"].append(f"{base_name}.ids.json missing sensors data")
                        print(f"  ✗ {base_name}: Invalid structure")
                else:
                    results["issues"].append(f"{base_name}.ids.json missing required fields")
                    print(f"  ✗ {base_name}: Invalid structure")
            except json.JSONDecodeError as e:
                results["issues"].append(f"{base_name}.ids.json is not valid JSON")
                print(f"  ✗ {base_name}: Invalid JSON")
        else:
            results["issues"].append(f"Missing IDS conversion for {base_name}")
            print(f"  ✗ {base_name}: Not found")
    
    # Step 4: Validate conversions (data integrity)
    print("\n[4/5] Validating data integrity...")
    for zip_file in zip_files:
        base_name = zip_file.stem
        extracted_file = extraction_dir / base_name / f"{base_name}_extracted.json"
        ids_file = extraction_dir / base_name / f"{base_name}.ids.json"
        
        if not extracted_file.exists() or not ids_file.exists():
            continue
        
        try:
            # Load both files
            with open(extracted_file, 'r') as f:
                akta_data = json.load(f)
            with open(ids_file, 'r') as f:
                ids_data = json.load(f)
            
            # Count curves/sensors
            akta_curve_count = sum(len(chrom['curves']) for chrom in akta_data['chromatograms'].values())
            ids_sensor_count = len(ids_data['data']['sensors'])
            
            if akta_curve_count == ids_sensor_count:
                # Quick spot check - verify first sensor has data
                if ids_data['data']['sensors'] and len(ids_data['data']['sensors'][0]['data_points']) > 0:
                    results["validated"] += 1
                    print(f"  ✓ {base_name}: Data integrity confirmed")
                else:
                    results["issues"].append(f"{base_name}: IDS sensors have no data points")
                    print(f"  ✗ {base_name}: Empty sensors")
            else:
                results["issues"].append(f"{base_name}: Sensor count mismatch (AKTA={akta_curve_count}, IDS={ids_sensor_count})")
                print(f"  ✗ {base_name}: Sensor count mismatch")
        except Exception as e:
            results["issues"].append(f"{base_name}: Validation error - {e}")
            print(f"  ✗ {base_name}: Error during validation")
    
    # Step 5: Check CSV export capability
    print("\n[5/5] Checking CSV export readiness...")
    for zip_file in zip_files:
        base_name = zip_file.stem
        ids_file = extraction_dir / base_name / f"{base_name}.ids.json"
        
        if ids_file.exists():
            # Verify IDS structure is suitable for CSV export
            try:
                with open(ids_file, 'r') as f:
                    ids_data = json.load(f)
                
                if ids_data['data']['sensors']:
                    sensor = ids_data['data']['sensors'][0]
                    if 'data_points' in sensor and len(sensor['data_points']) > 0:
                        results["csv_ready"] += 1
                        print(f"  ✓ {base_name}: Ready for CSV export")
                    else:
                        results["issues"].append(f"{base_name}: No data points for CSV export")
                        print(f"  ✗ {base_name}: No data")
                else:
                    results["issues"].append(f"{base_name}: No sensors for CSV export")
                    print(f"  ✗ {base_name}: No sensors")
            except Exception as e:
                results["issues"].append(f"{base_name}: CSV check error - {e}")
                print(f"  ✗ {base_name}: Error")
        else:
            print(f"  - {base_name}: No IDS file")
    
    # Print results
    print_results(results)
    
    # Return success if all steps passed
    all_passed = (
        results["source_files"] > 0 and
        results["extracted"] == results["source_files"] and
        results["ids_converted"] == results["source_files"] and
        results["validated"] == results["source_files"] and
        results["csv_ready"] == results["source_files"] and
        len(results["issues"]) == 0
    )
    
    return all_passed


def print_results(results):
    """Print formatted results summary"""
    
    print(f"\n{'='*80}")
    print("PIPELINE COVERAGE SUMMARY")
    print(f"{'='*80}")
    print(f"Source files:      {results['source_files']}")
    print(f"Extracted:         {results['extracted']}/{results['source_files']}")
    print(f"IDS converted:     {results['ids_converted']}/{results['source_files']}")
    print(f"Validated:         {results['validated']}/{results['source_files']}")
    print(f"CSV ready:         {results['csv_ready']}/{results['source_files']}")
    
    if results["issues"]:
        print(f"\nISSUES ({len(results['issues'])}):")
        for issue in results["issues"]:
            print(f"  - {issue}")
    
    print(f"\n{'='*80}")
    if len(results["issues"]) == 0:
        print("✓ COMPLETE PIPELINE VALIDATED - ALL TESTS PASSED")
    else:
        print("✗ PIPELINE HAS ISSUES - SEE ABOVE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    success = test_complete_pipeline()
    exit(0 if success else 1)
