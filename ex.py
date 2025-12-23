Framework Architecture Overview

📁 Recommended Folder Structure
docreader-automation/
│
├── .gitlab/                              # GitLab specific configurations
│   └── merge_request_templates/
│       └── default.md
│
├── .gitlab-ci.yml                        # CI/CD Pipeline configuration
│
├── config/                               # Environment configurations
│   ├── __init__.py
│   ├── qa.yaml
│   ├── prod.yaml
│   └── config_manager.py
│
├── resources/                            # Robot Framework resources
│   ├── keywords/                         # Custom keyword libraries
│   │   ├── dashboard_keywords.robot
│   │   ├── upload_keywords.robot
│   │   ├── detail_view_keywords.robot
│   │   ├── labelling_keywords.robot
│   │   └── common_keywords.robot
│   │
│   ├── locators/                         # Page object locators
│   │   ├── dashboard_locators.robot
│   │   ├── upload_locators.robot
│   │   ├── detail_view_locators.robot
│   │   └── labelling_locators.robot
│   │
│   └── variables/                        # Test data variables
│       ├── common_variables.robot
│       └── test_data.robot
│
├── libraries/                            # Python custom libraries
│   ├── __init__.py
│   ├── aws_helper.py                     # AWS S3, Textract interactions
│   ├── database_helper.py                # Database operations
│   ├── pdf_helper.py                     # PDF validation/operations
│   ├── api_helper.py                     # API testing support
│   └── report_generator.py               # Custom reporting
│
├── tests/                                # Test suites
│   ├── smoke/
│   │   └── smoke_test.robot
│   ├── functional/
│   │   ├── dashboard_tests.robot
│   │   ├── upload_tests.robot
│   │   ├── processing_tests.robot
│   │   └── labelling_tests.robot
│   ├── integration/
│   │   ├── aws_integration_tests.robot
│   │   └── end_to_end_tests.robot
│   └── regression/
│       └── regression_suite.robot
│
├── test_data/                            # Test files and data
│   ├── valid_pdfs/
│   ├── invalid_pdfs/
│   └── expected_outputs/
│
├── results/                              # Test execution results (git-ignored)
│   ├── qa/
│   └── prod/
│
├── utils/                                # Utility scripts
│   ├── setup_env.sh
│   ├── clean_results.sh
│   └── generate_report.py
│
├── .pre-commit-config.yaml              # Pre-commit hooks configuration
├── .robocop                             # Robocop configuration
├── .gitignore
├── requirements.txt                     # Python dependencies
├── requirements-dev.txt                 # Development dependencies
├── Makefile                             # Common commands
├── README.md                            # Framework documentation
├── pyproject.toml                       # Python project configuration
└── setup.py                             # Package setup

🔧 Configuration Files
1. requirements.txt
txt# Core Framework
robotframework==7.0
robotframework-seleniumlibrary==6.2.0
robotframework-requests==0.9.6
robotframework-databaselibrary==1.3.0
robotframework-pabot==2.17.0

# AWS Integration
boto3==1.34.0
botocore==1.34.0

# PDF Processing
PyPDF2==3.0.1
pdf2image==1.16.3
Pillow==10.2.0

# Database
pymysql==1.1.0
psycopg2-binary==2.9.9

# Utilities
pyyaml==6.0.1
python-dotenv==1.0.0
openpyxl==3.1.2
Faker==22.0.0

# Web Drivers
webdriver-manager==4.0.1
selenium==4.16.0
2. requirements-dev.txt
txt# Code Quality
robotframework-robocop==5.0.0
robotframework-tidy==4.11.0
pre-commit==3.6.0
pylint==3.0.3
black==23.12.1
flake8==7.0.0
isort==5.13.2

# Testing
pytest==7.4.4
pytest-cov==4.1.0
coverage==7.4.0

# Documentation
sphinx==7.2.6
sphinx-rtd-theme==2.0.0
3. .gitlab-ci.yml
yaml# dOCReader Test Automation CI/CD Pipeline

