# IDS (Intermediary Data Schema) Design Document

## Overview

The IDS is a unified JSON schema for Fast Protein Liquid Chromatography (FPLC) data that enables:
- **Cross-platform compatibility**: AKTA (UNICORN), BioRad (NGC, CFX), and other FPLC systems
- **Complete data preservation**: All sensor data, events, peaks, and metadata
- **Extensibility**: Custom fields for platform-specific data
- **Validation**: JSON Schema for automated validation

## Schema Version: 1.0.0

## Core Design Principles

### 1. Separation of Concerns
- **Metadata**: Source file information, extraction details
- **Run Parameters**: Experimental conditions, instrument configuration
- **Sensor Data**: Time-series measurements (UV, pressure, conductivity, etc.)
- **Events**: Discrete occurrences (injections, fractions, alarms)
- **Peaks**: Integrated peak data
- **Fractions**: Collected fraction information

### 2. Flexibility in X-Axis
Data can be referenced by:
- Volume (ml) - most common
- Time (min/sec)
- Fraction number

Each sensor specifies its x-axis type and unit.

### 3. Multi-Channel Support
- Multiple UV wavelengths (e.g., UV 1_280, UV 2_295, UV 3_0)
- Multiple pressure sensors (PreC, PostC, System, Delta)
- Multiple flow measurements
- Each sensor is independent with its own sampling rate

### 4. Extensibility
- `custom_data` section for format-specific information
- `metadata` field in sensors, events, and peaks for additional properties
- `additionalProperties: true` allows format extensions

## Key Fields

### Metadata Section
```json
{
  "source_format": "AKTA-UNICORN-6",
  "file_name": "2025.03.12_PPLOT00335.zip",
  "extraction_timestamp": "2026-01-16T18:45:00Z",
  "extraction_tool": "PyCORN-0.20",
  "schema_version": "1.0.0"
}
```

### Run Parameters Section
Critical for reproducing chromatography:
- Instrument identification
- Column specifications (volume, type, dimensions)
- Method/protocol reference
- Sample information

### Sensor Data Section
Array of sensor objects, each with:
```json
{
  "sensor_id": "uv_280_1",
  "sensor_type": "UV",
  "sensor_name": "UV 1_280",
  "wavelength_nm": 280,
  "unit": "mAU",
  "x_axis_type": "volume",
  "x_axis_unit": "ml",
  "data_points": [[0.0, -0.0016], [0.0016, -0.0016], ...]
}
```

**Sensor Types**:
- `UV`: Ultraviolet/visible absorbance
- `Conductivity`: Electrical conductivity (mS/cm or %)
- `Pressure`: System, column, or differential pressure
- `Temperature`: Temperature measurements
- `pH`: pH readings
- `Flow`: Flow rate measurements
- `Concentration`: Buffer concentration (e.g., % Buffer B)
- `Other`: Platform-specific sensors

### Events Section
Captures discrete occurrences:
```json
{
  "event_id": "injection_1",
  "event_type": "injection",
  "event_name": "Sample injection",
  "position": {
    "volume_ml": 13.579,
    "time_min": 6.365
  },
  "description": "Automatic injection"
}
```

**Event Types**:
- `injection`: Sample introduction
- `fraction_start`/`fraction_end`: Fraction collection boundaries
- `alarm`: System alarms or warnings
- `phase_change`: Method phase transitions
- `logbook`: Log entries
- `mark`: User-defined markers
- `other`: Custom events

### Peaks Section
Integrated peak data for quantitative analysis:
```json
{
  "peak_id": "peak_1_uv280",
  "sensor_id": "uv_280_1",
  "peak_number": 1,
  "retention_volume_ml": 14.2,
  "height": 125.5,
  "area": 1250.3,
  "percent_total_area": 87.5,
  "classification": "monomer"
}
```

### Fractions Section
Collected fractions with positions:
```json
{
  "fraction_id": "frac_1",
  "fraction_number": 1,
  "well_position": "A1",
  "start_volume_ml": 13.5,
  "end_volume_ml": 15.0,
  "volume_ml": 1.5,
  "peak_id": "peak_1_uv280"
}
```

## Format-Specific Considerations

### AKTA (UNICORN 6/7)
- Typically provides: UV (multiple wavelengths), Cond, pH, Pressure (multiple), Flow, Temperature
- Events may include: Injection, Fractions, Logbook entries
- Peaks usually integrated by UNICORN software

### BioRad (NGC)
- Similar sensor suite to AKTA
- May have different naming conventions
- Column volume often explicitly specified

### Generic/Other Formats
- Use `sensor_type: "Other"` for custom sensors
- Store platform-specific data in `custom_data` section
- Maintain original field names in metadata

## Validation

The schema is a JSON Schema (draft-07) that can be validated using standard tools:

```python
import jsonschema
import json

with open('ids_schema.json') as f:
    schema = json.load(f)

with open('data.ids.json') as f:
    data = json.load(f)

jsonschema.validate(instance=data, schema=schema)
```

## File Naming Convention

IDS files should follow this naming pattern:
```
[original_name].ids.json
```

Examples:
- `2025.03.12_PPLOT00335.ids.json`
- `biorad_run_001.ids.json`

## Evolution and Versioning

Schema version follows semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes (e.g., required field changes)
- **MINOR**: Backward-compatible additions (e.g., new optional fields)
- **PATCH**: Documentation updates, clarifications

Current version: **1.0.0**

## Usage Example

See [sample.ids.json](../execution/sample.ids.json) for a complete example derived from AKTA data.

## References

- JSON Schema: https://json-schema.org/
- PyCORN: https://github.com/ronald-jaepel/PyCORN
- FPLC Data Analysis Report: [analysis_report.json](../.tmp/akta_extracted/analysis_report.json)
