'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { loadAllComFunctions } = require('./extract-com-functions');

test('skill-level: proficiency ranks', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Rank 0: Newcomer', () => {
    const result = fns.getEventSkillLevel('A-15- Newcomer BALLROOM');
    assert.equal(result.rank, 0);
    assert.equal(result.label, 'Newcomer / Beginner');
  });

  await t.test('Rank 0: Beginner', () => {
    const result = fns.getEventSkillLevel('A-15- Débutant / Beginner LATIN SOLO (C/R/S)');
    assert.equal(result.rank, 0);
    assert.equal(result.label, 'Newcomer / Beginner');
  });

  await t.test('Rank 0: Débutant (French only)', () => {
    const result = fns.getEventSkillLevel('G-C Closed Débutant Tango');
    assert.equal(result.rank, 0);
  });

  await t.test('Rank 1: Pre-Bronze (Pré-Bronze/Pre-Bronze)', () => {
    const result = fns.getEventSkillLevel('AC-JV Pré-Bronze/Pre-Bronze AMATEUR BALLROOM (W/T/Q)');
    assert.equal(result.rank, 1);
    assert.equal(result.label, 'Pre-Bronze');
  });

  await t.test('Rank 1: Pre-Bronze (combined form Pré-Br. & Bronze)', () => {
    const result = fns.getEventSkillLevel('AC-15- Pré-Br. & Bronze/Pre-Br. & Bronze AMATEUR BALLROOM (W/T/Q)');
    assert.equal(result.rank, 1, 'Combined Pre-Bronze+Bronze should rank at Pre-Bronze (lower bound)');
    assert.equal(result.label, 'Pre-Bronze');
  });

  await t.test('Rank 1: Pre-Bronze 1 with sublevel', () => {
    const result = fns.getEventSkillLevel('A-JV2 Solo Indv. Pre-Bronze 1 BALLROOM (W/T/Q)');
    assert.equal(result.rank, 1);
    assert.equal(result.sublevel, 1);
    assert.equal(result.label, 'Pre-Bronze');
  });

  await t.test('Regression: Pre-Bronze (rank 1) does NOT match Bronze (rank 2) regex', () => {
    const preB = fns.getEventSkillLevel('AC-JV Pré-Bronze/Pre-Bronze AMATEUR BALLROOM (W/T/Q)');
    const bronze = fns.getEventSkillLevel('AC-JV Bronze/Bronze AMATEUR BALLROOM (W/T/Q)');
    assert.equal(preB.rank, 1, 'Pre-Bronze should be rank 1');
    assert.equal(bronze.rank, 2, 'Bronze should be rank 2');
    assert.notEqual(preB.rank, bronze.rank, 'Pre-Bronze and Bronze must have different ranks (\\bBronze\\b bug fix)');
  });

  await t.test('Rank 2: Bronze', () => {
    const result = fns.getEventSkillLevel('A-15- Bronze / Bronze BALLROOM SOLO (W/T/Q)');
    assert.equal(result.rank, 2);
    assert.equal(result.label, 'Bronze');
  });

  await t.test('Rank 3: Silver', () => {
    const result = fns.getEventSkillLevel('A-15- Argent / Silver BALLROOM SOLO (W/T/Q)');
    assert.equal(result.rank, 3);
    assert.equal(result.label, 'Silver');
  });

  await t.test('Rank 4: Gold', () => {
    const result = fns.getEventSkillLevel('A-15- Or / Gold BALLROOM SOLO (W/T/Q)');
    assert.equal(result.rank, 4);
    assert.equal(result.label, 'Gold');
  });

  await t.test('Rank 5: Novice', () => {
    const result = fns.getEventSkillLevel('AC-C Novice CLUB Salsa');
    assert.equal(result.rank, 5);
    assert.equal(result.label, 'Novice');
  });

  await t.test('Rank 6: Pre-Championship', () => {
    const result = fns.getEventSkillLevel('A-16+ Pre-Champ BALLROOM SOLO');
    assert.equal(result.rank, 6);
    assert.equal(result.label, 'Pre-Championship');
  });

  await t.test('Rank 7: Open (bare)', () => {
    const result = fns.getEventSkillLevel('A-16+ Ouvert / Open BALLROOM SOLO (W/T/VW/F/Q)');
    assert.equal(result.rank, 7);
    assert.equal(result.label, 'Open');
  });

  await t.test('Rank 9: Five Star', () => {
    const result = fns.getEventSkillLevel('L-E Closed Imperial Cup Pro-Am Five Star LATIN Championship (C/S/R/P/J)');
    assert.equal(result.rank, 9);
    assert.equal(result.label, 'Five Star');
  });

  await t.test('Rank 8: Championship (NATIONAL CHAMP)', () => {
    const result = fns.getEventSkillLevel('AC-JV2 AMATEUR BALLROOM "NATIONAL CHAMP" (W/T/VW/F/Q)');
    assert.equal(result.rank, 8);
    assert.equal(result.label, 'Championship');
  });

  await t.test('Rank 8: Championship beats bare Open', () => {
    const result = fns.getEventSkillLevel('AC-AD Open Amateur BALLROOM Championship (W/T/VW/F/Q)');
    assert.equal(result.rank, 8, 'Open Amateur ... Championship should rank as Championship (8), not Open (7)');
    assert.equal(result.label, 'Championship');
  });

  await t.test('Regression: named metal Bronze beats Championship decoration', () => {
    const result = fns.getEventSkillLevel('G-D Closed Bronze 1 Pro-Am CLUB Salsa Championship');
    assert.equal(result.rank, 2, 'Should be Bronze (rank 2), not Championship (rank 8)');
    assert.equal(result.label, 'Bronze');
  });

  await t.test('Regression: named metal Bronze beats Championship decoration (Open variant)', () => {
    const result = fns.getEventSkillLevel('L-C Open Bronze Pro-Am CLUB Salsa Championship');
    assert.equal(result.rank, 2, 'Should be Bronze (rank 2), not Championship (rank 8)');
    assert.equal(result.label, 'Bronze');
  });

  await t.test('Regression: Five Star beats Championship', () => {
    const result = fns.getEventSkillLevel('L-E Closed Imperial Cup Pro-Am Five Star LATIN Championship (C/S/R/P/J)');
    assert.equal(result.rank, 9, 'Five Star (rank 9) should beat Championship (rank 8)');
    assert.equal(result.label, 'Five Star');
  });
});