stages:
  - quality
  - test-qa
  - test-prod
  - report

variables:
  ROBOT_OPTIONS: "--maxerrorlines 1 --loglevel INFO"
  PYTHON_VERSION: "3.11"
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

# Cache configuration
cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - .cache/pip
    - venv/

# Templates
.setup_template: &setup_env
  before_script:
    - python${PYTHON_VERSION} -m venv venv
    - source venv/bin/activate
    - pip install --upgrade pip
    - pip install -r requirements.txt
    - pip install -r requirements-dev.txt

# ====================
# STAGE 1: Code Quality
# ====================

code-quality:
  stage: quality
  image: python:${PYTHON_VERSION}
  <<: *setup_env
  script:
    - echo "🔍 Running Code Quality Checks..."
    
    # Python Linting
    - echo "📋 Running Pylint..."
    - pylint libraries/ --fail-under=8.0 --exit-zero
    
    # Python Code Formatting
    - echo "🎨 Checking Black formatting..."
    - black --check libraries/ utils/
    
    # Import Sorting
    - echo "📦 Checking import order..."
    - isort --check-only libraries/ utils/
    
    # Flake8
    - echo "✅ Running Flake8..."
    - flake8 libraries/ utils/ --max-line-length=120
    
  allow_failure: false
  only:
    - merge_requests
    - main
    - develop

robocop-check:
  stage: quality
  image: python:${PYTHON_VERSION}
  <<: *setup_env
  script:
    - echo "🤖 Running Robocop checks..."
    - robocop --reports all --configure return_status:quality_gate:W=30:E=0 resources/ tests/
    
  artifacts:
    when: always
    paths:
      - .robocop_cache/
    reports:
      junit: .robocop_cache/robocop.xml
    expire_in: 7 days
  allow_failure: false
  only:
    - merge_requests
    - main
    - develop

robot-tidy:
  stage: quality
  image: python:${PYTHON_VERSION}
  <<: *setup_env
  script:
    - echo "🧹 Running Robot Tidy..."
    - robotidy --check --diff resources/ tests/
  allow_failure: true
  only:
    - merge_requests

# ====================
# STAGE 2: QA Testing
# ====================

.test_template: &test_template
  image: python:${PYTHON_VERSION}
  <<: *setup_env
  artifacts:
    when: always
    paths:
      - results/${ENV}/
      - results/${ENV}/log.html
      - results/${ENV}/report.html
      - results/${ENV}/output.xml
    reports:
      junit: results/${ENV}/xunit.xml
    expire_in: 30 days

smoke-tests-qa:
  stage: test-qa
  <<: *test_template
  variables:
    ENV: "qa"
  script:
    - echo "🔥 Running Smoke Tests on QA Environment..."
    - robot 
        --outputdir results/qa
        --variable ENV:qa
        --variable CONFIG_FILE:config/qa.yaml
        --include smoke
        --xunit xunit.xml
        ${ROBOT_OPTIONS}
        tests/smoke/
  only:
    - merge_requests
    - develop
  environment:
    name: qa
    url: https://docreader-qa.siemens-energy.com

functional-tests-qa:
  stage: test-qa
  <<: *test_template
  variables:
    ENV: "qa"
  script:
    - echo "🧪 Running Functional Tests on QA..."
    - robot 
        --outputdir results/qa
        --variable ENV:qa
        --variable CONFIG_FILE:config/qa.yaml
        --include functional
        --exclude wip
        --xunit xunit.xml
        ${ROBOT_OPTIONS}
        tests/functional/
  only:
    - develop
    - /^release\/.*$/
  needs: ["smoke-tests-qa"]
  environment:
    name: qa

parallel-tests-qa:
  stage: test-qa
  <<: *test_template
  variables:
    ENV: "qa"
  script:
    - echo "⚡ Running Tests in Parallel on QA..."
    - pabot 
        --processes 4
        --outputdir results/qa
        --variable ENV:qa
        --variable CONFIG_FILE:config/qa.yaml
        --exclude slow
        ${ROBOT_OPTIONS}
        tests/functional/
  only:
    - schedules
  environment:
    name: qa

