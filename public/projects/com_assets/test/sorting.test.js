'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { loadAllComFunctions } = require('./extract-com-functions');

// Load real event data from both competitions
const national = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', 'national2026', 'heat_events.json'), 'utf8'
));
const impercup = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', 'impercup2026', 'heat_events.json'), 'utf8'
));

// Deduplicate events by name and create heat objects
function getUniqueHeats() {
  const seen = new Set();
  const heats = [];
  [...national, ...impercup].forEach(h => {
    if (!seen.has(h.event)) {
      seen.add(h.event);
      heats.push({
        name: h.event,
        competitors: h.competitors ? h.competitors.length : 0
      });
    }
  });
  return heats;
}

test('sorting: name_asc (ascending alphabetical)', async (t) => {
  const fns = loadAllComFunctions();
  const heats = getUniqueHeats();

  await t.test('sorted list has same length as input', () => {
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'name_asc'));
    assert.equal(sorted.length, heats.length);
  });

  await t.test('sorted list contains same events as input', () => {
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'name_asc'));
    const originalSet = new Set(heats.map(h => h.name));
    const sortedSet = new Set(sorted.map(h => h.name));
    assert.deepEqual(sortedSet, originalSet);
  });

  await t.test('sorted names are in ascending alphabetical order', () => {
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'name_asc'));
    for (let i = 1; i < sorted.length; i++) {
      assert.ok(
        sorted[i - 1].name.localeCompare(sorted[i].name) <= 0,
        `${sorted[i - 1].name} should come before ${sorted[i].name}`
      );
    }
  });
});

test('sorting: name_desc (descending alphabetical)', async (t) => {
  const fns = loadAllComFunctions();
  const heats = getUniqueHeats();

  await t.test('sorted names are in descending alphabetical order', () => {
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'name_desc'));
    for (let i = 1; i < sorted.length; i++) {
      assert.ok(
        sorted[i - 1].name.localeCompare(sorted[i].name) >= 0,
        `${sorted[i - 1].name} should come before or equal to ${sorted[i].name}`
      );
    }
  });
});

test('sorting: count_asc (ascending by competitor count)', async (t) => {
  const fns = loadAllComFunctions();
  const heats = getUniqueHeats();

  await t.test('sorted counts are in ascending order', () => {
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'count_asc'));
    for (let i = 1; i < sorted.length; i++) {
      assert.ok(
        sorted[i - 1].competitors <= sorted[i].competitors,
        `${sorted[i - 1].competitors} should be <= ${sorted[i].competitors}`
      );
    }
  });
});

test('sorting: count_desc (descending by competitor count)', async (t) => {
  const fns = loadAllComFunctions();
  const heats = getUniqueHeats();

  await t.test('sorted counts are in descending order', () => {
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'count_desc'));
    for (let i = 1; i < sorted.length; i++) {
      assert.ok(
        sorted[i - 1].competitors >= sorted[i].competitors,
        `${sorted[i - 1].competitors} should be >= ${sorted[i].competitors}`
      );
    }
  });
});

test('sorting: age_asc (ascending by age)', async (t) => {
  const fns = loadAllComFunctions();
  const heats = getUniqueHeats();

  await t.test('sorted ages are monotonic ascending', () => {
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'age_asc'));
    let lastMinAge = -Infinity;
    let lastMaxAge = -Infinity;

    for (const heat of sorted) {
      const cat = fns.getEventAgeCategory(heat.name);
      if (cat) {
        const minAge = cat.minAge;
        // When minAge is equal, maxAge should be tiebreaker (lower max = younger = earlier)
        if (minAge === lastMinAge) {
          const maxA = cat.maxAge ?? -Infinity;
          assert.ok(
            maxA >= lastMaxAge,
            `For same minAge ${minAge}, maxAge should be ascending: ${lastMaxAge} <= ${maxA}`
          );
          lastMaxAge = maxA;
        } else {
          assert.ok(minAge >= lastMinAge, `minAge should be ascending: ${lastMinAge} <= ${minAge}`);
          lastMinAge = minAge;
          lastMaxAge = cat.maxAge ?? -Infinity;
        }
      }
    }
  });

  await t.test('events with no age category appear last', () => {
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'age_asc'));
    let foundNoAge = false;
    for (let i = 0; i < sorted.length; i++) {
      const hasAge = fns.getEventAgeCategory(sorted[i].name) !== null;
      if (!hasAge) {
        foundNoAge = true;
        // All remaining should also have no age
        for (let j = i + 1; j < sorted.length; j++) {
          const nextHasAge = fns.getEventAgeCategory(sorted[j].name) !== null;
          assert.ok(!nextHasAge || (nextHasAge && i === j), 'No-age events should all be at the end');
        }
      }
    }
  });

  await t.test('Regression: Under 10 < Under 12 < 15 & Under when age_asc', () => {
    const heats = [
      { name: 'A-JV1 Bronze BALLROOM', competitors: 5 },
      { name: 'AC-U12 Silver AMATEUR', competitors: 5 },
      { name: 'A-15- Gold BALLROOM', competitors: 5 }
    ];
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'age_asc'));

    assert.equal(sorted[0].name, 'A-JV1 Bronze BALLROOM', 'JV1 (max:10) should come first');
    assert.equal(sorted[1].name, 'AC-U12 Silver AMATEUR', 'U12 (max:12) should come second');
    assert.equal(sorted[2].name, 'A-15- Gold BALLROOM', '15- (max:15) should come last');
  });
});

