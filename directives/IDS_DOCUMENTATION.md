# IDS (Intermediary Data Schema) Documentation

## Overview

The FPLC Intermediary Data Schema (IDS) is a unified, vendor-agnostic format for representing chromatography data from multiple platforms (AKTA, BioRad, etc.). It serves as a "source of truth" enabling:

- **Cross-platform compatibility**: Data from different instruments in one format
- **Data integration**: Combine runs from multiple systems
- **Analysis standardization**: Common structure for downstream processing
- **Long-term archival**: Platform-independent data preservation

## Design Principles

1. **Extensibility**: Accommodate new platforms and sensor types without breaking changes
2. **Self-documenting**: Clear field names and embedded metadata
3. **Normalized structure**: Minimize redundancy, maximize clarity
4. **Flexible arrays**: Support variable numbers of UV channels, sensors, events
5. **SI units preferred**: Use standard units where possible (with original units preserved)

## Schema Structure

### Top Level

```json
{
  "schema_version": "1.0.0",
  "metadata": {...},      // Source file and extraction info
  "run_info": {...},      // Run parameters and instrument config
  "data": {
    "curves": [...],      // Time-series sensor data
    "events": [...],      // Discrete events (injections, fractions)
    "peaks": [...]        // Detected peaks (optional)
  }
}
```

### 1. Metadata Section

Tracks data provenance and extraction details:

- `source_format`: Platform identifier (e.g., "AKTA-UNICORN-6")
- `source_file`: Original filename
- `source_file_hash`: SHA256 for integrity verification
- `extraction_timestamp`: When conversion occurred
- `extraction_tool`: Tool used (e.g., "PyCORN-0.20")
- `converter_version`: Version of conversion script

**Purpose**: Ensures traceability back to original data source.

### 2. Run Info Section

Captures experimental context:

**Required**:
- `run_timestamp`: When chromatography run started (ISO 8601)

**Optional but recommended**:
- `run_id`, `run_name`: Identifiers
- `instrument`: manufacturer, model, serial_number, software_version
- `method`: name, description, file path
- `column`: name, type (SEC/IEX/HIC), volume_ml, dimensions
- `sample`: id, name, description, volume_ml, concentration
- `operator`: Person who performed run
- `notes`: Free text annotations

**Purpose**: Preserves experimental metadata critical for reproducibility and analysis.

### 3. Data Section

#### 3a. Curves (Time-Series Data)

Array of sensor measurements over time/volume:

**Required fields**:
- `curve_id`: Unique identifier (e.g., "UV_280nm", "Pressure_System")
- `curve_type`: Standardized category
  - UV, Fluorescence, Conductivity, Pressure, Temperature, pH, Flow, Concentration, Other
- `curve_name`: Human-readable name
- `unit`: Measurement unit (e.g., "mAU", "mS/cm", "MPa")
- `x_axis`: Definition of independent variable
  - `type`: "volume", "time", or "fraction"
  - `unit`: "ml", "min", or "fraction_number"
- `data`: Array of `[x, y]` pairs

**Optional fields**:
- `sampling_rate`: Points per unit (for info only)
- `metadata`: Curve-specific details
  - `wavelength_nm`: For UV/Fluorescence
  - `sensor_id`: Physical sensor identifier
  - `calibration_date`: Last calibration

**Design rationale**:
- **Flexible X-axis**: Some platforms use volume, others use time
- **Multiple UV channels**: curve_id distinguishes wavelengths
- **Variable sampling rates**: Each curve has independent data array
- **Extensible metadata**: Platform-specific details in metadata object

#### 3b. Events (Discrete Annotations)

Array of point events marking important moments:

**Required fields**:
- `event_id`: Unique identifier
- `event_type`: Category
  - injection, fraction_start, fraction_end, alarm, user_mark, method_step, other
- `position`: Where event occurred
  - `value`: Position on x-axis
  - `unit`: "ml" or "min"

**Optional fields**:
- `event_name`: Display label
- `text`: Descriptive text
- `metadata`: Event-specific data (flexible)

**Common event types**:
- **injection**: Sample loaded onto column
- **fraction_start/end**: Collection boundaries
- **alarm**: System alerts
- **user_mark**: Manual annotations
- **method_step**: Protocol phase changes

