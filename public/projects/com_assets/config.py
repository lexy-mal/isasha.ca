#!/usr/bin/env python3
"""
Configuration loader for dance competition scrapers.

Resolution order for each setting (first non-empty wins):
    os.environ  →  competitions.json  →  .env file  →  built-in default

competitions.json is the committed, per-competition source of truth, so scraping
a given competition works on a fresh checkout with no .env present. The .env file
remains supported for local overrides.
"""

import os
import json
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


def load_competitions():
    """Load competitions.json (list of competition metadata dicts)"""
    comp_file = Path(__file__).parent / 'competitions.json'
    if not comp_file.exists():
        return []
    try:
        with open(comp_file, 'r', encoding='utf-8') as f:
            return json.load(f).get('competitions', [])
    except (json.JSONDecodeError, OSError):
        return []


def get_competition(comp_id):
    """Look up one competition's metadata by id, or {} if unknown"""
    for comp in load_competitions():
        if comp.get('id') == comp_id:
            return comp
    return {}


def get_config(comp_id=None):
    """Get configuration for a competition"""
    env_vars = load_env()

    if comp_id is None:
        comp_id = os.environ.get('COMPETITION_ID') or env_vars.get('COMPETITION_ID', 'national2026')

    comp = get_competition(comp_id)

    def resolve(env_key, comp_key, default=''):
        return (os.environ.get(env_key)
                or comp.get(comp_key)
                or env_vars.get(env_key)
                or default)

    config = {
        'competition_id': comp_id,
        'heat_lists_url': resolve('HEAT_LISTS_URL', 'heatListUrl'),
        'results_index_url': resolve('RESULTS_INDEX_URL', 'resultsIndexUrl'),
        'results_cgi_url': resolve('RESULTS_CGI_URL', 'resultsCgiUrl',
                                   'http://www.comp-mngr.com/cgi-bin/ScoresheetHandler.pl'),
        'results_data_file': resolve('RESULTS_DATA_FILE', 'resultsDataFile'),
        'results_dat_url': resolve('RESULTS_DAT_URL', 'resultsDatUrl'),
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