test('sorting: age_desc (descending by age)', async (t) => {
  const fns = loadAllComFunctions();
  const heats = getUniqueHeats();

  await t.test('sorted ages are monotonic descending', () => {
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'age_desc'));
    let lastMinAge = Infinity;
    let lastMaxAge = Infinity;

    for (const heat of sorted) {
      const cat = fns.getEventAgeCategory(heat.name);
      if (cat) {
        const minAge = cat.minAge;
        if (minAge === lastMinAge) {
          const maxA = cat.maxAge ?? Infinity;
          assert.ok(
            maxA <= lastMaxAge,
            `For same minAge ${minAge}, maxAge should be descending: ${lastMaxAge} >= ${maxA}`
          );
          lastMaxAge = maxA;
        } else {
          assert.ok(minAge <= lastMinAge, `minAge should be descending: ${lastMinAge} >= ${minAge}`);
          lastMinAge = minAge;
          lastMaxAge = cat.maxAge ?? Infinity;
        }
      }
    }
  });

  await t.test('events with no age category appear last (in both directions)', () => {
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'age_desc'));
    let foundNoAge = false;
    for (let i = 0; i < sorted.length; i++) {
      const hasAge = fns.getEventAgeCategory(sorted[i].name) !== null;
      if (!hasAge) {
        foundNoAge = true;
        for (let j = i + 1; j < sorted.length; j++) {
          const nextHasAge = fns.getEventAgeCategory(sorted[j].name) !== null;
          assert.ok(!nextHasAge, 'No-age events should all be at the end in desc too');
        }
      }
    }
  });
});

test('sorting: level_asc (ascending by proficiency)', async (t) => {
  const fns = loadAllComFunctions();
  const heats = getUniqueHeats();

  await t.test('sorted levels are monotonic ascending by rank', () => {
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'level_asc'));
    let lastRank = -Infinity;

    for (const heat of sorted) {
      const level = fns.getEventSkillLevel(heat.name);
      if (level) {
        assert.ok(level.rank >= lastRank, `rank should be ascending: ${lastRank} <= ${level.rank}`);
        if (level.rank === lastRank) {
          // Tiebreaks: sublevel, then openRank
        }
        lastRank = level.rank;
      }
    }
  });

  await t.test('unranked events appear strictly after all ranked events', () => {
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'level_asc'));
    let foundUnranked = false;
    for (let i = 0; i < sorted.length; i++) {
      const level = fns.getEventSkillLevel(sorted[i].name);
      if (!level) {
        foundUnranked = true;
        // All remaining should also be unranked
        for (let j = i + 1; j < sorted.length; j++) {
          const nextLevel = fns.getEventSkillLevel(sorted[j].name);
          assert.ok(!nextLevel, 'Unranked events should all be at the end (asc)');
        }
      }
    }
  });

  await t.test('Regression: Bronze < Silver < Gold < Open in level_asc', () => {
    const heats = [
      { name: 'AC-C Closed Gold CLUB Salsa', competitors: 5 },
      { name: 'AC-C Closed Bronze CLUB Salsa', competitors: 5 },
      { name: 'AC-C Closed Silver CLUB Salsa', competitors: 5 },
      { name: 'AC-C Open Salsa', competitors: 5 }
    ];
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'level_asc'));

    const ranks = sorted.map(h => {
      const level = fns.getEventSkillLevel(h.name);
      return level ? level.rank : null;
    });

    assert.deepEqual(ranks, [2, 3, 4, 7], 'Should be Bronze(2) < Silver(3) < Gold(4) < Open(7)');
  });

  await t.test('Regression: full tier ordering including Pre-Bronze and Championship in level_asc', () => {
    const heats = [
      { name: 'AC-C Open Salsa', competitors: 5 },          // Open rank 7
      { name: 'L-E Closed Imperial Cup Pro-Am Five Star LATIN Championship (C/S/R/P/J)', competitors: 5 }, // Five Star rank 9
      { name: 'AC-JV Pré-Bronze/Pre-Bronze AMATEUR BALLROOM (W/T/Q)', competitors: 5 },     // Pre-Bronze rank 1
      { name: 'AC-C Closed Bronze CLUB Salsa', competitors: 5 },  // Bronze rank 2
      { name: 'AC-JV2 AMATEUR BALLROOM "NATIONAL CHAMP" (W/T/VW/F/Q)', competitors: 5 },   // Championship rank 8
      { name: 'AC-C Closed Silver CLUB Salsa', competitors: 5 },  // Silver rank 3
      { name: 'AC-C Closed Gold CLUB Salsa', competitors: 5 }     // Gold rank 4
    ];
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'level_asc'));

    const ranks = sorted.map(h => {
      const level = fns.getEventSkillLevel(h.name);
      return level ? level.rank : null;
    });

    assert.deepEqual(ranks, [1, 2, 3, 4, 7, 8, 9], 'Should be Pre-Bronze(1) < Bronze(2) < Silver(3) < Gold(4) < Open(7) < Championship(8) < Five Star(9)');
  });
});

