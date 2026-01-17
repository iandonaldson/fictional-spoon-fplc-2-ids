# fictional-spoon-fplc-2-ids

Develop parsers that convert various FPLC formats to an Intermediary Data Schema (IDS).

## Overview

This project implements a complete pipeline for converting ÄKTA chromatography data files to a standardized IDS format with comprehensive validation and testing.

## Quick Start

### Prerequisites

- Python 3.x
- PyCORN library (installed automatically by pipeline)

### Running the Complete Pipeline

```bash
# Clean build with all validation (recommended for first run)
python orchestrate.py --clean

# Process specific files only
python orchestrate.py --process-files "sample.zip,file2.zip"

# Skip specific validation steps
python orchestrate.py --no-check-end2end

# Custom data directory
python orchestrate.py --data-dir path/to/data
```

## Pipeline Architecture

The pipeline follows a 6-step process:

1. **Extract** - Extract data from AKTA .zip archives using PyCORN
2. **Test Extraction** - Verify all source files were extracted successfully
3. **Convert** - Transform extracted data to IDS JSON format
4. **Validate** - Verify IDS conversions preserve all data
5. **End-to-End Test** - Complete pipeline coverage validation (optional)
6. **CSV Export** - Generate CSV files from IDS data for analysis

### Pipeline Orchestrator

The `orchestrate.py` script coordinates the entire pipeline with configurable options:

```bash
python orchestrate.py [options]

Options:
  --data-dir PATH           Data directory with AKTA .zip files (default: data/akta)
  --process-files FILES     Files to process: 'all', 'none', or comma-separated list
  --log-dir PATH            Directory for timestamped logs (default: output/logs)
  --clean                   Clean all output directories before starting
  --csv / --no-csv          Create CSV exports (default: yes)
  --check-extraction        Verify extraction coverage (default: yes)
  --check-conversion        Validate IDS conversions (default: yes)
  --check-end2end           Run end-to-end pipeline test (default: yes)
```

### Directory Structure

```
fictional-spoon-fplc-2-ids/
├── orchestrate.py              # Main pipeline coordinator
├── data/
│   └── akta/                   # Source AKTA .zip files
├── execution/                  # Individual processing scripts
│   ├── extract_akta_v2.py      # AKTA data extraction
│   ├── akta_to_ids.py          # IDS conversion + CSV export
│   ├── test_extraction_coverage.py
│   ├── validate_ids_conversion.py
│   └── test_complete_pipeline.py
├── directives/                 # Process documentation
│   ├── a2i.md                  # AKTA to IDS converter directive
│   ├── ids_schema_v1.json      # IDS JSON schema definition
│   ├── IDS_DOCUMENTATION.md    # Schema documentation
│   └── PyCORN_usage.md         # PyCORN API reference
├── .tmp/
│   └── akta_extracted/         # Extracted data and IDS outputs
│       └── {sample}/
│           ├── raw_files/      # Original extracted files
│           ├── {sample}_extracted.json
│           ├── {sample}_summary.json
│           ├── {sample}.ids.json
│           └── {sample}.ids.csv
└── output/
    └── logs/                   # Timestamped execution logs
```

## Manual Execution

Individual pipeline steps can be run manually:

### 1. Extract AKTA Data

```bash
python execution/extract_akta_v2.py --all .tmp/akta_extracted
```

### 2. Test Extraction Coverage

```bash
python execution/test_extraction_coverage.py
```

### 3. Convert to IDS Format

```bash
python execution/akta_to_ids.py path/to/extracted.json
# Or convert all files in a directory
python execution/akta_to_ids.py --all .tmp/akta_extracted
```

### 4. Validate IDS Conversion

```bash
python execution/validate_ids_conversion.py
```

### 5. Generate CSV Export

```bash
python execution/akta_to_ids.py --csv path/to/file.ids.json
```

### 6. Run Complete Pipeline Test

```bash
python execution/test_complete_pipeline.py
```

## IDS Format

The Intermediary Data Schema (IDS) is a standardized JSON format for chromatography data:

- **Schema Version**: 1.0.0
- **Multi-platform support**: AKTA, BioRad, and other FPLC systems
- **Flexible sensor data**: Variable sampling rates per sensor
- **Complete metadata**: Provenance, instrument config, run parameters
- **Event tracking**: Injections, fractions, alarms, user marks
- **Optional peaks**: Integrated peak data when available

See [directives/IDS_DOCUMENTATION.md](directives/IDS_DOCUMENTATION.md) for complete specification.

## Logging

All pipeline runs generate timestamped logs in `output/logs/`:

- `orchestrate_YYYYMMDD_HHMMSS.log` - Main orchestration log
- `step{N}_{operation}_YYYYMMDD_HHMMSS.log` - Individual step logs
- `results_YYYYMMDD_HHMMSS.json` - Machine-readable results summary

## Testing

The pipeline includes comprehensive testing at multiple levels:

- **Unit tests**: Individual file extraction and conversion
- **Integration tests**: Cross-step data validation
- **End-to-end tests**: Complete pipeline coverage

Run all tests with:
```bash
python orchestrate.py --clean
```

## Known Issues

1. **extract_akta_v2.py**: Currently not extracting curve data properly - end-to-end test will fail. Use `--no-check-end2end` to skip this test.
2. **Path handling**: All scripts use absolute paths to avoid working directory issues

## Documentation

- [directives/a2i.md](directives/a2i.md) - Complete AKTA to IDS process documentation
- [directives/PyCORN_usage.md](directives/PyCORN_usage.md) - PyCORN API reference
- [directives/IDS_DOCUMENTATION.md](directives/IDS_DOCUMENTATION.md) - IDS schema specification
- [.github/copilot-instructions.md](.github/copilot-instructions.md) - AI agent instructions

## License

See [LICENSE](LICENSE) for details.
