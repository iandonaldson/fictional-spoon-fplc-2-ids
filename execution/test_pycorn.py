"""
Test script to verify PyCORN can handle UNICORN 6 zip format

Usage:
    python test_pycorn.py <path_to_zip_file>
"""

import sys
sys.path.insert(0, '/tmp/PyCORN')

from pycorn import PcUni6
import json

def test_pycorn_on_zip(zip_file_path):
    """Test if PyCORN can extract data from UNICORN 6 zip file"""
    
    print(f"Testing PyCORN on: {zip_file_path}")
    print("=" * 60)
    
    try:
        # Create PcUni6 object
        print("\n1. Loading zip file...")
        data = PcUni6(zip_file_path)
        
        # Load the file
        print("2. Calling load()...")
        data.load(print_log=True)
        
        # Load all XML data
        print("\n3. Calling load_all_xml()...")
        data.load_all_xml()
        
        # Display available keys
        print("\n4. Available data keys:")
        for key in sorted(data.keys()):
            print(f"   - {key}")
        
        # Check for chromatogram data
        print("\n5. Looking for chromatogram data...")
        chrom_keys = [k for k in data.keys() if k.startswith('Chrom.') and not k.endswith('.Xml') and not k.endswith('_dict')]
        
        if chrom_keys:
            print(f"   Found chromatogram: {chrom_keys[0]}")
            chrom_data = data[chrom_keys[0]]
            
            print(f"\n6. Data types available in {chrom_keys[0]}:")
            for key in sorted(chrom_data.keys()):
                print(f"   - {key}")
                
            # Try to extract UV data
            print("\n7. Attempting to extract UV data...")
            uv_keys = [k for k in chrom_data.keys() if 'UV' in k and 'cell path' not in k.lower()]
            
            if uv_keys:
                uv_key = uv_keys[0]
                print(f"   Found UV data: {uv_key}")
                uv_data = chrom_data[uv_key]
                
                print(f"\n8. UV data structure:")
                for k, v in uv_data.items():
                    if k == 'data':
                        print(f"   - {k}: {len(v)} data points")
                        print(f"      First 3 points: {v[:3]}")
                        print(f"      Last 3 points: {v[-3:]}")
                    else:
                        print(f"   - {k}: {v}")
                
                print("\n✓ SUCCESS: PyCORN can read this zip format!")
                return True
            else:
                print("   ✗ No UV data found")
                return False
        else:
            print("   ✗ No chromatogram data found")
            return False
            
    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_pycorn.py <path_to_zip_file>")
        sys.exit(1)
    
    zip_file = sys.argv[1]
    success = test_pycorn_on_zip(zip_file)
    sys.exit(0 if success else 1)