test('sorting: level_desc (descending by proficiency)', async (t) => {
  const fns = loadAllComFunctions();
  const heats = getUniqueHeats();

  await t.test('sorted levels are monotonic descending by rank', () => {
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'level_desc'));
    let lastRank = Infinity;

    for (const heat of sorted) {
      const level = fns.getEventSkillLevel(heat.name);
      if (level) {
        assert.ok(level.rank <= lastRank, `rank should be descending: ${lastRank} >= ${level.rank}`);
        lastRank = level.rank;
      }
    }
  });

  await t.test('unranked events appear strictly after all ranked events (desc too)', () => {
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'level_desc'));
    let foundUnranked = false;
    for (let i = 0; i < sorted.length; i++) {
      const level = fns.getEventSkillLevel(sorted[i].name);
      if (!level) {
        foundUnranked = true;
        for (let j = i + 1; j < sorted.length; j++) {
          const nextLevel = fns.getEventSkillLevel(sorted[j].name);
          assert.ok(!nextLevel, 'Unranked events should all be at the end (desc)');
        }
      }
    }
  });
});

test('sorting: division_asc (by division prestige)', async (t) => {
  const fns = loadAllComFunctions();
  const heats = getUniqueHeats();

  const divisionOrder = { Standard: 0, 'Rising Star': 1, Prechamp: 2, CLUB: 3, NATIONAL: 4, Championship: 5, 'Five Star': 6, PRO: 7 };

  await t.test('sorted divisions are in prestige order', () => {
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'division_asc'));
    let lastRank = -Infinity;

    for (const heat of sorted) {
      const division = fns.getEventDivision(heat.name);
      const divRank = divisionOrder[division] ?? 8;
      assert.ok(divRank >= lastRank, `division rank should be ascending: ${lastRank} <= ${divRank}`);
      lastRank = divRank;
    }
  });

  await t.test('Regression: Five Star vs Championship shadowing in sort order', () => {
    const heats = [
      { name: 'G-D Closed Bronze 1 Pro-Am CLUB Salsa Championship', competitors: 5 }, // CLUB
      { name: 'L-E Closed Imperial Cup Pro-Am Five Star LATIN Championship (C/S/R/P/J)', competitors: 5 }, // Five Star
      { name: 'A-16+ Ouvert / Open BALLROOM SOLO NATIONAL (W/T/VW/F/Q)', competitors: 5 } // NATIONAL
    ];
    const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, 'division_asc'));

    const divs = sorted.map(h => fns.getEventDivision(h.name));
    // Should be CLUB(3) < NATIONAL(4) < Five Star(6)
    assert.equal(divs[0], 'CLUB', 'CLUB should come first');
    assert.equal(divs[1], 'NATIONAL', 'NATIONAL should come second');
    assert.equal(divs[2], 'Five Star', 'Five Star should come last');
  });
});

test('sorting: all sort modes on large real dataset', async (t) => {
  const fns = loadAllComFunctions();
  const heats = getUniqueHeats();
  const sortModes = ['name_asc', 'name_desc', 'count_asc', 'count_desc', 'age_asc', 'age_desc', 'level_asc', 'level_desc', 'division_asc'];

  for (const sortMode of sortModes) {
    await t.test(`${sortMode}: maintains length and uniqueness on real data`, () => {
      const sorted = heats.slice().sort((a, b) => fns.compareHeatsBySort(a, b, sortMode));
      assert.equal(sorted.length, heats.length, 'Same length');

      const sortedSet = new Set(sorted.map(h => h.name));
      assert.equal(sortedSet.size, heats.length, 'No duplicates');

      const originalSet = new Set(heats.map(h => h.name));
      assert.deepEqual(sortedSet, originalSet, 'Same events');
    });
  }
});