# ====================
# STAGE 3: Production Testing
# ====================

smoke-tests-prod:
  stage: test-prod
  <<: *test_template
  variables:
    ENV: "prod"
  script:
    - echo "🔥 Running Smoke Tests on Production..."
    - robot 
        --outputdir results/prod
        --variable ENV:prod
        --variable CONFIG_FILE:config/prod.yaml
        --include smoke
        --include critical
        --xunit xunit.xml
        ${ROBOT_OPTIONS}
        tests/smoke/
  only:
    - main
    - tags
  when: manual
  environment:
    name: production
    url: https://docreader.siemens-energy.com

regression-tests-prod:
  stage: test-prod
  <<: *test_template
  variables:
    ENV: "prod"
  script:
    - echo "🔄 Running Regression Tests on Production..."
    - robot 
        --outputdir results/prod
        --variable ENV:prod
        --variable CONFIG_FILE:config/prod.yaml
        --include regression
        --exclude flaky
        --xunit xunit.xml
        ${ROBOT_OPTIONS}
        tests/regression/
  only:
    - schedules
  environment:
    name: production

# ====================
# STAGE 4: Reporting
# ====================

generate-report:
  stage: report
  image: python:${PYTHON_VERSION}
  <<: *setup_env
  script:
    - echo "📊 Generating Test Reports..."
    - python utils/generate_report.py --env ${ENV}
  artifacts:
    when: always
    paths:
      - results/${ENV}/consolidated_report.html
      - results/${ENV}/metrics.json
    expire_in: 90 days
  only:
    - develop
    - main

# Merge multiple test results
merge-results:
  stage: report
  image: python:${PYTHON_VERSION}
  <<: *setup_env
  script:
    - echo "🔗 Merging Test Results..."
    - rebot 
        --outputdir results/merged
        --name "Combined Results"
        --merge
        results/qa/output.xml results/prod/output.xml || true
  artifacts:
    when: always
    paths:
      - results/merged/
    expire_in: 90 days
  only:
    - schedulesOrchestrated comprehensive framework architecture with modular components.This is getting long. Let me continue with more configuration files that are essential for the framework.4. .pre-commit-config.yaml
yaml# Pre-commit hooks configuration
repos:
  # Python code formatting
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11
        files: ^(libraries|utils)/.*\.py$

  # Import sorting
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: ["--profile", "black"]
        files: ^(libraries|utils)/.*\.py$

  # Python linting
  - repo: https://github.com/pycqa/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ["--max-line-length=120", "--ignore=E203,W503"]
        files: ^(libraries|utils)/.*\.py$

  # Robot Framework linting
  - repo: https://github.com/MarketSquare/robotframework-robocop
    rev: v5.0.0
    hooks:
      - id: robocop
        args: ["--configure", "return_status:quality_gate:W=30:E=0"]
        files: ^(resources|tests)/.*\.robot$

  # Robot Framework formatting
  - repo: https://github.com/MarketSquare/robotframework-tidy
    rev: 4.11.0
    hooks:
      - id: robotidy
        files: ^(resources|tests)/.*\.robot$

  # General file checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-merge-conflict
      - id: detect-private-key

  # Commit message validation
  - repo: https://github.com/commitizen-tools/commitizen
    rev: 3.13.0
    hooks:
      - id: commitizen
        stages: [commit-msg]
5. .robocop
ini# Robocop configuration for Robot Framework code quality

[tool.robocop]
# General settings
include = 
exclude = 

# Severity thresholds
return_status = quality_gate:W=30:E=0

# Rule configuration
configure = 
    line-too-long:line_length:120
    too-many-calls-in-keyword:max_calls:15
    too-few-calls-in-keyword:min_calls:1
    too-many-calls-in-test-case:max_calls:20

# Disabled rules
exclude = 
    missing-doc-keyword
    missing-doc-test-case
    missing-doc-suite

