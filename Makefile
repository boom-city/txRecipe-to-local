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
OUTPUT_DIR := ./fivem-server-dry-run
SCRIPT := src/main.py

# Default target - ensure venv exists and clone
.PHONY: all
all: prepare clone

# Create virtual environment and install requirements
.PHONY: prepare
prepare:
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

# Alias for prepare (backward compatibility)
.PHONY: install
install: prepare

# Run the entire script (clone mode)
.PHONY: clone
clone: prepare
	@echo "Cloning repositories from txAdmin recipe..."
	@$(PYTHON) $(SCRIPT) $(RECIPE_FILE) -o $(OUTPUT_DIR)

# Create folder structure without cloning repos
.PHONY: dry-run
dry-run: prepare
	@echo "Creating folder structure (dry-run mode)..."
	@$(PYTHON) $(SCRIPT) $(RECIPE_FILE) -o $(OUTPUT_DIR) --dry-run

# Clone with verbose output
.PHONY: clone-verbose
clone-verbose: prepare
	@echo "Cloning repositories (verbose mode)..."
	@$(PYTHON) $(SCRIPT) $(RECIPE_FILE) -o $(OUTPUT_DIR) -v

# Clean with multiple options
.PHONY: clean
clean:
	@if echo "$(MAKECMDGOALS)" | grep -q "\--artifacts"; then \
		echo "Cleaning artifacts (helper dotfiles)..."; \
		find $(OUTPUT_DIR) -name ".*" -type f 2>/dev/null | head -10 | while read f; do rm -f "$$f" && echo "Removed: $$f"; done; \
		find $(OUTPUT_DIR) -name "*.tmp" -o -name "*.log" 2>/dev/null | head -10 | while read f; do rm -f "$$f" && echo "Removed: $$f"; done; \
	elif echo "$(MAKECMDGOALS)" | grep -q "\--git"; then \
		echo "Removing .git folders..."; \
		find $(OUTPUT_DIR) -name ".git" -type d 2>/dev/null | while read d; do rm -rf "$$d" && echo "Removed: $$d"; done; \
	elif echo "$(MAKECMDGOALS)" | grep -q "\--reset"; then \
		echo "Resetting - cleaning all created files..."; \
		rm -rf $(OUTPUT_DIR) && echo "Removed: $(OUTPUT_DIR)"; \
	else \
		echo "Cleaning output directory..."; \
		rm -rf $(OUTPUT_DIR) && echo "Cleaned: $(OUTPUT_DIR)"; \
	fi

# Clean everything including virtual environment
.PHONY: clean-all
clean-all:
	@echo "Removing virtual environment..."
	@rm -rf $(VENV_DIR)
	@echo "Removed virtual environment"
	@$(MAKE) clean --reset

# Clean and clone
.PHONY: rebuild
rebuild:
	@$(MAKE) clean --reset
	@$(MAKE) clone

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
	@echo "  make                  - Create venv (if needed) and clone repositories"
	@echo "  make prepare          - Create .venv folder, activate and install requirements"
	@echo "  make dry-run          - Create folder structure without cloning repos"
	@echo "  make clone            - Run the entire script (download and clone)"
	@echo "  make clone-verbose    - Clone with verbose output"
	@echo "  make clean            - Remove output directory (no args) or use:"
	@echo "                          --artifacts (remove helper dotfiles)"
	@echo "                          --git (remove .git folders)"
	@echo "                          --reset (remove all created files)"
	@echo "  make clean-all        - Remove output and virtual environment"
	@echo "  make rebuild          - Clean --reset and clone again"
	@echo "  make activate         - Show how to activate the venv"
	@echo "  make help             - Show this help message"
	@echo ""
	@echo "Configuration:"
	@echo "  Recipe file: $(RECIPE_FILE)"
	@echo "  Output dir:  $(OUTPUT_DIR)"
	@echo ""
	@echo "Examples:"
	@echo "  make dry-run          - Create folder structure only"
	@echo "  make clone            - Download and clone all repositories"
	@echo "  make clean --artifacts - Remove helper dotfiles"
	@echo "  make clean --git      - Remove .git folders from cloned repos"
	@echo "  make clean --reset    - Reset everything for fresh start"

# Allow arguments to be passed to clean command
--artifacts --git --reset:
	@: 