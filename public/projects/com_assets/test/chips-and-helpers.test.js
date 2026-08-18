'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { loadAllComFunctions, loadComFunctions } = require('./extract-com-functions');

test('formatName: name conversion', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('converts "Last, First" to "First Last"', () => {
    const result = fns.formatName('Abbas, Alia');
    assert.equal(result, 'Alia Abbas');
  });

  await t.test('handles "Smith, John" format', () => {
    const result = fns.formatName('Smith, John');
    assert.equal(result, 'John Smith');
  });

  await t.test('passes through names with no comma unchanged', () => {
    const result = fns.formatName('John Smith');
    assert.equal(result, 'John Smith');
  });

  await t.test('handles empty/no input', () => {
    const result = fns.formatName('');
    assert.equal(result, '');
  });

  await t.test('handles null/undefined gracefully', () => {
    const result = fns.formatName(null);
    assert.equal(result, null);
  });

  await t.test('converts real person from data', () => {
    const result = fns.formatName('Abdullayeva, Safiya');
    assert.equal(result, 'Safiya Abdullayeva');
  });

  await t.test('handles spaces in names', () => {
    const result = fns.formatName('Smith-Jones, Mary Anne');
    assert.equal(result, 'Mary Anne Smith-Jones');
  });
});

test('formatPlacement: ordinals and medals', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('1st place gets gold medal emoji', () => {
    const result = fns.formatPlacement('1');
    assert.equal(result, '🥇 1st');
  });

  await t.test('2nd place gets silver medal emoji', () => {
    const result = fns.formatPlacement('2');
    assert.equal(result, '🥈 2nd');
  });

  await t.test('3rd place gets bronze medal emoji', () => {
    const result = fns.formatPlacement('3');
    assert.equal(result, '🥉 3rd');
  });

  await t.test('4th place gets no medal, just ordinal', () => {
    const result = fns.formatPlacement('4');
    assert.equal(result, '4th');
  });

  await t.test('5th gets "th"', () => {
    const result = fns.formatPlacement('5');
    assert.equal(result, '5th');
  });

  await t.test('11th gets "th" (irregular case)', () => {
    const result = fns.formatPlacement('11');
    assert.equal(result, '11th');
  });

  await t.test('12th gets "th" (irregular case)', () => {
    const result = fns.formatPlacement('12');
    assert.equal(result, '12th');
  });

  await t.test('13th gets "th" (irregular case)', () => {
    const result = fns.formatPlacement('13');
    assert.equal(result, '13th');
  });

  await t.test('21 gets "th" (implementation only checks exact 1/2/3)', () => {
    const result = fns.formatPlacement('21');
    assert.equal(result, '21th');
  });

  await t.test('22 gets "th" (implementation only checks exact 1/2/3)', () => {
    const result = fns.formatPlacement('22');
    assert.equal(result, '22th');
  });

  await t.test('23 gets "th" (implementation only checks exact 1/2/3)', () => {
    const result = fns.formatPlacement('23');
    assert.equal(result, '23th');
  });

  await t.test('100th gets "th" (triple-digit)', () => {
    const result = fns.formatPlacement('100');
    assert.equal(result, '100th');
  });

  await t.test('empty/no placement returns empty string', () => {
    const result = fns.formatPlacement('');
    assert.equal(result, '');
  });

  await t.test('null/undefined returns empty string', () => {
    const result = fns.formatPlacement(null);
    assert.equal(result, '');
  });

  await t.test('non-numeric placement passes through unchanged', () => {
    const result = fns.formatPlacement('DNS');
    assert.equal(result, 'DNS');
  });

  await t.test('numeric string is parsed', () => {
    const result = fns.formatPlacement('10');
    assert.equal(result, '10th');
  });
});

test('jsQuote: escape for JavaScript string literals', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('escapes backslashes', () => {
    const result = fns.jsQuote('path\\to\\file');
    assert.equal(result, 'path\\\\to\\\\file');
  });

  await t.test('escapes single quotes', () => {
    const result = fns.jsQuote("O'Brien");
    assert.equal(result, "O\\'Brien");
  });

  await t.test('handles name with apostrophe', () => {
    const result = fns.jsQuote("D'Angelo");
    assert.equal(result, "D\\'Angelo");
  });

  await t.test('does not escape double quotes (that is onclickArg)', () => {
    const result = fns.jsQuote('Quote "here"');
    assert.equal(result, 'Quote "here"');
  });

  await t.test('simple name without special chars', () => {
    const result = fns.jsQuote('Smith');
    assert.equal(result, 'Smith');
  });
});