# Reports
reports = all
output = .robocop_cache/robocop.xml
6. Makefile
makefile# dOCReader Automation Framework Makefile

.PHONY: help setup install install-dev clean test test-qa test-prod test-smoke test-parallel format lint robocop pre-commit

# Variables
PYTHON := python3.11
PIP := $(PYTHON) -m pip
ROBOT := robot
VENV := venv
ENV ?= qa

help:
	@echo "dOCReader Test Automation Framework"
	@echo "===================================="
	@echo ""
	@echo "Available targets:"
	@echo "  setup          - Create virtual environment"
	@echo "  install        - Install production dependencies"
	@echo "  install-dev    - Install development dependencies"
	@echo "  clean          - Remove generated files and cache"
	@echo "  test           - Run all tests for specified ENV (default: qa)"
	@echo "  test-smoke     - Run smoke tests"
	@echo "  test-qa        - Run tests on QA environment"
	@echo "  test-prod      - Run tests on Production environment"
	@echo "  test-parallel  - Run tests in parallel"
	@echo "  format         - Format Python and Robot code"
	@echo "  lint           - Run all linters"
	@echo "  robocop        - Run Robocop checks"
	@echo "  pre-commit     - Install pre-commit hooks"
	@echo "  report         - Generate custom test report"
	@echo ""
	@echo "Example: make test ENV=qa"

setup:
	@echo "🔧 Setting up virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "✅ Virtual environment created. Activate with: source venv/bin/activate"

install: setup
	@echo "📦 Installing production dependencies..."
	. $(VENV)/bin/activate && $(PIP) install --upgrade pip
	. $(VENV)/bin/activate && $(PIP) install -r requirements.txt
	@echo "✅ Production dependencies installed"

install-dev: install
	@echo "📦 Installing development dependencies..."
	. $(VENV)/bin/activate && $(PIP) install -r requirements-dev.txt
	@echo "✅ Development dependencies installed"

clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".robocop_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf results/* || true
	@echo "✅ Cleanup complete"

test:
	@echo "🧪 Running tests on $(ENV) environment..."
	. $(VENV)/bin/activate && $(ROBOT) \
		--outputdir results/$(ENV) \
		--variable ENV:$(ENV) \
		--variable CONFIG_FILE:config/$(ENV).yaml \
		--xunit xunit.xml \
		tests/

test-smoke:
	@echo "🔥 Running smoke tests on $(ENV)..."
	. $(VENV)/bin/activate && $(ROBOT) \
		--outputdir results/$(ENV)/smoke \
		--variable ENV:$(ENV) \
		--variable CONFIG_FILE:config/$(ENV).yaml \
		--include smoke \
		tests/smoke/

test-qa:
	@$(MAKE) test ENV=qa

test-prod:
	@$(MAKE) test ENV=prod

test-parallel:
	@echo "⚡ Running tests in parallel on $(ENV)..."
	. $(VENV)/bin/activate && pabot \
		--processes 4 \
		--outputdir results/$(ENV)/parallel \
		--variable ENV:$(ENV) \
		--variable CONFIG_FILE:config/$(ENV).yaml \
		tests/

format:
	@echo "🎨 Formatting code..."
	. $(VENV)/bin/activate && black libraries/ utils/
	. $(VENV)/bin/activate && isort libraries/ utils/
	. $(VENV)/bin/activate && robotidy resources/ tests/
	@echo "✅ Code formatted"

lint:
	@echo "🔍 Running linters..."
	. $(VENV)/bin/activate && pylint libraries/ utils/ --fail-under=8.0 || true
	. $(VENV)/bin/activate && flake8 libraries/ utils/ --max-line-length=120
	. $(VENV)/bin/activate && black --check libraries/ utils/
	. $(VENV)/bin/activate && isort --check-only libraries/ utils/
	@echo "✅ Linting complete"

robocop:
	@echo "🤖 Running Robocop checks..."
	. $(VENV)/bin/activate && robocop --reports all resources/ tests/
	@echo "✅ Robocop checks complete"