test('skill-level: French/English pairing', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Or / Gold always maps to Gold', () => {
    const result = fns.getEventSkillLevel('A-15- Or / Gold BALLROOM');
    assert.equal(result.rank, 4);
    assert.equal(result.label, 'Gold');
  });

  await t.test('Argent / Silver always maps to Silver', () => {
    const result = fns.getEventSkillLevel('AC-11U Argent / Silver AMATEUR BALLROOM');
    assert.equal(result.rank, 3);
    assert.equal(result.label, 'Silver');
  });

  await t.test('Ouvert / Open (bare) maps to Open rank 7', () => {
    const result = fns.getEventSkillLevel('A-16+ Ouvert / Open BALLROOM SOLO');
    assert.equal(result.rank, 7);
  });

  await t.test('Fermé / Closed works (modifier, not rank)', () => {
    const result = fns.getEventSkillLevel('L-C Fermé / Closed Bronze LATIN');
    assert.equal(result.rank, 2);
    assert.equal(result.modifier, 'Closed');
  });
});

test('skill-level: sub-levels (Bronze 1, 2, 3 etc.)', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Bronze 1 has sublevel 1', () => {
    const result = fns.getEventSkillLevel('G-D Closed Bronze 1 Pro-Am CLUB Salsa Championship');
    assert.equal(result.rank, 2);
    assert.equal(result.sublevel, 1);
  });

  await t.test('Bronze 2 has sublevel 2', () => {
    const result = fns.getEventSkillLevel('AC-C Open Bronze 2 CLUB Salsa');
    assert.equal(result.rank, 2);
    assert.equal(result.sublevel, 2);
  });

  await t.test('Bronze 3 has sublevel 3', () => {
    const result = fns.getEventSkillLevel('L-E Open Bronze 3 CLUB Merengue');
    assert.equal(result.rank, 2);
    assert.equal(result.sublevel, 3);
  });

  await t.test('Silver with no number has sublevel 0', () => {
    const result = fns.getEventSkillLevel('A-16+ Argent / Silver BALLROOM');
    assert.equal(result.rank, 3);
    assert.equal(result.sublevel, 0);
  });

  await t.test('Silver 1 has sublevel 1', () => {
    const result = fns.getEventSkillLevel('L-E Open Silver 1 CLUB Bachata');
    assert.equal(result.rank, 3);
    assert.equal(result.sublevel, 1);
  });

  await t.test('Silver 2 has sublevel 2', () => {
    const result = fns.getEventSkillLevel('AC-F Open Silver 2 CLUB Argentine Tango');
    assert.equal(result.rank, 3);
    assert.equal(result.sublevel, 2);
  });
});

test('skill-level: named metal beats Open/Closed modifier', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Open Bronze ranks as Bronze (rank 2) with modifier Open', () => {
    const result = fns.getEventSkillLevel('AC-C Open Bronze CLUB Salsa');
    assert.equal(result.rank, 2, 'Should be Bronze (rank 2), not Open (rank 7)');
    assert.equal(result.modifier, 'Open');
  });

  await t.test('Closed Bronze ranks as Bronze (rank 2) with modifier Closed', () => {
    const result = fns.getEventSkillLevel('L-C Closed Bronze LATIN');
    assert.equal(result.rank, 2);
    assert.equal(result.modifier, 'Closed');
  });

  await t.test('Open Silver ranks as Silver (rank 3) with modifier Open', () => {
    const result = fns.getEventSkillLevel('A-16+ Open Argent / Silver BALLROOM');
    assert.equal(result.rank, 3);
    assert.equal(result.modifier, 'Open');
  });

  await t.test('Closed Gold ranks as Gold (rank 4) with modifier Closed', () => {
    const result = fns.getEventSkillLevel('A-16+ Closed Or / Gold BALLROOM');
    assert.equal(result.rank, 4);
    assert.equal(result.modifier, 'Closed');
  });
});

