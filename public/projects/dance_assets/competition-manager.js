/**
 * Competition Manager - Handles switching between different dance competitions
 * Loads competition metadata and manages data paths
 */

class CompetitionManager {
  constructor() {
    this.competitions = [];
    this.activeCompetition = null;
    this.storageKey = 'danceActiveCompetition';
  }

  async load() {
    try {
      const res = await fetch('/projects/dance_assets/competitions.json');
      const data = await res.json();
      this.competitions = data.competitions || [];

      // Restore or set active competition
      const saved = localStorage.getItem(this.storageKey);
      const active = saved ?
        this.competitions.find(c => c.id === saved) :
        this.competitions.find(c => !c.archived);

      this.activeCompetition = active || this.competitions[0];

      if (this.activeCompetition) {
        localStorage.setItem(this.storageKey, this.activeCompetition.id);
      }

      return this.competitions;
    } catch (e) {
      console.error('Failed to load competitions:', e);
      return [];
    }
  }

  getActive() {
    return this.activeCompetition;
  }

  setActive(competitionId) {
    const comp = this.competitions.find(c => c.id === competitionId);
    if (comp) {
      this.activeCompetition = comp;
      localStorage.setItem(this.storageKey, competitionId);
      return true;
    }
    return false;
  }

  getDataPath(filename) {
    if (!this.activeCompetition) return `/projects/dance_assets/${filename}`;
    return `/projects/dance_assets/${this.activeCompetition.id}/${filename}`;
  }

  getCompetitionName() {
    return this.activeCompetition?.name || 'Dance Competition';
  }

  // Render a competition selector UI
  renderSelector(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let html = '<select id="competitionSelect" onchange="window.competitionManager.onSelectChange()" style="padding:8px 12px;background:var(--bg-secondary);border:1px solid var(--bg-tertiary);border-radius:4px;color:var(--text-primary);cursor:pointer;font-size:0.9em;">';

    this.competitions.forEach(comp => {
      const selected = comp.id === (this.activeCompetition?.id) ? 'selected' : '';
      const archived = comp.archived ? ' (archive)' : '';
      html += `<option value="${comp.id}" ${selected}>${comp.name}${archived}</option>`;
    });

    html += '</select>';
    container.innerHTML = html;
  }

  onSelectChange() {
    const select = document.getElementById('competitionSelect');
    if (select) {
      const newCompId = select.value;
      if (this.setActive(newCompId)) {
        // Update title immediately
        document.getElementById('competitionTitle').textContent = this.getCompetitionName();
        // Reload data
        if (window.loadData) {
          window.loadData();
        }
      } else {
        // Revert dropdown if setActive failed
        this.renderSelector('competitionSelector');
      }
    }
  }
}

// Global instance
window.competitionManager = new CompetitionManager();