pre-commit:
	@echo "🪝 Installing pre-commit hooks..."
	. $(VENV)/bin/activate && pre-commit install
	. $(VENV)/bin/activate && pre-commit install --hook-type commit-msg
	@echo "✅ Pre-commit hooks installed"

report:
	@echo "📊 Generating custom report..."
	. $(VENV)/bin/activate && $(PYTHON) utils/generate_report.py --env $(ENV)
	@echo "✅ Report generated"

.DEFAULT_GOAL := help
7. config/qa.yaml
yaml# QA Environment Configuration

environment:
  name: "QA"
  url: "https://docreader-qa.siemens-energy.com"
  api_url: "https://api-docreader-qa.siemens-energy.com"

credentials:
  username: "${QA_USERNAME}"
  password: "${QA_PASSWORD}"
  api_key: "${QA_API_KEY}"

database:
  host: "db-qa.siemens-energy.com"
  port: 5432
  name: "docreader_qa"
  username: "${DB_QA_USERNAME}"
  password: "${DB_QA_PASSWORD}"

aws:
  region: "us-east-1"
  s3_bucket: "docreader-qa-storage"
  textract_enabled: true
  sagemaker_endpoint: "docreader-qa-ml-model"
  access_key_id: "${AWS_QA_ACCESS_KEY}"
  secret_access_key: "${AWS_QA_SECRET_KEY}"

test_data:
  upload_path: "test_data/valid_pdfs/"
  max_file_size_mb: 50
  max_pages: 150

timeouts:
  page_load: 30
  upload: 120
  processing: 600
  api_response: 10

browser:
  name: "chrome"
  headless: true
  window_size: "1920x1080"
  implicit_wait: 5

retry:
  max_attempts: 3
  delay_seconds: 2

logging:
  level: "INFO"
  console_output: true
  file_output: true

reporting:
  screenshot_on_failure: true
  video_recording: false
8. config/prod.yaml
yaml# Production Environment Configuration

environment:
  name: "PRODUCTION"
  url: "https://docreader.siemens-energy.com"
  api_url: "https://api-docreader.siemens-energy.com"

credentials:
  username: "${PROD_USERNAME}"
  password: "${PROD_PASSWORD}"
  api_key: "${PROD_API_KEY}"

database:
  host: "db-prod.siemens-energy.com"
  port: 5432
  name: "docreader_prod"
  username: "${DB_PROD_USERNAME}"
  password: "${DB_PROD_PASSWORD}"

aws:
  region: "us-east-1"
  s3_bucket: "docreader-prod-storage"
  textract_enabled: true
  sagemaker_endpoint: "docreader-prod-ml-model"
  access_key_id: "${AWS_PROD_ACCESS_KEY}"
  secret_access_key: "${AWS_PROD_SECRET_KEY}"

test_data:
  upload_path: "test_data/valid_pdfs/"
  max_file_size_mb: 50
  max_pages: 150

timeouts:
  page_load: 30
  upload: 120
  processing: 600
  api_response: 10

browser:
  name: "chrome"
  headless: true
  window_size: "1920x1080"
  implicit_wait: 5

retry:
  max_attempts: 2
  delay_seconds: 3

logging:
  level: "WARNING"
  console_output: false
  file_output: true

reporting:
  screenshot_on_failure: true
  video_recording: true

