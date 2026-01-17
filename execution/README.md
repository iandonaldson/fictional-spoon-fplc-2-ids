# Execution Scripts

This directory contains deterministic Python scripts that handle specific tasks.

## Guidelines

- Scripts must be reliable and testable
- Use `.env` for credentials and configuration
- Add comprehensive error handling
- Include docstrings and comments
- Each script should do one thing well

## Before Creating New Scripts

1. Check if a suitable script already exists
2. Consider if existing scripts can be extended
3. Only create new scripts if truly needed

## Best Practices

- Use virtual environments for dependencies
- Follow PEP 8 style guidelines
- Handle exceptions gracefully
- Log important operations
- Return structured outputs (JSON when possible)

## Example Script Structure

```python
"""
Module description

Usage:
    python script_name.py [arguments]
"""

import os
from dotenv import load_dotenv

load_dotenv()

def main():
    """Main function"""
    # Implementation
    pass

if __name__ == "__main__":
    main()
```