test('skill-level: bare Open/Ouvert with no metal is rank 6', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Bare Open (English only) is rank 7', () => {
    const result = fns.getEventSkillLevel('G-D Open Waltz');
    assert.equal(result.rank, 7);
    assert.equal(result.modifier, null, 'Bare Open should have no modifier since Open IS the level');
  });

  await t.test('Bare Ouvert (French only) is rank 7', () => {
    const result = fns.getEventSkillLevel('L-E Ouvert Tango');
    assert.equal(result.rank, 7);
  });

  await t.test('Ouvert / Open (pair) is rank 7', () => {
    const result = fns.getEventSkillLevel('A-16+ Ouvert / Open BALLROOM SOLO');
    assert.equal(result.rank, 7);
  });
});

test('skill-level: unranked events return null', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Showcase event returns null', () => {
    const result = fns.getEventSkillLevel('G-F Americano');
    assert.equal(result, null);
  });

  await t.test('Challenge Cup returns null', () => {
    const result = fns.getEventSkillLevel('Challenge Cup BALLROOM');
    assert.equal(result, null);
  });

  await t.test('Event with no proficiency word returns null', () => {
    const result = fns.getEventSkillLevel('A-15- BALLROOM SOLO');
    assert.equal(result, null);
  });
});

test('skill-level: openRank flag', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Closed Bronze has openRank 0', () => {
    const result = fns.getEventSkillLevel('L-C Closed Bronze LATIN');
    assert.equal(result.openRank, 0);
  });

  await t.test('Open Bronze has openRank 1', () => {
    const result = fns.getEventSkillLevel('AC-C Open Bronze CLUB Salsa');
    assert.equal(result.openRank, 1);
  });

  await t.test('Closed Silver has openRank 0', () => {
    const result = fns.getEventSkillLevel('A-16+ Closed Argent / Silver BALLROOM');
    assert.equal(result.openRank, 0);
  });

  await t.test('Open Silver has openRank 1', () => {
    const result = fns.getEventSkillLevel('A-19+ Open Argent / Silver BALLROOM SOLO');
    assert.equal(result.openRank, 1);
  });

  await t.test('Bare Open (rank 7) without explicit Open mention has openRank 1 (Open is the level)', () => {
    const result = fns.getEventSkillLevel('G-D Ouvert / Open Waltz');
    assert.equal(result.rank, 7);
    assert.equal(result.openRank, 1);
  });
});

test('skill-level: regression cases from session fixes', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Real Bronze event from data', () => {
    const result = fns.getEventSkillLevel('A-15- Bronze / Bronze BALLROOM SOLO (W/T/Q)');
    assert.equal(result.rank, 2);
    assert.equal(result.label, 'Bronze');
  });

  await t.test('Real Silver event from data', () => {
    const result = fns.getEventSkillLevel('A-15- Argent / Silver BALLROOM SOLO (W/T/Q)');
    assert.equal(result.rank, 3);
    assert.equal(result.label, 'Silver');
  });

  await t.test('Real Gold event from data', () => {
    const result = fns.getEventSkillLevel('A-15- Or / Gold BALLROOM SOLO (W/T/Q)');
    assert.equal(result.rank, 4);
    assert.equal(result.label, 'Gold');
  });

  await t.test('Real Open event from data', () => {
    const result = fns.getEventSkillLevel('A-16+ Ouvert / Open BALLROOM SOLO NATIONAL (W/T/VW/F/Q)');
    assert.equal(result.rank, 7);
    assert.equal(result.label, 'Open');
  });

  await t.test('Level ladder ascending: Bronze < Silver < Gold < bare Open', () => {
    const bronze = fns.getEventSkillLevel('AC-C Closed Bronze CLUB Salsa');
    const silver = fns.getEventSkillLevel('AC-C Closed Silver CLUB Salsa');
    const gold = fns.getEventSkillLevel('AC-C Closed Gold CLUB Salsa');
    const open = fns.getEventSkillLevel('AC-C Open Salsa');

    assert.ok(bronze.rank < silver.rank, 'Bronze should rank lower than Silver');
    assert.ok(silver.rank < gold.rank, 'Silver should rank lower than Gold');
    assert.ok(gold.rank < open.rank, 'Gold should rank lower than Open');
  });
});