📝 Sample Framework Files
9. config/config_manager.py
python"""Configuration Manager for environment-specific settings."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    """Manages configuration loading and environment variables."""

    def __init__(self, config_file: str = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration YAML file
        """
        self.config_file = config_file or os.getenv('CONFIG_FILE', 'config/qa.yaml')
        self.config = self._load_config()
        self._substitute_env_vars()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_path = Path(self.config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)

    def _substitute_env_vars(self):
        """Replace environment variable placeholders in config."""
        self._recursive_substitute(self.config)

    def _recursive_substitute(self, obj):
        """Recursively substitute environment variables."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                obj[key] = self._recursive_substitute(value)
        elif isinstance(obj, list):
            return [self._recursive_substitute(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
            env_var = obj[2:-1]
            return os.getenv(env_var, obj)
        return obj

    def get(self, key_path: str, default=None):
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Dot-separated path to config value (e.g., 'database.host')
            default: Default value if key not found
        
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value

    def get_env_name(self) -> str:
        """Get current environment name."""
        return self.get('environment.name', 'UNKNOWN')

    def get_base_url(self) -> str:
        """Get base application URL."""
        return self.get('environment.url')

    def get_credentials(self) -> Dict[str, str]:
        """Get login credentials."""
        return {
            'username': self.get('credentials.username'),
            'password': self.get('credentials.password')
        }


# Global instance
_config_instance = None


def get_config(config_file: str = None) -> ConfigManager:
    """Get or create global configuration instance."""
    global _config_instance
    if _config_instance is None or config_file:
        _config_instance = ConfigManager(config_file)
    return _config_instance
10. resources/keywords/common_keywords.robot
robotframework*** Settings ***
Documentation    Common keywords used across the application
Library          SeleniumLibrary
Library          Collections
Library          String
Library          OperatingSystem
Library          ../../libraries/pdf_helper.py
Variables        ../../config/config_manager.py

*** Variables ***
${BROWSER}              chrome
${IMPLICIT_WAIT}        10s
${PAGE_LOAD_TIMEOUT}    30s

*** Keywords ***
Open dOCReader Application
    [Documentation]    Opens the dOCReader application in browser
    [Arguments]    ${environment}=qa
    
    ${config}=    Load Config    ${environment}
    ${base_url}=    Get From Dictionary    ${config}    base_url
    
    Open Browser    ${base_url}    ${BROWSER}
    Maximize Browser Window
    Set Selenium Implicit Wait    ${IMPLICIT_WAIT}
    Set Selenium Timeout    ${PAGE_LOAD_TIMEOUT}
    
    Log    Opened dOCReader application: ${base_url}    INFO

Login To Application
    [Documentation]    Performs login with credentials
    [Arguments]    ${username}    ${password}
    
    Wait Until Page Contains Element    id=username    timeout=10s
    Input Text    id=username    ${username}
    Input Password    id=password    ${password}
    Click Button    id=loginButton
    
    Wait Until Page Contains Element    xpath=//h1[contains(text(),'Dashboard')]    timeout=15s
    Log    Successfully logged in as ${username}    INFO

Close Application
    [Documentation]    Closes browser and cleans up
    Capture Page Screenshot
    Close All Browsers
    Log    Application closed    INFO

Wait For Element And Click
    [Documentation]    Waits for element and clicks it
    [Arguments]    ${locator}    ${timeout}=10s
    
    Wait Until Element Is Visible    ${locator}    timeout=${timeout}
    Wait Until Element Is Enabled    ${locator}    timeout=${timeout}
    Click Element    ${locator}
    Sleep    0.5s

Wait For Processing To Complete
    [Documentation]    Waits for document processing with status checks
    [Arguments]    ${document_id}    ${max_wait_time}=600s
    
    ${start_time}=    Get Time    epoch
    ${timeout}=    Evaluate    ${start_time} + ${max_wait_time}
    
    FOR    ${i}    IN RANGE    999999
        ${current_time}=    Get Time    epoch
        Exit For Loop If    ${current_time} > ${timeout}
        
        ${status}=    Get Document Status    ${document_id}
        Exit For Loop If    '${status}' == 'Ready To Export'
        Exit For Loop If    '${status}' == 'Processing Failed'
        
        Sleep    5s
        Reload Page
    END
    
    ${final_status}=    Get Document Status    ${document_id}
    Should Be Equal    ${final_status}    Ready To Export
    Log    Document ${document_id} processing completed    INFO

Verify Page Title Contains
    [Documentation]    Verifies page title contains expected text
    [Arguments]    ${expected_text}
    
    ${title}=    Get Title
    Should Contain    ${title}    ${expected_text}    ignore_case=True
    Log    Page title verified: ${title}    INFO

Take Screenshot On Failure
    [Documentation]    Custom keyword to capture screenshots on failure
    Run Keyword If Test Failed    Capture Page Screenshot
11. tests/smoke/smoke_test.robot
robotframework*** Settings ***
Documentation    Smoke test suite to verify basic application functionality
...              This suite should run quickly and verify critical paths
Resource         ../../resources/keywords/common_keywords.robot
Resource         ../../resources/keywords/dashboard_keywords.robot
Suite Setup      Test Suite Setup
Suite Teardown   Test Suite Teardown
Test Teardown    Take Screenshot On Failure
Test Tags        smoke    critical

*** Variables ***
${TEST_ENV}         qa
${VALID_PDF_PATH}   test_data/valid_pdfs/sample_drawing.pdf

*** Test Cases ***
TC001 - Verify Application Is Accessible
    [Documentation]    Verify that the dOCReader application loads successfully
    [Tags]    smoke    P0
    
    Open dOCReader Application    environment=${TEST_ENV}
    Verify Page Title Contains    dOCReader
    Page Should Contain Element    xpath=//button[contains(text(),'Upload')]
    Log    ✅ Application is accessible    INFO

TC002 - Verify User Can Login
    [Documentation]    Verify successful login with valid credentials
    [Tags]    smoke    P0    authentication
    
    ${credentials}=    Get Test Credentials    ${TEST_ENV}
    Login To Application    ${credentials.username}    ${credentials.password}
    
    Page Should Contain Element    xpath=//h1[text()='Dashboard']
    Page Should Contain    Uploaded on
    Log    ✅ User login successful    INFO

TC003 - Verify Dashboard Loads With Document Table
    [Documentation]    Verify dashboard page displays with all required elements
    [Tags]    smoke    P0    ui
    
    # Verify dashboard elements
    Page Should Contain Element    xpath=//table[@id='documentTable']
    Page Should Contain    Document Name
    Page Should Contain    Status
    Page Should Contain    Action
    
    # Verify action buttons present
    Page Should Contain Element    xpath=//button[contains(text(),'Upload File')]
    Page Should Contain Element    xpath=//input[@placeholder='Search...']
    
    ${row_count}=    Get Element Count    xpath=//table[@id='documentTable']//tbody/tr
    Should Be True    ${row_count} >= 0
    Log    ✅ Dashboard loaded with ${row_count} documents    INFO

*** Keywords ***
Test Suite Setup
    [Documentation]    Setup executed once before all tests in suite
    Log    Starting Smoke Test Suite on ${TEST_ENV} environment    INFO
    Set Log Level    INFO

Test Suite Teardown
    [Documentation]    Cleanup after all tests complete
    Close Application
    Log    Smoke Test Suite completed    INFO

Get Test Credentials
    [Documentation]    Retrieves credentials for specified environment
    [Arguments]    ${env}
    
    ${config}=    Load Config    ${env}
    ${creds}=    Create Dictionary    
    ...    username=${config.credentials.username}
    ...    password=${config.credentials.password}
    
    [Return]    ${creds}

🚀 Setup & Execution Instructions
Initial Setup (One-time)
bash# Clone repository
git clone <repository-url>
cd docreader-automation

# Create virtual environment and install dependencies
make install-dev

# Activate virtual environment
source venv/bin/activate

# Install pre-commit hooks
make pre-commit

# Set up environment variables (create .env file)
cp .env.example .env
# Edit .env with your credentials
Running Tests Locally
bash# Run smoke tests on QA
make test-smoke ENV=qa

# Run all tests on QA
make test-qa

# Run tests in parallel
make test-parallel ENV=qa

# Run specific test suite
robot --outputdir results/qa --variable ENV:qa tests/functional/dashboard_tests.robot
Code Quality Checks
bash# Format code
make format

# Run linters
make lint

# Run robocop
make robocop

# Run pre-commit on all files
pre-commit run --all-files