#### 3c. Peaks (Detected Features)

Array of integrated peaks (optional, not always available):

**Required fields**:
- `peak_id`: Unique identifier
- `curve_id`: Reference to curve where peak found
- `retention`: Peak apex position (value + unit)

**Optional fields**:
- `peak_number`: Sequential numbering
- `area`, `area_percent`: Integration results
- `height`: Peak maximum
- `width`: Peak width (various definitions)
- `start`, `end`: Peak boundaries
- `symmetry`: Asymmetry factor
- `resolution`: Separation from previous peak

**Note**: Many platforms don't auto-detect peaks, so this array is often empty in raw data.

## Key Features

### 1. Multi-Channel Support

Sample with 3 UV wavelengths:

```json
{
  "curves": [
    {
      "curve_id": "UV_280nm",
      "curve_type": "UV",
      "metadata": {"wavelength_nm": 280},
      ...
    },
    {
      "curve_id": "UV_295nm", 
      "curve_type": "UV",
      "metadata": {"wavelength_nm": 295},
      ...
    },
    {
      "curve_id": "UV_0nm",
      "curve_type": "UV", 
      "metadata": {"wavelength_nm": 0},
      ...
    }
  ]
}
```

### 2. Variable Sampling Rates

Different sensors sample at different frequencies:

```json
{
  "curves": [
    {
      "curve_id": "UV_280nm",
      "sampling_rate": 600.0,    // 600 points/ml
      "data": [[0.0, -0.001], [0.00167, -0.001], ...]  // 22,580 points
    },
    {
      "curve_id": "pH_01",
      "sampling_rate": 60.0,     // 60 points/ml  
      "data": [[0.0117, 7.0], [0.0283, 7.0], ...]      // 2,243 points
    }
  ]
}
```

### 3. Cross-Platform Extensibility

Schema accommodates different platforms:

**AKTA files** have:
- UV, Conductivity, Pressure (multiple), Flow, pH, Temperature
- Events: Fractions, Injections

**BioRad files** might have:
- UV (different wavelengths), Conductivity, Pressure
- Events: Fractions, Peaks (auto-detected)

**Schema handles both** via:
- Flexible `curve_type` enum (extensible)
- Generic `event_type` enum
- Platform-specific details in `metadata` objects

### 4. Unit Preservation

Original units always preserved:

```json
{
  "curve_id": "Pressure_System",
  "unit": "MPa",              // AKTA uses MPa
  "data": [[0.0, 0.002], ...]
}
```

vs.

```json
{
  "curve_id": "Pressure_Column",
  "unit": "psi",              // BioRad might use psi
  "data": [[0.0, 0.29], ...]
}
```

## Usage Guidelines

### For Data Producers (Converters)

1. **Required fields**: Always populate schema_version, metadata, run_info.run_timestamp, data.curves
2. **Unique IDs**: Ensure curve_id and event_id are unique within the file
3. **Standardize types**: Map platform-specific curve types to standard categories
4. **Preserve originals**: Keep original units and names in appropriate fields
5. **X-axis consistency**: Use same x-axis type/unit for all curves in a run

### For Data Consumers (Analysis Tools)

1. **Check schema_version**: Validate compatibility
2. **Iterate curves**: Don't assume specific curve_ids exist
3. **Filter by curve_type**: Select data by standardized type
4. **Handle missing data**: Not all runs have events or peaks
5. **Unit conversion**: Convert to analysis units as needed

## Validation

Validate IDS files against the schema:

```bash
# Using Python jsonschema
python -c "
import json
import jsonschema

with open('ids_schema.json') as f:
    schema = json.load(f)
with open('data.json') as f:
    data = json.load(f)
    
jsonschema.validate(data, schema)
print('Valid!')
"
```

## Version History

### 1.0.0 (2026-01-16)
- Initial schema design
- Support for AKTA UNICORN 6 format
- Extensible structure for multi-platform support
- Flexible curve and event arrays
- Comprehensive metadata capture

## Future Enhancements

Potential additions in future versions:

- **Batch processing**: Link multiple runs
- **Processed data**: Store analyzed/normalized curves alongside raw
- **Calibration data**: Embed calibration curves for sensors
- **Images**: Reference to gel/blot images associated with fractions
- **Provenance chain**: Link to upstream sample prep steps
