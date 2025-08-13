# txAdmin Recipe Processor

A Python tool that processes txAdmin recipe files (`.yaml`) and replicates the FiveM server folder structure locally by cloning repositories and downloading files.

## Overview

This tool reads `txAdminRecipe.yaml` files (the standard pattern for cloning files into a FiveM server) and recreates the exact folder structure locally without needing txAdmin. It handles:

- ✅ GitHub repository cloning (with specific branches/refs)
- ✅ File downloads (including releases and zip files)
- ✅ Zip file extraction
- ✅ Path moving/renaming operations
- ✅ Commented out sections (automatically skipped)
- ✅ Throttling/rate limiting
- ✅ Database operations (skipped - no database required)

## Installation

### Prerequisites

- Python 3.7 or higher
- Git (for cloning repositories)
- Make (optional, for using Makefile commands)

### Setup

The project automatically creates and manages a Python virtual environment to keep dependencies isolated:

```bash
# Navigate to the ref-folder directory
cd ref-folder/

# This will automatically:
# 1. Create a virtual environment (if not exists)
# 2. Install dependencies
# 3. Process the recipe
make

# Or just create the virtual environment and install dependencies:
make venv
```

## Usage

### Using Make (Recommended)

```bash
# Navigate to the ref-folder directory
cd ref-folder/

# Process recipe with default settings (creates venv if needed)
make

# Process with verbose output
make process-verbose

# Process to a custom directory
make process-custom DIR=/path/to/output

# Clean output directory
make clean

# Clean everything including virtual environment
make clean-all

# Clean and rebuild
make rebuild

# Show how to activate the virtual environment manually
make activate

# Show help
make help
```

### Using Python Directly

If you want to run the script directly, first activate the virtual environment:

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt

# Basic usage (uses default recipe file and output directory)
python txadmin_recipe_processor.py

# Specify custom recipe file
python txadmin_recipe_processor.py path/to/recipe.yaml

# Specify custom output directory
python txadmin_recipe_processor.py recipe.yaml -o /path/to/output

# Enable verbose mode
python txadmin_recipe_processor.py recipe.yaml -v

# When done, deactivate the virtual environment
deactivate
```

### Command Line Options

- `recipe` - Path to the txAdminRecipe.yaml file (default: `txAdminRecipe.yaml`)
- `-o, --output` - Output directory for server files (default: `../fivem-server`)
- `-v, --verbose` - Enable verbose output for debugging

## How It Works

1. **Parses YAML**: Reads and parses the txAdminRecipe.yaml file
2. **Processes Tasks**: Executes each task in sequence:
   - `download_github` - Clones GitHub repositories
   - `download_file` - Downloads files from URLs
   - `unzip` - Extracts zip archives
   - `move_path` - Moves/renames files and directories
   - `remove_path` - Removes files and directories
   - `waste_time` - Implements throttling delays
3. **Skips Database**: Automatically skips database-related actions
4. **Creates Structure**: Builds the exact folder structure as specified

## Features

### Supported Actions

| Action | Description | Status |
|--------|-------------|--------|
| `download_github` | Clone GitHub repositories with specific branches/refs | ✅ Supported |
| `download_file` | Download files from URLs | ✅ Supported |
| `unzip` | Extract zip archives | ✅ Supported |
| `move_path` | Move or rename files/directories | ✅ Supported |
| `remove_path` | Delete files/directories | ✅ Supported |
| `waste_time` | Throttling/rate limiting | ✅ Supported |
| `connect_database` | Database connection | ⏭️ Skipped |
| `query_database` | Database queries | ⏭️ Skipped |

### Smart Handling

- **Commented Sections**: Automatically detects and skips commented-out tasks in the YAML
- **Subpaths**: Supports downloading only specific subdirectories from repositories
- **Error Recovery**: Continues processing even if individual tasks fail
- **Cleanup**: Automatically cleans up temporary files after processing
- **Progress Tracking**: Shows real-time progress and final statistics

## Example Output Structure

After processing, the script will create a `fivem-server/` folder in the parent directory with the structure:
```
../fivem-server/
├── resources/
│   ├── [cfx-default]/
│   ├── [standalone]/
│   ├── [voice]/
│   ├── [qbx]/
│   ├── [ox]/
│   ├── [npwd]/
│   ├── [mri]/
│   └── [addons]/
├── server.cfg
├── permissions.cfg
└── ox.cfg
```

## Troubleshooting

### Common Issues

1. **Git not found**: Ensure Git is installed and in your PATH
2. **Permission denied**: Run with appropriate permissions or use sudo if needed
3. **Network errors**: Check internet connection and GitHub access
4. **Rate limiting**: The tool includes automatic throttling, but you may need to wait if hitting API limits

### Verbose Mode

Enable verbose mode (`-v`) to see detailed logs of what the tool is doing:
```bash
python3 txadmin_recipe_processor.py recipe.yaml -v
```

## Virtual Environment

The project uses a Python virtual environment to isolate dependencies:

- **Automatic Creation**: Running `make` or `make venv` will automatically create a virtual environment if it doesn't exist
- **Location**: The virtual environment is created in the `venv/` directory within `ref-folder/`
- **Dependencies**: All required packages are installed within the virtual environment
- **Cleanup**: Use `make clean-all` to remove both the output and the virtual environment

## Notes

- The tool creates a temporary directory for downloads that is automatically cleaned up
- Existing files/directories in the output path will be overwritten
- Database-related actions are automatically skipped (no database required)
- The `.git` directories are removed from cloned repos to save space
- A Python virtual environment is automatically created to keep dependencies isolated

## License

This tool is provided as-is for processing txAdmin recipe files locally. 