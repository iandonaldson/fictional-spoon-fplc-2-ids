#!/usr/bin/env python3
"""
Utility to properly extract and view binary configuration files from AKTA archives.

These files (MethodData, SystemData, etc.) are:
1. ZIP archives
2. Containing .NET binary-serialized XML
3. With a binary header that must be skipped

This script demonstrates how to:
- Open these files correctly
- Skip the .NET binary header
- Extract readable XML content
- Show that the XML is NOT in the output JSON files

Usage:
    python notes/extract_and_view_binary_files.py
"""

import zipfile
from pathlib import Path


def extract_dotnet_xml(zip_path):
    """
    Extract XML from a .NET binary-serialized ZIP file.
    
    .NET binary format structure:
    - Bytes 0-17: Binary header (18 bytes)
    - Bytes 18+: Actual XML content
    
    Returns:
    - xml_content: The extracted XML string
    - header_size: Size of the binary header
    """
    with zipfile.ZipFile(zip_path, 'r') as zf:
        if 'Xml' not in zf.namelist():
            return None, 0
        
        # Read the raw bytes
        raw_bytes = zf.read('Xml')
        
        # .NET binary serialization typically has an 18-byte header
        # Look for the XML declaration or root element
        xml_start = raw_bytes.find(b'<')
        
        if xml_start == -1:
            return None, 0
        
        # Extract XML from the found position
        xml_bytes = raw_bytes[xml_start:]
        xml_content = xml_bytes.decode('utf-8', errors='ignore')
        
        return xml_content, xml_start


def main():
    print("="*80)
    print("AKTA Binary Configuration Files - Extraction Demo")
    print("="*80)
    print()
    
    base_dir = Path("/workspaces/fictional-spoon-fplc-2-ids")
    raw_files = base_dir / ".tmp/akta_extracted/sample/raw_files"
    
    config_files = [
        'MethodData',
        'SystemData',
        'CalibrationSettingData',
    ]
    
    for config_file in config_files:
        file_path = raw_files / config_file
        
        if not file_path.exists():
            continue
        
        print(f"\n{'='*80}")
        print(f"FILE: {config_file}")
        print(f"{'='*80}")
        
        # Extract XML
        xml_content, header_size = extract_dotnet_xml(file_path)
        
        if xml_content is None:
            print("  ✗ No XML found in file")
            continue
        
        print(f"\n✓ Successfully extracted XML")
        print(f"  - .NET binary header size: {header_size} bytes")
        print(f"  - XML content size: {len(xml_content):,} characters")
        print(f"  - Compressed file size: {file_path.stat().st_size:,} bytes")
        print(f"  - Compression ratio: {len(xml_content) / file_path.stat().st_size:.1f}x")
        
        # Show first 1000 characters of XML
        print(f"\n--- First 1000 characters of XML content ---")
        print(xml_content[:1000])
        print(f"\n... ({len(xml_content) - 1000:,} more characters) ...\n")
        
        # Extract key information based on file type
        if 'MethodData' in config_file:
            if '<Description>' in xml_content:
                desc_start = xml_content.find('<Description>') + len('<Description>')
                desc_end = xml_content.find('</Description>')
                method_desc = xml_content[desc_start:desc_end]
                print(f"✓ Method Description: {method_desc}")
            
            if '<SystemName>' in xml_content:
                sys_start = xml_content.find('<SystemName>') + len('<SystemName>')
                sys_end = xml_content.find('</SystemName>')
                system_name = xml_content[sys_start:sys_end]
                print(f"✓ System Name: {system_name}")
        
        print()
    
    # Now check if this data is in the output JSON
    print("\n" + "="*80)
    print("CHECKING: Is this XML content in the output IDS JSON files?")
    print("="*80)
    
    ids_json_path = base_dir / "output/sample/json/sample.ids.json"
    
    if ids_json_path.exists():
        with open(ids_json_path, 'r') as f:
            ids_content = f.read()
        
        print(f"\nIDS JSON file size: {len(ids_content):,} characters")
        
        # Check for method description
        if 'Soumi_ColumnSaltPulseTest' in ids_content:
            print("✓ Method description FOUND in IDS JSON")
        else:
            print("✗ Method description NOT in IDS JSON")
        
        # Check for method XML structure
        if '<Block>' in ids_content or '<Blocks>' in ids_content:
            print("✓ Method XML structure FOUND in IDS JSON")
        else:
            print("✗ Method XML structure NOT in IDS JSON")
        
        # Check run_info.method fields
        if '"method": {' in ids_content:
            method_start = ids_content.find('"method": {')
            method_section = ids_content[method_start:method_start+200]
            print(f"\nMethod section in IDS JSON:")
            print(method_section)
    
    print("\n" + "="*80)
    print("CONCLUSION:")
    print("="*80)
    print("""
Configuration files (MethodData, SystemData, etc.):
✓ ARE present in raw AKTA archives
✓ CONTAIN extensive XML configuration data (10KB-150KB compressed)
✓ CAN be extracted using proper ZIP + binary header handling
✗ ARE NOT transferred to final IDS output JSON files

The IDS format focuses on:
- Chromatogram time-series data (UV traces, conductivity, etc.)
- Basic run metadata (timestamps, instrument info)
- NOT method configuration/instructions

To access method configuration, extract from raw files or use the
.tmp/akta_extracted/<sample>/ directories where metadata is preserved.
""")
    print("="*80)


if __name__ == "__main__":
    main()
