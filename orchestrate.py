#!/usr/bin/env python
"""
AKTA to IDS Pipeline Orchestrator

Coordinates the complete data processing pipeline from AKTA .zip files to validated IDS outputs.

Pipeline Steps:
1. Extract data from AKTA .zip archives
2. Test extraction coverage (optional)
3. Convert extracted data to IDS format
4. Validate IDS conversions (optional)
5. End-to-end pipeline test (optional)
6. Generate CSV exports (optional)

Usage:
    python orchestrate.py [options]
    
Examples:
    python orchestrate.py --clean                    # Clean build all files
    python orchestrate.py --process-files sample.zip # Process single file
    python orchestrate.py --data-dir custom_data     # Use custom data directory
"""

import argparse
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import json


class PipelineOrchestrator:
    """Orchestrates the complete AKTA to IDS pipeline"""
    
    def __init__(self, args):
        self.args = args
        self.workspace_root = Path(__file__).parent.absolute()
        self.data_dir = self.workspace_root / args.data_dir
        self.tmp_dir = self.workspace_root / ".tmp" / "akta_extracted"
        self.log_dir = self.workspace_root / args.log_dir
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Execution scripts
        self.extract_script = self.workspace_root / "execution" / "extract_akta_v2.py"
        self.test_extraction_script = self.workspace_root / "execution" / "test_extraction_coverage.py"
        self.convert_script = self.workspace_root / "execution" / "akta_to_ids.py"
        self.validate_script = self.workspace_root / "execution" / "validate_ids_conversion.py"
        self.test_pipeline_script = self.workspace_root / "execution" / "test_complete_pipeline.py"
        
        # Results tracking
        self.results = {
            "timestamp": self.timestamp,
            "steps": {},
            "files_processed": [],
            "success": False
        }
        
        # Setup logging
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.main_log = self.log_dir / f"orchestrate_{self.timestamp}.log"
        
    def log(self, message, level="INFO"):
        """Write to log file and console"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)
        
        with open(self.main_log, 'a') as f:
            f.write(log_message + "\n")
    
    def run_command(self, cmd, step_name, log_file=None):
        """Run a command and capture output"""
        if log_file is None:
            log_file = self.log_dir / f"{step_name}_{self.timestamp}.log"
        
        self.log(f"Running: {' '.join(str(c) for c in cmd)}")
        
        try:
            with open(log_file, 'w') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=True
                )
            
            self.log(f"✓ {step_name} completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"✗ {step_name} failed with exit code {e.returncode}", "ERROR")
            self.log(f"See log: {log_file}", "ERROR")
            return False
    
    def clean_outputs(self):
        """Clean all output directories"""
        self.log("Cleaning output directories...")
        
        dirs_to_clean = [
            self.tmp_dir,
            self.workspace_root / "output"
        ]
        
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                self.log(f"  Removing {dir_path}")
                shutil.rmtree(dir_path)
        
        # Recreate log directory after clean
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.log("✓ Clean complete")
    
    def get_files_to_process(self):
        """Get list of files to process"""
        if self.args.process_files == "all":
            files = sorted(self.data_dir.glob("*.zip"))
        elif self.args.process_files == "none":
            files = []
        else:
            # Parse comma-separated list
            file_list = [f.strip() for f in self.args.process_files.split(",")]
            files = [self.data_dir / f for f in file_list if (self.data_dir / f).exists()]
        
        return files
    
    def step1_extract(self):
        """Step 1: Extract AKTA data"""
        self.log("\n" + "="*80)
        self.log("STEP 1: Extract AKTA Data")
        self.log("="*80)
        
        # Check data directory exists
        if not self.data_dir.exists():
            self.log(f"✗ Data directory not found: {self.data_dir}", "ERROR")
            return False
        
        files = self.get_files_to_process()
        if not files:
            self.log("✗ No files to process", "ERROR")
            return False
        
        self.log(f"Processing {len(files)} file(s)")
        self.results["files_processed"] = [f.name for f in files]
        
        # Create temp directory
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        
        # Run extraction
        cmd = ["python", str(self.extract_script), "--all", str(self.tmp_dir)]
        success = self.run_command(cmd, "extract", self.log_dir / f"step1_extract_{self.timestamp}.log")
        
        self.results["steps"]["1_extract"] = {
            "success": success,
            "files": len(files)
        }
        
        return success
    
    def step2_test_extraction(self):
        """Step 2: Test extraction coverage"""
        if not self.args.check_extraction:
            self.log("\nStep 2: Skipped (--check-extraction=no)")
            return True
        
        self.log("\n" + "="*80)
        self.log("STEP 2: Test Extraction Coverage")
        self.log("="*80)
        
        cmd = ["python", str(self.test_extraction_script)]
        success = self.run_command(cmd, "test_extraction", self.log_dir / f"step2_test_extraction_{self.timestamp}.log")
        
        self.results["steps"]["2_test_extraction"] = {
            "success": success
        }
        
        return success
    
    def step3_convert(self):
        """Step 3: Convert to IDS format"""
        self.log("\n" + "="*80)
        self.log("STEP 3: Convert to IDS Format")
        self.log("="*80)
        
        # Find all extracted JSON files in subdirectories
        extracted_files = list(self.tmp_dir.glob("*/*_extracted.json"))
        
        if not extracted_files:
            self.log("✗ No extracted files found", "ERROR")
            return False
        
        self.log(f"Converting {len(extracted_files)} file(s)")
        
        all_success = True
        for extracted_file in extracted_files:
            cmd = ["python", str(self.convert_script), str(extracted_file)]
            success = self.run_command(
                cmd, 
                f"convert_{extracted_file.stem}",
                self.log_dir / f"step3_convert_{extracted_file.stem}_{self.timestamp}.log"
            )
            all_success = all_success and success
        
        self.results["steps"]["3_convert"] = {
            "success": all_success,
            "files": len(extracted_files)
        }
        
        return all_success
    
    def step4_validate(self):
        """Step 4: Validate IDS conversions"""
        if not self.args.check_conversion:
            self.log("\nStep 4: Skipped (--check-conversion=no)")
            return True
        
        self.log("\n" + "="*80)
        self.log("STEP 4: Validate IDS Conversions")
        self.log("="*80)
        
        cmd = ["python", str(self.validate_script)]
        success = self.run_command(cmd, "validate", self.log_dir / f"step4_validate_{self.timestamp}.log")
        
        self.results["steps"]["4_validate"] = {
            "success": success
        }
        
        return success
    
    def step5_end2end(self):
        """Step 5: End-to-end pipeline test"""
        if not self.args.check_end2end:
            self.log("\nStep 5: Skipped (--check-end2end=no)")
            return True
        
        self.log("\n" + "="*80)
        self.log("STEP 5: End-to-End Pipeline Test")
        self.log("="*80)
        
        cmd = ["python", str(self.test_pipeline_script)]
        success = self.run_command(cmd, "test_pipeline", self.log_dir / f"step5_end2end_{self.timestamp}.log")
        
        self.results["steps"]["5_end2end"] = {
            "success": success
        }
        
        return success
    
    def step6_csv(self):
        """Step 6: Generate CSV exports"""
        if not self.args.csv:
            self.log("\nStep 6: Skipped (--csv=no)")
            return True
        
        self.log("\n" + "="*80)
        self.log("STEP 6: Generate CSV Exports")
        self.log("="*80)
        
        # Find all IDS files in subdirectories
        ids_files = list(self.tmp_dir.glob("*/*.ids.json"))
        
        if not ids_files:
            self.log("✗ No IDS files found to export", "ERROR")
            return False
        
        self.log(f"Exporting {len(ids_files)} file(s) to CSV")
        
        all_success = True
        for ids_file in ids_files:
            cmd = ["python", str(self.convert_script), "--csv", str(ids_file)]
            success = self.run_command(
                cmd, 
                f"csv_export_{ids_file.stem}",
                self.log_dir / f"step6_csv_{ids_file.stem}_{self.timestamp}.log"
            )
            all_success = all_success and success
        
        self.results["steps"]["6_csv_export"] = {
            "success": all_success,
            "files": len(ids_files)
        }
        
        return all_success
    
    def save_results(self):
        """Save pipeline results to JSON"""
        results_file = self.log_dir / f"results_{self.timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        self.log(f"\nResults saved to: {results_file}")
    
    def print_summary(self):
        """Print pipeline summary"""
        self.log("\n" + "="*80)
        self.log("PIPELINE SUMMARY")
        self.log("="*80)
        
        self.log(f"Timestamp: {self.timestamp}")
        self.log(f"Files processed: {len(self.results['files_processed'])}")
        
        if self.results['files_processed']:
            for fname in self.results['files_processed']:
                self.log(f"  - {fname}")
        
        self.log(f"\nSteps executed:")
        for step_name, step_result in self.results["steps"].items():
            status = "✓" if step_result["success"] else "✗"
            self.log(f"  {status} {step_name}")
        
        if self.results["success"]:
            self.log("\n✓ PIPELINE COMPLETED SUCCESSFULLY")
        else:
            self.log("\n✗ PIPELINE FAILED", "ERROR")
        
        self.log(f"\nLogs saved to: {self.log_dir}")
        self.log("="*80)
    
    def run(self):
        """Execute the complete pipeline"""
        self.log("="*80)
        self.log("AKTA to IDS Pipeline Orchestrator")
        self.log("="*80)
        self.log(f"Workspace: {self.workspace_root}")
        self.log(f"Data directory: {self.data_dir}")
        self.log(f"Output directory: {self.tmp_dir}")
        self.log(f"Log directory: {self.log_dir}")
        
        # Clean if requested
        if self.args.clean:
            self.clean_outputs()
        
        # Execute pipeline steps
        steps = [
            self.step1_extract,
            self.step2_test_extraction,
            self.step3_convert,
            self.step4_validate,
            self.step5_end2end,
            self.step6_csv
        ]
        
        for step_func in steps:
            success = step_func()
            if not success:
                self.log(f"✗ Pipeline failed at {step_func.__name__}", "ERROR")
                self.results["success"] = False
                self.save_results()
                self.print_summary()
                return False
        
        # All steps succeeded
        self.results["success"] = True
        self.save_results()
        self.print_summary()
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="AKTA to IDS Pipeline Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--data-dir",
        default="data/akta",
        help="Data directory path with original AKTA .zip archives (default: data/akta)"
    )
    
    parser.add_argument(
        "--process-files",
        default="all",
        help="Files to process: 'all', 'none', or comma-separated list (default: all)"
    )
    
    parser.add_argument(
        "--log-dir",
        default="output/logs",
        help="Directory for all log files (default: output/logs)"
    )
    
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean all output dirs before starting (including .tmp and output)"
    )
    
    parser.add_argument(
        "--csv",
        action="store_true",
        default=True,
        help="Create CSV output (default: yes)"
    )
    
    parser.add_argument(
        "--no-csv",
        action="store_false",
        dest="csv",
        help="Skip CSV generation"
    )
    
    parser.add_argument(
        "--check-extraction",
        action="store_true",
        default=True,
        help="Carry out extraction coverage check (default: yes)"
    )
    
    parser.add_argument(
        "--no-check-extraction",
        action="store_false",
        dest="check_extraction",
        help="Skip extraction coverage check"
    )
    
    parser.add_argument(
        "--check-conversion",
        action="store_true",
        default=True,
        help="Carry out IDS conversion validation (default: yes)"
    )
    
    parser.add_argument(
        "--no-check-conversion",
        action="store_false",
        dest="check_conversion",
        help="Skip IDS conversion validation"
    )
    
    parser.add_argument(
        "--check-end2end",
        action="store_true",
        default=True,
        help="Carry out end-to-end pipeline test (default: yes)"
    )
    
    parser.add_argument(
        "--no-check-end2end",
        action="store_false",
        dest="check_end2end",
        help="Skip end-to-end pipeline test"
    )
    
    args = parser.parse_args()
    
    # Create and run orchestrator
    orchestrator = PipelineOrchestrator(args)
    success = orchestrator.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
