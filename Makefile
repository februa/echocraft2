.PHONY: install test lint format clean all help

# Project root
PROJECT_ROOT := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

# Python tools
PYTHON_TOOLS := ec_source_nb ec_noise ec_propagate ec_array ec_sample ec_beamform ec_to_wav eca_spectrum eca_integrate eca_peak_freq eca_snr

# PYTHONPATH for tests and running
export PYTHONPATH := $(PROJECT_ROOT)/lib:$(PROJECT_ROOT)/tools/ec_source_nb:$(PROJECT_ROOT)/tools/ec_noise:$(PROJECT_ROOT)/tools/ec_propagate:$(PROJECT_ROOT)/tools/ec_array:$(PROJECT_ROOT)/tools/ec_sample:$(PROJECT_ROOT)/tools/ec_beamform:$(PROJECT_ROOT)/tools/ec_to_wav:$(PROJECT_ROOT)/tools/eca_spectrum:$(PROJECT_ROOT)/tools/eca_integrate:$(PROJECT_ROOT)/tools/eca_peak_freq:$(PROJECT_ROOT)/tools/eca_snr

help:
	@echo "ECHOCRAFT Makefile Targets:"
	@echo ""
	@echo "  make install    Install all Python tools in editable mode"
	@echo "  make test       Run tests for all tools"
	@echo "  make lint       Run ruff linter on all tools"
	@echo "  make format     Format code with ruff"
	@echo "  make clean      Remove build artifacts, __pycache__, .pyc files"
	@echo "  make all        Run install target (default)"
	@echo ""

# Install all Python tools in editable mode
install:
	@echo "Installing ECHOCRAFT tools..."
	@for tool in $(PYTHON_TOOLS); do \
		echo "Installing tools/$$tool ..."; \
		pip install -e "$(PROJECT_ROOT)/tools/$$tool" || exit 1; \
	done
	@echo "Installation complete!"

# Run pytest on all tests
test:
	@echo "Running tests..."
	PYTHONPATH=$(PYTHONPATH) pytest $(PROJECT_ROOT)/tools/*/tests/ -v

# Lint all Python files using ruff
lint:
	@echo "Running ruff linter..."
	ruff check $(PROJECT_ROOT)/tools $(PROJECT_ROOT)/lib

# Format all Python files using ruff
format:
	@echo "Formatting with ruff..."
	ruff format $(PROJECT_ROOT)/tools $(PROJECT_ROOT)/lib

# Clean up build artifacts
clean:
	@echo "Cleaning build artifacts..."
	find $(PROJECT_ROOT) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find $(PROJECT_ROOT) -type f -name "*.pyc" -delete
	find $(PROJECT_ROOT) -type f -name "*.pyo" -delete
	find $(PROJECT_ROOT) -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find $(PROJECT_ROOT) -type d -name build -exec rm -rf {} + 2>/dev/null || true
	find $(PROJECT_ROOT) -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete!"

# Default target
all: install

.DEFAULT_GOAL := all
