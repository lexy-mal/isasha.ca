#!/usr/bin/env python3
"""
Configuration loader for dance competition scrapers.
Reads from .env file in parent directory.
"""

import os
import re
from pathlib import Path


def load_env():
    """Load .env file from parent directory"""
    env_file = Path(__file__).parent.parent / '.env'
    env_vars = {}

    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()

    return env_vars


def get_config(comp_id=None):
    """Get configuration for a competition"""
    env_vars = load_env()

    if comp_id is None:
        comp_id = env_vars.get('COMPETITION_ID', 'national2026')

    config = {
        'competition_id': comp_id,
        'heat_lists_url': env_vars.get('HEAT_LISTS_URL', ''),
        'results_index_url': env_vars.get('RESULTS_INDEX_URL', ''),
        'results_cgi_url': env_vars.get('RESULTS_CGI_URL', 'http://www.comp-mngr.com/cgi-bin/ScoresheetHandler.pl'),
        'results_data_file': env_vars.get('RESULTS_DATA_FILE', ''),
        'request_delay': 0.5,
        'max_retries': 3,
    }

    return config


def get_output_dir(comp_id):
    """Get output directory for competition data"""
    script_dir = Path(__file__).parent
    comp_dir = script_dir / comp_id
    comp_dir.mkdir(exist_ok=True)
    return comp_dir
