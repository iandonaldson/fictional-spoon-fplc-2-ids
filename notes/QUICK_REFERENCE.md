# Quick Reference: Opening AKTA Binary Configuration Files

## TL;DR

```bash
# Problem: This looks garbled
unzip -p MethodData Xml | head

# Solution: Use strings to skip binary header
unzip -p MethodData Xml | strings > MethodData.xml

# Or use the Python utility
python notes/extract_and_view_binary_files.py
```

## File Types

| File | Type | Compressed | Uncompressed | Content |
|------|------|-----------|--------------|---------|
| `Chrom.1_*_True` | ZIP + Binary | 10-90 KB | N/A | Float32 arrays (sensor data) |
| `MethodData` | ZIP + .NET XML | 10 KB | 147 KB | Method definition |
| `SystemData` | ZIP + .NET XML | 5 KB | 21 KB | Hardware config |
| `CalibrationSettingData` | ZIP + .NET XML | 1.3 KB | 2 KB | Calibration params |

## Opening Methods

### Method 1: `strings` Command (Easiest)

```bash
cd .tmp/akta_extracted/sample/raw_files

# Extract all configuration files
for file in MethodData SystemData CalibrationSettingData; do
    unzip -p "$file" Xml | strings > "${file}.xml"
done

# View
cat MethodData.xml | head -50
```

### Method 2: Python Script (Most Reliable)

```python
import zipfile

def extract_xml(file_path):
    with zipfile.ZipFile(file_path, 'r') as zf:
        raw = zf.read('Xml')
        start = raw.find(b'<')
        return raw[start:].decode('utf-8')

# Usage
xml = extract_xml('MethodData')
print(xml[:1000])
```

### Method 3: Use Provided Utility

```bash
python notes/extract_and_view_binary_files.py
```

## What's Inside

### MethodData
- **Method name:** `Soumi_ColumnSaltPulseTest_WithPurgeAndEq_Rev_00`
- **System:** `AKTA Pure 2350181`
- **Blocks:** PurgeB, Purge, Equilibrate, SampleLoad, Wash, RUN
- **Instructions:** Flow rates, gradients, injection valves, peak fractionation
- **Scouting runs:** 8 configurations with different volumes/flows

### SystemData
- **System name:** `AKTA Pure 2350181`
- **Computer:** `DESKTOP-JG88QSN`
- **Configuration:** `AKTA pure 25` v1.9.0.11
- **Components:** Accumulator wash, air sensors, buffer valves, UV monitors
- **Communication:** Ethernet, port 40502

### CalibrationSettingData
- **Calibration points:** pH 7.0, pH 4.01
- **Electrode slope:** 100.066%
- **Asymmetry potential:** -25.929 mV
- **Calibration date:** Various timestamps

## Common Issues

### Issue 1: Binary/Garbled Output
**Symptom:** `������ <Method xmlns:xsi=...`

**Cause:** .NET binary serialization header (24-25 bytes)

**Fix:** Use `strings` or skip header in Python

### Issue 2: Empty or Null Fields in IDS Output
**Symptom:** `"method": {"name": null, "description": null}`

**Cause:** Configuration data is not transferred to IDS format by design

**Fix:** Access from raw files using methods above

### Issue 3: File Not Found
**Symptom:** `No such file or directory: MethodData`

**Cause:** Need to extract from original .zip first

**Fix:**
```bash
# Extract all files
unzip sample.zip -d raw_files/
cd raw_files/

# Then access MethodData
unzip -p MethodData Xml | strings
```

## Key Differences

### Chromatogram Data (Chrom.1_*_True)
- ✓ Transferred to IDS output
- ✓ Accessible via PyCORN library
- ✓ In final sample.ids.json (97,980 points)

### Configuration Data (MethodData, etc.)
- ✗ NOT transferred to IDS output
- ⚠ Requires manual extraction
- ⚠ Preserved in raw_files/ only

## Verification

Prove what's transferred:

```bash
# Check IDS output
grep "Soumi_ColumnSaltPulseTest" output/sample/json/sample.ids.json
# Returns: (nothing found)

# Check raw files
unzip -p .tmp/akta_extracted/sample/raw_files/MethodData Xml | strings | grep "Soumi"
# Returns: <Description>Soumi_ColumnSaltPulseTest_WithPurgeAndEq_Rev_00</Description>
```

## Scripts

1. **`notes/extract_and_view_binary_files.py`** - Extract and view all config files
2. **`notes/verify_method_data_transfer.py`** - Verify what's transferred where
3. **`notes/verify_binary_data.py`** - Check curve data transfer

## See Also

- Full documentation: [notes/akta_raw_files_desc.md](./akta_raw_files_desc.md)
- Transfer report: [notes/configuration_data_transfer_report.md](./configuration_data_transfer_report.md)