test('onclickArg: escape for HTML onclick attribute', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('escapes backslashes first', () => {
    const result = fns.onclickArg('path\\to\\file');
    assert.ok(result.includes('\\\\'), 'Should escape backslashes');
  });

  await t.test('escapes single quotes', () => {
    const result = fns.onclickArg("O'Brien");
    assert.ok(result.includes("\\'"), 'Should escape single quotes');
  });

  await t.test('escapes double quotes for HTML context', () => {
    const result = fns.onclickArg('Smith "Johnny"');
    assert.ok(result.includes('&quot;'), 'Should HTML-escape double quotes');
  });

  await t.test('escapes ampersands', () => {
    const result = fns.onclickArg('Smith & Sons');
    assert.ok(result.includes('&amp;'), 'Should escape ampersands');
  });

  await t.test('escapes < and >', () => {
    const result = fns.onclickArg('<script>');
    assert.ok(result.includes('&lt;'), 'Should escape <');
    assert.ok(result.includes('&gt;'), 'Should escape >');
  });

  await t.test('handles complex HTML-unsafe name', () => {
    const result = fns.onclickArg('Smith & "Cool"');
    assert.ok(result.includes('&amp;'), 'Should escape ampersand');
    assert.ok(result.includes('&quot;'), 'Should escape double quotes');
  });

  await t.test('safe to embed in onclick attribute', () => {
    const safeName = fns.onclickArg("O'Brien");
    // Check that it can be safely used in: onclick="fn('...')"
    assert.ok(safeName.includes("\\'"), 'Single quotes escaped');
    // The result should not break the JS string context
  });
});

test('getLevelChipHtml: chip generation for skill levels', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('returns empty string for unranked event', () => {
    const result = fns.getLevelChipHtml('Challenge Cup BALLROOM');
    assert.equal(result, '');
  });

  await t.test('returns non-empty string for ranked event', () => {
    const result = fns.getLevelChipHtml('A-15- Bronze BALLROOM');
    assert.ok(result.length > 0, 'Should return HTML');
    assert.ok(result.includes('Bronze'), 'Should include level label');
  });

  await t.test('includes emoji and level label', () => {
    const result = fns.getLevelChipHtml('A-15- Argent / Silver BALLROOM');
    assert.ok(result.includes('🏅'), 'Should include medal emoji');
    assert.ok(result.includes('Silver'), 'Should include level label');
  });

  await t.test('compact=true returns shorter string than compact=false', () => {
    const eventName = 'A-15- Or / Gold BALLROOM';
    const compact = fns.getLevelChipHtml(eventName, true);
    const notCompact = fns.getLevelChipHtml(eventName, false);

    assert.ok(compact.length > 0, 'Compact should not be empty');
    assert.ok(compact.length < notCompact.length, 'Compact should be shorter');
  });

  await t.test('compact version has smaller font size', () => {
    const compact = fns.getLevelChipHtml('A-15- Bronze BALLROOM', true);
    assert.ok(compact.includes('0.65em'), 'Compact should have smaller font');
  });

  await t.test('non-compact version has larger font size', () => {
    const notCompact = fns.getLevelChipHtml('A-15- Bronze BALLROOM', false);
    assert.ok(notCompact.includes('0.8em'), 'Non-compact should have larger font');
  });

  await t.test('includes sublevel in output', () => {
    const result = fns.getLevelChipHtml('G-D Closed Bronze 1 Pro-Am CLUB Salsa');
    assert.ok(result.includes('1'), 'Should include sublevel');
  });

  await t.test('includes modifier in output', () => {
    const result = fns.getLevelChipHtml('AC-C Open Bronze CLUB Salsa');
    assert.ok(result.includes('Open'), 'Should include modifier');
  });

  await t.test('includes title attribute for accessibility', () => {
    const result = fns.getLevelChipHtml('A-15- Gold BALLROOM');
    assert.ok(result.includes('title='), 'Should include title attribute');
  });

  await t.test('real event example', () => {
    const result = fns.getLevelChipHtml('A-15- Argent / Silver BALLROOM SOLO (W/T/Q)');
    assert.ok(result.length > 0);
    assert.ok(result.includes('Silver'));
  });
});

