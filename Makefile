# txAdmin Recipe Processor Makefile
# Process txAdminRecipe.yaml files and replicate folder structure locally

# Virtual environment settings
VENV_DIR := venv
VENV_PYTHON := $(VENV_DIR)/bin/python
VENV_PIP := $(VENV_DIR)/bin/pip

# Check if venv exists, use it if available, otherwise use system python
ifeq ($(wildcard $(VENV_PYTHON)),)
	PYTHON := python3
	PIP := python3 -m pip
else
	PYTHON := $(VENV_PYTHON)
	PIP := $(VENV_PIP)
endif

RECIPE_FILE := txAdminRecipe.yaml
OUTPUT_DIR := ../fivem-server
SCRIPT := txadmin_recipe_processor.py

# Default target - ensure venv exists and process
.PHONY: all
all: venv process

# Create virtual environment if it doesn't exist
.PHONY: venv
venv:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating Python virtual environment..."; \
		python3 -m venv $(VENV_DIR); \
		echo "Virtual environment created at $(VENV_DIR)"; \
		$(VENV_PIP) install --upgrade pip; \
		$(VENV_PIP) install -r requirements.txt; \
		echo "Dependencies installed in virtual environment"; \
	else \
		echo "Virtual environment already exists at $(VENV_DIR)"; \
	fi

# Install dependencies (creates venv if needed)
.PHONY: install
install: venv
	@echo "Installing/updating dependencies..."
	@$(PIP) install -r requirements.txt

# Process the recipe file
.PHONY: process
process: venv
	@echo "Processing txAdmin recipe..."
	@$(PYTHON) $(SCRIPT) $(RECIPE_FILE) -o $(OUTPUT_DIR)

# Process with verbose output
.PHONY: process-verbose
process-verbose: venv
	@echo "Processing txAdmin recipe (verbose mode)..."
	@$(PYTHON) $(SCRIPT) $(RECIPE_FILE) -o $(OUTPUT_DIR) -v

# Process to a custom directory
.PHONY: process-custom
process-custom: venv
	@if [ -z "$(DIR)" ]; then \
		echo "Error: Please specify DIR=<output_directory>"; \
		exit 1; \
	fi
	@echo "Processing txAdmin recipe to $(DIR)..."
	@$(PYTHON) $(SCRIPT) $(RECIPE_FILE) -o $(DIR)

# Clean the output directory
.PHONY: clean
clean:
	@echo "Cleaning output directory..."
	@rm -rf $(OUTPUT_DIR)
	@echo "Cleaned $(OUTPUT_DIR)"

# Clean everything including virtual environment
.PHONY: clean-all
clean-all: clean
	@echo "Removing virtual environment..."
	@rm -rf $(VENV_DIR)
	@echo "Removed virtual environment"

# Clean and process
.PHONY: rebuild
rebuild: clean process

# Activate virtual environment (for manual use)
.PHONY: activate
activate:
	@echo "To activate the virtual environment, run:"
	@echo "  source $(VENV_DIR)/bin/activate"
	@echo ""
	@echo "To deactivate, run:"
	@echo "  deactivate"

# Show help
.PHONY: help
help:
	@echo "txAdmin Recipe Processor - Make Targets"
	@echo "========================================"
	@echo ""
	@echo "Available targets:"
	@echo "  make                  - Create venv (if needed) and process recipe"
	@echo "  make venv             - Create Python virtual environment"
	@echo "  make install          - Install/update Python dependencies"
	@echo "  make process          - Process the recipe file"
	@echo "  make process-verbose  - Process with verbose output"
	@echo "  make process-custom DIR=<path> - Process to custom directory"
	@echo "  make clean            - Remove the output directory"
	@echo "  make clean-all        - Remove output and virtual environment"
	@echo "  make rebuild          - Clean and process again"
	@echo "  make activate         - Show how to activate the venv"
	@echo "  make help             - Show this help message"
	@echo ""
	@echo "Configuration:"
	@echo "  Recipe file: $(RECIPE_FILE)"
	@echo "  Output dir:  $(OUTPUT_DIR)"
	@echo ""
	@echo "Examples:"
	@echo "  make                  - Process recipe to default location"
	@echo "  make process-verbose  - Process with detailed output"
	@echo "  make process-custom DIR=/opt/fivem - Process to /opt/fivem" 