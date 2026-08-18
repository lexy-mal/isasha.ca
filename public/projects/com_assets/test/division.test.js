'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { loadAllComFunctions } = require('./extract-com-functions');

test('division: PRO events', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Event starting with "PRO " returns PRO', () => {
    const result = fns.getEventDivision('PRO BALLROOM Championnat National Canadien');
    assert.equal(result, 'PRO');
  });

  await t.test('PRO prefix is checked first even if other markers present', () => {
    const result = fns.getEventDivision('PRO BALLROOM Championship');
    assert.equal(result, 'PRO');
  });
});

test('division: Five Star events', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Event containing "Five Star" returns Five Star', () => {
    const result = fns.getEventDivision('L-E Closed Imperial Cup Pro-Am Five Star LATIN Championship (C/S/R/P/J)');
    assert.equal(result, 'Five Star');
  });

  await t.test('Five Star shadows Championship in the title', () => {
    // This is the critical regression case from EVENT_DIVISIONS.md:
    // "...Pro-Am Five Star LATIN Championship" must return "Five Star", not "Championship"
    const result = fns.getEventDivision('L-E Closed Imperial Cup Pro-Am Five Star LATIN Championship (C/S/R/P/J)');
    assert.equal(result, 'Five Star', 'Five Star marker should be found even though "Championship" appears later in the name');
  });

  await t.test('Regression: real Five Star event should not be classified as Championship', () => {
    const result = fns.getEventDivision('L-C Open Imperial Cup Pro-Am Five Star LATIN Championship (C/S/R/P/J)');
    assert.notEqual(result, 'Championship', 'Should not be classified as Championship');
    assert.equal(result, 'Five Star');
  });
});

test('division: CLUB events', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Event containing CLUB returns CLUB', () => {
    const result = fns.getEventDivision('G-C Closed Newcomer CLUB Merengue');
    assert.equal(result, 'CLUB');
  });

  await t.test('CLUB shadows Championship in the title', () => {
    const result = fns.getEventDivision('G-D Closed Bronze 1 Pro-Am CLUB Salsa Championship');
    assert.equal(result, 'CLUB', 'CLUB marker should take precedence over Championship');
  });

  await t.test('Real CLUB event from data', () => {
    const result = fns.getEventDivision('AC-C Open Pre-Bronze CLUB Salsa');
    assert.equal(result, 'CLUB');
  });
});

test('division: NATIONAL events', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Event containing NATIONAL returns NATIONAL', () => {
    const result = fns.getEventDivision('A-16+ Ouvert / Open BALLROOM SOLO NATIONAL (W/T/VW/F/Q)');
    assert.equal(result, 'NATIONAL');
  });

  await t.test('Real NATIONAL event from data', () => {
    const result = fns.getEventDivision('A-16+ Ouvert / Open LATIN SOLO NATIONAL (C/S/R/P/J)');
    assert.equal(result, 'NATIONAL');
  });
});

test('division: Rising Star events', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Event containing "Rising Star" returns Rising Star', () => {
    const result = fns.getEventDivision('A-15- Rising Star Bronze BALLROOM');
    assert.equal(result, 'Rising Star');
  });
});

test('division: Prechamp events', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Event containing "Prechamp" returns Prechamp', () => {
    const result = fns.getEventDivision('A-JR Prechamp Silver BALLROOM');
    assert.equal(result, 'Prechamp');
  });

  await t.test('Event containing "Pre-Champ" (hyphenated) returns Prechamp', () => {
    const result = fns.getEventDivision('AC-JR Pre-Champ Gold AMATEUR');
    assert.equal(result, 'Prechamp');
  });
});

test('division: Championship events', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Event containing Championship (but no Five Star or CLUB) returns Championship', () => {
    const result = fns.getEventDivision('AC-JR AMATEUR BALLROOM Championship (W/T/VW/F/Q)');
    assert.equal(result, 'Championship');
  });

  await t.test('Generic "Championship" in title', () => {
    const result = fns.getEventDivision('A-15- Bronze Championship BALLROOM');
    assert.equal(result, 'Championship');
  });

  await t.test('Championnat (French) also matches', () => {
    const result = fns.getEventDivision('L-E Closed Bronze Championnat LATIN');
    assert.equal(result, 'Championship');
  });
});

test('division: Standard events (default)', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Simple event with no division marker returns Standard', () => {
    const result = fns.getEventDivision('A-15- Bronze BALLROOM SOLO');
    assert.equal(result, 'Standard');
  });

  await t.test('Real Standard event from data', () => {
    const result = fns.getEventDivision('A-15- Argent / Silver BALLROOM SOLO (W/T/Q)');
    assert.equal(result, 'Standard');
  });

  await t.test('Another Standard example', () => {
    const result = fns.getEventDivision('G-F Closed Newcomer CLUB Merengue');
    // Wait, this one has CLUB...
    assert.equal(result, 'CLUB');
  });

  await t.test('Standard with no category markers', () => {
    const result = fns.getEventDivision('A-15- Or / Gold LATIN SOLO');
    assert.equal(result, 'Standard');
  });
});

test('division: precedence order matters', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('PRO at start beats everything', () => {
    const result = fns.getEventDivision('PRO BALLROOM Five Star Championship');
    assert.equal(result, 'PRO', 'PRO should be found first');
  });

  await t.test('Five Star beats CLUB beats NATIONAL', () => {
    const result = fns.getEventDivision('L-E Closed Imperial Cup Pro-Am Five Star CLUB Championship');
    // Five Star appears before CLUB in the name, but order in code checks Five Star first
    assert.equal(result, 'Five Star');
  });

  await t.test('CLUB beats NATIONAL', () => {
    const result = fns.getEventDivision('AC-C CLUB Salsa NATIONAL');
    assert.equal(result, 'CLUB');
  });

  await t.test('NATIONAL beats Championship', () => {
    const result = fns.getEventDivision('AC-16+ NATIONAL Championship');
    assert.equal(result, 'NATIONAL');
  });
});

test('division: regression case - Five Star vs Championship shadowing', async (t) => {
  const fns = loadAllComFunctions();

  // This is from the bug documented in EVENT_DIVISIONS.md:
  // "Championship is often just title decoration on an event whose real division is something else"
  // Testing the exact real case from the data:

  await t.test('Five Star event with Championship in title should return Five Star, not Championship', () => {
    const eventName = 'L-E Closed Imperial Cup Pro-Am Five Star LATIN Championship (C/S/R/P/J)';
    const result = fns.getEventDivision(eventName);
    assert.equal(result, 'Five Star', 'Should identify as Five Star division');
    assert.notEqual(result, 'Championship', 'Should NOT be misidentified as Championship');
  });

  await t.test('CLUB event with Championship in title should return CLUB, not Championship', () => {
    const eventName = 'G-D Closed Bronze 1 Pro-Am CLUB Salsa Championship';
    const result = fns.getEventDivision(eventName);
    assert.equal(result, 'CLUB', 'Should identify as CLUB division');
    assert.notEqual(result, 'Championship', 'Should NOT be misidentified as Championship');
  });

  await t.test('Pure Championship (no Five Star, no CLUB) should still be Championship', () => {
    const eventName = 'A-JR Closed Silver Championship BALLROOM';
    const result = fns.getEventDivision(eventName);
    assert.equal(result, 'Championship', 'Should identify as Championship when no Five Star or CLUB present');
  });
});
