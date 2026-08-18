'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { loadAllComFunctions } = require('./extract-com-functions');

const national = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', 'national2026', 'heat_events.json'), 'utf8'
));
const impercup = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', 'impercup2026', 'heat_events.json'), 'utf8'
));

function uniqueEventNames() {
  return [...new Set([...national, ...impercup].map(h => h.event))];
}

test('dance style: the four main disciplines', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('BALLROOM event', () => {
    const result = fns.getEventDanceStyle('A-19+ Bronze / Bronze BALLROOM SOLO Waltz');
    assert.equal(result.code, 'BALLROOM');
    assert.equal(result.label, 'Ballroom');
  });

  await t.test('LATIN event', () => {
    const result = fns.getEventDanceStyle('A-19+ Or / Gold LATIN SOLO Rumba');
    assert.equal(result.code, 'LATIN');
    assert.equal(result.label, 'Latin');
  });

  await t.test('SMOOTH event', () => {
    const result = fns.getEventDanceStyle('AC-15- Argent Fermé / Closed Silver AMATEUR SMOOTH (W/T/F)');
    assert.equal(result.code, 'SMOOTH');
  });

  await t.test('RHYTHM event', () => {
    const result = fns.getEventDanceStyle('AC-15- Bronze AMATEUR RHYTHM (C/R/S)');
    assert.equal(result.code, 'RHYTHM');
  });

  await t.test('CLUB event (secondary vocabulary, not one of the four)', () => {
    const result = fns.getEventDanceStyle('G-C Bronze Ouvert / Open Bronze CLUB Hustle');
    assert.equal(result.code, 'CLUB');
  });

  await t.test('TANGO STYLE event (secondary vocabulary, not one of the four)', () => {
    const result = fns.getEventDanceStyle('G-A Bronze Ouvert / Open Bronze TANGO STYLE Argentine Tango');
    assert.equal(result.code, 'TANGO_STYLE');
  });

  await t.test('event with none of the style words returns null', () => {
    const result = fns.getEventDanceStyle('L- Or / Gold Rumba');
    assert.equal(result, null);
  });
});

test('dance name: specific dance precedence (longer/more specific phrase wins)', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('Viennese Waltz is not read as plain Waltz', () => {
    const result = fns.getEventDanceName('A-19+ Argent / Silver BALLROOM SOLO Viennese Waltz');
    assert.equal(result.code, 'VIENNESE_WALTZ');
    assert.equal(result.label, 'Viennese Waltz');
  });

  await t.test('plain Waltz is still its own category', () => {
    const result = fns.getEventDanceName('A-19+ Bronze / Bronze BALLROOM SOLO Waltz');
    assert.equal(result.code, 'WALTZ');
  });

  await t.test('Argentine Tango is not read as plain Tango', () => {
    const result = fns.getEventDanceName('G-A Bronze Ouvert / Open Bronze TANGO STYLE Argentine Tango');
    assert.equal(result.code, 'ARGENTINE_TANGO');
  });

  await t.test('Tango Vals is not read as plain Tango', () => {
    const result = fns.getEventDanceName('G-C Or Fermé / Closed Gold TANGO STYLE Tango Vals');
    assert.equal(result.code, 'TANGO_VALS');
  });

  await t.test('plain Tango is still its own category', () => {
    const result = fns.getEventDanceName('A-36+ Ouvert / Open BALLROOM SOLO Tango');
    assert.equal(result.code, 'TANGO');
  });
});

test('dance name: "Chacha" and "Cha Cha" spellings merge to one canonical dance', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('"Chacha" (no space) resolves to Cha Cha', () => {
    const result = fns.getEventDanceName('A-19+ Or / Gold LATIN SOLO Chacha');
    assert.equal(result.code, 'CHA_CHA');
    assert.equal(result.label, 'Cha Cha');
  });

  await t.test('"Cha Cha" (with space) resolves to the same code', () => {
    const result = fns.getEventDanceName('AC-15- Bronze AMATEUR LATIN SOLO Cha Cha');
    assert.equal(result.code, 'CHA_CHA');
  });
});

test('dance name: unmatched events return null', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('multi-dance abbreviated round returns null', () => {
    const result = fns.getEventDanceName('A-15- Argent / Silver BALLROOM SOLO (W/T/Q)');
    assert.equal(result, null);
  });

  await t.test('themed freestyle solo with no standard dance name returns null', () => {
    const result = fns.getEventDanceName('"Beautiful Flower" - Acro');
    assert.equal(result, null);
  });
});

test('dance style/name: real dataset coverage sanity', async (t) => {
  const fns = loadAllComFunctions();
  const names = uniqueEventNames();

  await t.test('every event classifies without throwing', () => {
    assert.doesNotThrow(() => {
      names.forEach(n => {
        fns.getEventDanceStyle(n);
        fns.getEventDanceName(n);
      });
    });
  });

  await t.test('style classification covers a large majority of events', () => {
    const matched = names.filter(n => fns.getEventDanceStyle(n) !== null).length;
    assert.ok(matched / names.length > 0.7, `only ${matched}/${names.length} events got a dance style`);
  });

  await t.test('every matched style code is one of the six known codes', () => {
    const validCodes = new Set(['BALLROOM', 'LATIN', 'SMOOTH', 'RHYTHM', 'CLUB', 'TANGO_STYLE']);
    names.forEach(n => {
      const result = fns.getEventDanceStyle(n);
      if (result) assert.ok(validCodes.has(result.code), `unexpected style code "${result.code}" for "${n}"`);
    });
  });
});
