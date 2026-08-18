# Multi-Competition Dance System

This system now supports managing data for multiple dance competitions. You can easily switch between different competitions and archive old ones.

## Quick Start

### View a Competition
1. Open `com.html`
2. Use the competition dropdown at the top to switch between competitions
3. The data will automatically load from the selected competition's directory

### Add a New Competition

1. **Create a new directory** in `com_assets/`:
   ```bash
   mkdir com_assets/mycompetition2026
   ```

2. **Update `.env`** file to configure scraping:
   ```bash
   COMPETITION_ID=mycompetition2026
   HEAT_LISTS_URL=http://www.comp-mngr.com/mycompetition/entries.htm
   RESULTS_INDEX_URL=http://www.comp-mngr.com/mycompetition/scoresheets.htm  # or empty for no results
   RESULTS_CGI_URL=http://www.comp-mngr.com/cgi-bin/ScoresheetHandler.pl
   RESULTS_DATA_FILE=<root>/mycompetition/scoresheetdata.dat
   ```

3. **Update `competitions.json`** to register the new competition:
   ```json
   {
     "competitions": [
       {
         "id": "mycompetition2026",
         "name": "My Competition 2026",
         "description": "Description of the competition",
         "entryListUrl": "http://www.comp-mngr.com/mycompetition/entries.htm",
         "hasResults": true,
         "archived": false
       },
       // ... other competitions
     ]
   }
   ```

4. **Scrape the entry lists**:
   ```bash
   cd com_assets
   python3 scrape_data_flexible.py mycompetition2026
   ```

5. **Scrape results** (if available):
   ```bash
   python3 scrape_results_flexible.py mycompetition2026
   ```

## File Structure

```
com_assets/
├── .env                                # Configuration file (add to .gitignore)
├── .env.sample                         # Configuration template
├── competitions.json                   # List of all competitions
├── competition-manager.js              # Frontend competition switching
├── config.py                           # Python scraper configuration loader
│
├── scrape_data_flexible.py             # Entry list scraper (flexible)
├── scrape_results_flexible.py          # Results scraper (flexible)
│
├── impercup2026/                       # Imperial Cup archive
│   ├── participants.json
│   ├── heat_events.json
│   ├── results.json                   # Results optional
│   ├── person_results.json            # Results optional
│   └── judges.json                    # Results optional
│
└── national2026/                       # National 2026 (current)
    ├── participants.json
    ├── heat_events.json
    ├── results.json                   # Results optional
    ├── person_results.json            # Results optional
    └── judges.json                    # Results optional
```

## Configuration (`.env`)

The `.env` file controls which competition is scraped and used:

```bash
# Which competition directory to use
COMPETITION_ID=national2026

# Which competition to show by default when com.html loads
ACTIVE_COMPETITION=national2026

# Entry lists URL for scraping participants/heats
HEAT_LISTS_URL=http://www.comp-mngr.com/national2026/national2026_EntryLists.htm

# Results URLs (leave empty if no results available)
RESULTS_INDEX_URL=
RESULTS_CGI_URL=http://www.comp-mngr.com/cgi-bin/ScoresheetHandler.pl
RESULTS_DATA_FILE=<root>/national2026/national2026_scoresheetsbyperson.dat

# Scraper settings
REQUEST_DELAY=0.5                      # Seconds between requests (be polite)
MAX_RETRIES=3                          # Retry failed requests up to 3 times
```

## Data Files

Each competition directory should contain:

- **`participants.json`** (required): Map of person name → entries
  ```json
  {
    "Last, First": {
      "entries": [
        {
          "heat": "Heat 123",
          "event": "Solo Bronze",
          "time": "02:15PM Friday",
          "session": "Session A",
          "partner": null
        }
      ]
    }
  }
  ```

- **`heat_events.json`** (required): List of all heats with competitors
  ```json
  [
    {
      "heat": "Heat 123",
      "event": "Solo Bronze",
      "time": "02:15PM Friday",
      "session": "Session A",
      "competitors": ["Last, First", "Another, Person"]
    }
  ]
  ```

- **`results.json`** (optional): Full scoresheet results
- **`person_results.json`** (optional): Person-indexed results
- **`judges.json`** (optional): Judge ID → name mappings

## Scraping Entry Lists

### Using the Flexible Scraper

```bash
cd com_assets
python3 scrape_data_flexible.py national2026
```

Or use the current `.env` COMPETITION_ID:

```bash
python3 scrape_data_flexible.py
```

### Requirements

- The website must follow the comp-mngr.com format
- The page must have person names in `<strong>` tags as "Entries for: PersonName"
- Entry data must be in HTML tables with columns: Session@Time, (blank), Heat, Event

## Scraping Results

### Using the Flexible Scraper

```bash
cd com_assets
python3 scrape_results_flexible.py national2026
```

### Requirements

- Results index page must have a `<select name="PERSON_LIST">` dropdown
- Must use comp-mngr.com's CGI handler at `/cgi-bin/ScoresheetHandler.pl`
- Results scoresheets must follow the standard format

## Legacy Scripts

Old scripts are still available for reference:

- `scrape_data.py` - Original Imperial Cup scraper (hardcoded)
- `scrape_results.py` - Original results scraper (hardcoded)

These are kept for backward compatibility but **should not be used** for new competitions. Use the flexible versions instead.

## Frontend Integration

The frontend (`com.html`) automatically:

1. Loads `competitions.json` on page load
2. Shows a dropdown to select which competition to view
3. Remembers your selection in localStorage
4. Loads data from the selected competition's directory

### Competition Selector

The selector is automatically added by `competition-manager.js`. It appears in the header and allows switching competitions without reloading the page.

```javascript
// Get the currently active competition
const active = window.competitionManager.getActive();

// Switch to a different competition
window.competitionManager.setActive('impercup2026');

// Get the data path for a file
const path = window.competitionManager.getDataPath('participants.json');
// Returns: 'com_assets/impercup2026/participants.json'
```

## Troubleshooting

### "No data found" when switching competitions

Make sure the competition directory exists and contains the required JSON files (`participants.json` and `heat_events.json`).

### Scraper gets encoding errors

The flexible scrapers automatically handle both UTF-8 and ISO-8859-1 (Latin-1) encoding. If you get other encoding errors, open an issue with the error details.

### Scraper finds names but no entries

The HTML structure of the entry lists page might be different. The scraper expects:
- Names in `<strong>` tags formatted as "Entries for: Name"
- Entries in HTML tables with specific column order
- Heat and event information in the 3rd and 4th columns

You may need to customize the parser for different competition websites.

## Maintenance

### Archiving Old Competitions

Set `"archived": true` in `competitions.json` to move a competition to the bottom of the dropdown:

```json
{
  "id": "impercup2026",
  "name": "Imperial Cup 2026",
  "archived": true
}
```

### Cleaning Up

You can delete old competition directories if you no longer need them, but keep the entry in `competitions.json` for records. Or remove completely:

```bash
rm -rf com_assets/oldcompetition/
```

And remove from `competitions.json`.

## Notes

- All competitor data is stored locally in JSON files
- No real-time synchronization with the competition website
- Re-run scrapers to get updated data (run periodically before/during events)
- The system gracefully handles missing results files (shows "N/A" instead of errors)