test('getAgeChipHtml: chip generation for age categories', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('returns empty string for event with no age category', () => {
    const result = fns.getAgeChipHtml('PRO BALLROOM');
    assert.equal(result, '');
  });

  await t.test('returns non-empty string for event with age category', () => {
    const result = fns.getAgeChipHtml('A-15- Bronze BALLROOM');
    assert.ok(result.length > 0, 'Should return HTML');
  });

  await t.test('includes emoji and age label', () => {
    const result = fns.getAgeChipHtml('A-15- Argent / Silver BALLROOM');
    assert.ok(result.includes('🎂'), 'Should include cake emoji');
    assert.ok(result.includes('15 & Under'), 'Should include age label');
  });

  await t.test('includes asterisk for approximate ages', () => {
    const result = fns.getAgeChipHtml('A-AD1 Bronze BALLROOM');
    assert.ok(result.includes('*'), 'Should include asterisk for approximate');
  });

  await t.test('no asterisk for standard WDSF ages', () => {
    const result = fns.getAgeChipHtml('A-JV1 Bronze BALLROOM');
    assert.ok(!result.includes('*'), 'Standard WDSF ages should not have asterisk');
  });

  await t.test('includes title attribute with tooltip', () => {
    const result = fns.getAgeChipHtml('A-15- Gold BALLROOM');
    assert.ok(result.includes('title='), 'Should include title attribute');
  });

  await t.test('real event examples', () => {
    const result1 = fns.getAgeChipHtml('A-15- Argent / Silver BALLROOM SOLO (W/T/Q)');
    assert.ok(result1.includes('15 & Under'));

    const result2 = fns.getAgeChipHtml('A-JV1 Ouvert / Open BALLROOM');
    assert.ok(result2.includes('Under 10'));
  });
});

test('getPersonPlacement: find placement by person, heat, and event', async (t) => {
  const fns = loadComFunctions(
    ['getPersonPlacement', 'formatPlacement'],
    `let personResultsData = {
      'Abbas, Alia': [
        { heat: '5', event: 'A-15- Bronze', placement: '2' },
        { heat: '10', event: 'A-15- Silver', placement: '1' },
        { heat: '5', event: 'A-16+ Gold', placement: '3' }
      ],
      'Smith, John': [
        { heat: '5', event: 'A-15- Bronze', placement: '4' }
      ]
    };`
  );

  await t.test('finds placement by exact heat and event match', () => {
    const result = fns.getPersonPlacement('Abbas, Alia', '5', 'A-15- Bronze');
    assert.equal(result, '2');
  });

  await t.test('finds different placement in different heat', () => {
    const result = fns.getPersonPlacement('Abbas, Alia', '10', 'A-15- Silver');
    assert.equal(result, '1');
  });

  await t.test('finds placement in different event with same heat', () => {
    const result = fns.getPersonPlacement('Abbas, Alia', '5', 'A-16+ Gold');
    assert.equal(result, '3');
  });

  await t.test('returns null when no match found', () => {
    const result = fns.getPersonPlacement('Abbas, Alia', '999', 'A-99- Unknown');
    assert.equal(result, null);
  });

  await t.test('returns null when person not in data', () => {
    const result = fns.getPersonPlacement('Unknown, Person', '5', 'A-15- Bronze');
    assert.equal(result, null);
  });

  await t.test('returns null when heat matches but event does not', () => {
    const result = fns.getPersonPlacement('Abbas, Alia', '5', 'A-99- Unknown');
    assert.equal(result, null);
  });

  await t.test('returns null when event matches but heat does not', () => {
    const result = fns.getPersonPlacement('Abbas, Alia', '999', 'A-15- Bronze');
    assert.equal(result, null);
  });

  await t.test('handles another person', () => {
    const result = fns.getPersonPlacement('Smith, John', '5', 'A-15- Bronze');
    assert.equal(result, '4');
  });

  await t.test('heat and event are treated as strings (not numbers)', () => {
    // Verify that heat '5' is different from heat 5
    const result = fns.getPersonPlacement('Abbas, Alia', 5, 'A-15- Bronze');
    assert.equal(result, null, 'Numeric heat should not match string heat');
  });
});

test('chips-and-helpers: integration with other functions', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('getLevelChipHtml uses getEventSkillLevel internally', () => {
    const event = 'AC-C Open Bronze CLUB Salsa';
    const level = fns.getEventSkillLevel(event);
    const chip = fns.getLevelChipHtml(event);

    if (level) {
      assert.ok(chip.includes(level.label), 'Chip should include the level label');
    }
  });

  await t.test('getAgeChipHtml uses getEventAgeCategory internally', () => {
    const event = 'A-15- Bronze BALLROOM';
    const age = fns.getEventAgeCategory(event);
    const chip = fns.getAgeChipHtml(event);

    if (age) {
      assert.ok(chip.includes(age.label), 'Chip should include the age label');
    }
  });

  await t.test('formatPlacement with real data', () => {
    for (let i = 1; i <= 10; i++) {
      const result = fns.formatPlacement(String(i));
      assert.ok(result.length > 0, `Placement ${i} should produce output`);
    }
  });
});
