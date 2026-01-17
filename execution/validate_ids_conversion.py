"""
Validate IDS Conversion - Compare IDS output with original extracted AKTA data

This script verifies that:
1. All curves from AKTA extraction are present in IDS
2. Data point counts match
3. First and last data points match (spot check)
4. All events are preserved
"""

import json
import sys
from pathlib import Path


def validate_ids_conversion(extracted_file, ids_file):
    """
    Validate that IDS file correctly represents extracted AKTA data
    
    Returns: (success: bool, issues: list)
    """
    
    issues = []
    
    # Load files
    with open(extracted_file, 'r') as f:
        akta = json.load(f)
    
    with open(ids_file, 'r') as f:
        ids = json.load(f)
    
    # Count AKTA curves and events
    akta_curve_count = 0
    akta_event_count = 0
    
    for chrom_key, chrom_data in akta['chromatograms'].items():
        akta_curve_count += len(chrom_data['curves'])
        for event_info in chrom_data['events'].values():
            akta_event_count += len(event_info.get('data', []))
    
    # Count IDS sensors and events
    ids_curve_count = len(ids['data']['sensors'])
    ids_event_count = len(ids['data']['events'])
    
    # Check counts
    if akta_curve_count != ids_curve_count:
        issues.append(f"Curve count mismatch: AKTA={akta_curve_count}, IDS={ids_curve_count}")
    
    if akta_event_count != ids_event_count:
        issues.append(f"Event count mismatch: AKTA={akta_event_count}, IDS={ids_event_count}")
    
    # Validate each curve
    for chrom_key, chrom_data in akta['chromatograms'].items():
        for curve_key, curve_info in chrom_data['curves'].items():
            # Find corresponding IDS sensor
            sensor_id = curve_key.lower().replace(' ', '_')
            ids_curve = None
            for c in ids['data']['sensors']:
                if c['sensor_id'] == sensor_id:
                    ids_curve = c
                    break
            
            if ids_curve is None:
                issues.append(f"Curve '{curve_key}' not found in IDS")
                continue
            
            # Check data point count
            akta_points = len(curve_info['data'])
            ids_points = len(ids_curve['data_points'])
            
            if akta_points != ids_points:
                issues.append(f"Curve '{curve_key}': point count mismatch AKTA={akta_points}, IDS={ids_points}")
                continue
            
            # Spot check first and last points
            if akta_points > 0:
                akta_first = curve_info['data'][0]
                ids_first = ids_curve['data_points'][0]
                
                if abs(akta_first[0] - ids_first[0]) > 1e-6 or abs(akta_first[1] - ids_first[1]) > 1e-6:
                    issues.append(f"Curve '{curve_key}': first point mismatch")
                
                akta_last = curve_info['data'][-1]
                ids_last = ids_curve['data_points'][-1]
                
                if abs(akta_last[0] - ids_last[0]) > 1e-6 or abs(akta_last[1] - ids_last[1]) > 1e-6:
                    issues.append(f"Curve '{curve_key}': last point mismatch")
    
    # Validate events
    event_idx = 0
    for chrom_key, chrom_data in akta['chromatograms'].items():
        for event_key, event_info in chrom_data['events'].items():
            for event_data in event_info.get('data', []):
                if event_idx >= len(ids['data']['events']):
                    issues.append(f"Event {event_idx} missing in IDS")
                    continue
                
                akta_pos = event_data[0]
                # IDS events have position dict with volume_ml or time_min
                ids_event = ids['data']['events'][event_idx]['position']
                ids_pos = ids_event.get('volume_ml') or ids_event.get('time_min', 0)
                
                if abs(akta_pos - ids_pos) > 1e-6:
                    issues.append(f"Event {event_idx}: position mismatch AKTA={akta_pos}, IDS={ids_pos}")
                
                event_idx += 1
    
    return (len(issues) == 0, issues)


def validate_all():
    """Validate all IDS files against their source extracted files"""
    
    # Use absolute paths
    workspace_root = Path(__file__).parent.parent
    base_dir = workspace_root / ".tmp" / "akta_extracted"
    
    # Find all IDS files in subdirectories
    ids_files = list(base_dir.glob("*/*.ids.json"))
    
    if not ids_files:
        print("No IDS files found in .tmp/akta_extracted/")
        return
    
    print(f"\n{'='*80}")
    print(f"Validating {len(ids_files)} IDS file(s) against source data")
    print(f"{'='*80}\n")
    
    all_passed = True
    
    for ids_file in sorted(ids_files):
        # Find corresponding extracted file in same directory
        base_name = ids_file.stem.replace('.ids', '')
        extracted_file = ids_file.parent / f"{base_name}_extracted.json"
        
        if not extracted_file.exists():
            print(f"✗ {ids_file.name}: Source file not found")
            all_passed = False
            continue
        
        # Validate
        success, issues = validate_ids_conversion(str(extracted_file), str(ids_file))
        
        if success:
            print(f"✓ {ids_file.name}: PASSED")
        else:
            print(f"✗ {ids_file.name}: FAILED")
            for issue in issues:
                print(f"  - {issue}")
            all_passed = False
    
    print(f"\n{'='*80}")
    if all_passed:
        print("✓ All validations PASSED")
    else:
        print("✗ Some validations FAILED")
    print(f"{'='*80}\n")
    
    return all_passed


if __name__ == "__main__":
    success = validate_all()
    sys.exit(0 if success else 1)
