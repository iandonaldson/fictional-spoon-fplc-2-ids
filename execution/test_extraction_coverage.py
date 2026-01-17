"""
Test script to verify all AKTA files have been extracted and captured

This script:
1. Checks that all .zip files in data/akta/ have been processed
2. Verifies extraction output directories and files exist
3. Validates JSON outputs are readable and contain expected structure
4. Reports any missing or incomplete extractions
"""

import json
import os
from pathlib import Path


def test_extraction_coverage():
    """
    Test that all AKTA files have been successfully extracted
    """
    
    # Paths (use absolute paths from workspace root)
    workspace_root = Path(__file__).parent.parent
    data_dir = workspace_root / "data" / "akta"
    output_dir = workspace_root / ".tmp" / "akta_extracted"
    
    print("="*80)
    print("AKTA Extraction Coverage Test")
    print("="*80)
    
    # Find all source zip files
    zip_files = sorted(data_dir.glob("*.zip"))
    print(f"\n[1/4] Found {len(zip_files)} source AKTA file(s):")
    for zf in zip_files:
        print(f"  - {zf.name}")
    
    if not zip_files:
        print("  ✗ ERROR: No .zip files found in data/akta/")
        return False
    
    # Check output directory exists
    print(f"\n[2/4] Checking output directory: {output_dir}")
    if not output_dir.exists():
        print(f"  ✗ ERROR: Output directory does not exist")
        return False
    print(f"  ✓ Output directory exists")
    
    # Check each file has been extracted
    print(f"\n[3/4] Verifying extractions:")
    all_successful = True
    results = []
    
    for zip_file in zip_files:
        base_name = zip_file.stem  # Remove .zip extension
        sample_dir = output_dir / base_name
        
        result = {
            "source": zip_file.name,
            "extracted": False,
            "raw_files": False,
            "json_files": [],
            "issues": []
        }
        
        # Check sample directory exists
        if not sample_dir.exists():
            result["issues"].append("Sample directory missing")
            all_successful = False
        else:
            result["extracted"] = True
            
            # Check raw_files/ subdirectory
            raw_files_dir = sample_dir / "raw_files"
            if raw_files_dir.exists():
                raw_count = len(list(raw_files_dir.glob("*")))
                result["raw_files"] = True
                result["raw_file_count"] = raw_count
            else:
                result["issues"].append("raw_files/ directory missing")
                all_successful = False
            
            # Check JSON files
            expected_json = [
                f"{base_name}_extracted.json",
                f"{base_name}_summary.json"
            ]
            
            for json_file in expected_json:
                json_path = sample_dir / json_file
                if json_path.exists():
                    # Try to load JSON to verify it's valid
                    try:
                        with open(json_path, 'r') as f:
                            data = json.load(f)
                        result["json_files"].append(json_file)
                    except json.JSONDecodeError as e:
                        result["issues"].append(f"{json_file}: Invalid JSON - {e}")
                        all_successful = False
                else:
                    result["issues"].append(f"{json_file}: File missing")
                    all_successful = False
        
        results.append(result)
        
        # Print result for this file
        status = "✓" if not result["issues"] else "✗"
        print(f"\n  {status} {zip_file.name}")
        print(f"     Directory: {sample_dir}")
        if result["raw_files"]:
            print(f"     Raw files: {result['raw_file_count']} files")
        if result["json_files"]:
            print(f"     JSON files: {', '.join(result['json_files'])}")
        if result["issues"]:
            print(f"     Issues:")
            for issue in result["issues"]:
                print(f"       - {issue}")
    
    # Check for unexpected directories
    print(f"\n[4/4] Checking for unexpected files:")
    expected_dirs = {zf.stem for zf in zip_files}
    actual_dirs = {d.name for d in output_dir.iterdir() if d.is_dir()}
    unexpected = actual_dirs - expected_dirs
    
    if unexpected:
        print(f"  ⚠ Found {len(unexpected)} unexpected director(ies):")
        for d in unexpected:
            print(f"    - {d}")
    else:
        print(f"  ✓ No unexpected directories")
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    successful = sum(1 for r in results if not r["issues"])
    print(f"Source files: {len(zip_files)}")
    print(f"Successfully extracted: {successful}/{len(zip_files)}")
    
    if all_successful:
        print(f"\n✓ ALL FILES SUCCESSFULLY EXTRACTED AND VALIDATED")
        return True
    else:
        failed = len(zip_files) - successful
        print(f"\n✗ {failed} FILE(S) FAILED OR INCOMPLETE")
        return False


if __name__ == "__main__":
    success = test_extraction_coverage()
    exit(0 if success else 1)
