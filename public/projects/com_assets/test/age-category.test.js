'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { loadAllComFunctions } = require('./extract-com-functions');

test('age-category: named age brackets', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('JV1 returns Juvenile I with correct age bounds', () => {
    const result = fns.getEventAgeCategory('A-JV1 Bronze BALLROOM');
    assert.equal(result.label, 'Juvenile I — Under 10');
    assert.equal(result.minAge, 0);
    assert.equal(result.maxAge, 10);
    assert.equal(result.approx, undefined);
  });

  await t.test('JV2 returns Juvenile II with correct age bounds', () => {
    const result = fns.getEventAgeCategory('AC-JV2 Silver AMATEUR BALLROOM');
    assert.equal(result.label, 'Juvenile II — Ages 10–11');
    assert.equal(result.minAge, 10);
    assert.equal(result.maxAge, 11);
  });

  await t.test('JV (combined) returns Juvenile with Under 12 span', () => {
    const result = fns.getEventAgeCategory('A-JV Ouvert / Open BALLROOM');
    assert.equal(result.label, 'Juvenile — Under 12');
    assert.equal(result.minAge, 0);
    assert.equal(result.maxAge, 12);
  });

  await t.test('JR1 returns Junior I with correct age bounds', () => {
    const result = fns.getEventAgeCategory('G-JR1 Bronze SOLO');
    assert.equal(result.label, 'Junior I — Ages 12–13');
    assert.equal(result.minAge, 12);
    assert.equal(result.maxAge, 13);
  });

  await t.test('JR2 returns Junior II with correct age bounds', () => {
    const result = fns.getEventAgeCategory('A-JR2 Silver BALLROOM');
    assert.equal(result.label, 'Junior II — Ages 14–15');
    assert.equal(result.minAge, 14);
    assert.equal(result.maxAge, 15);
  });

  await t.test('JR (combined) returns Junior with 12-15 span', () => {
    const result = fns.getEventAgeCategory('L-JR Argent / Silver LATIN');
    assert.equal(result.label, 'Junior — Ages 12–15');
    assert.equal(result.minAge, 12);
    assert.equal(result.maxAge, 15);
  });

  await t.test('YTH returns Youth with 16-18 span', () => {
    const result = fns.getEventAgeCategory('A-YTH Débutant / Beginner BALLROOM');
    assert.equal(result.label, 'Youth — Ages 16–18');
    assert.equal(result.minAge, 16);
    assert.equal(result.maxAge, 18);
  });

  await t.test('Y (shorthand) returns Youth with 16-18 span', () => {
    const result = fns.getEventAgeCategory('G-Y Or / Gold Waltz');
    assert.equal(result.label, 'Youth — Ages 16–18');
    assert.equal(result.minAge, 16);
    assert.equal(result.maxAge, 18);
  });

  await t.test('U21 returns Under 21 with 19-20 span', () => {
    const result = fns.getEventAgeCategory('A-U21 Bronze LATIN');
    assert.equal(result.label, 'Under 21 — Ages 19–20');
    assert.equal(result.minAge, 19);
    assert.equal(result.maxAge, 20);
  });

  await t.test('U12 returns Under 12', () => {
    const result = fns.getEventAgeCategory('AC-U12 Silver AMATEUR');
    assert.equal(result.label, 'Under 12');
    assert.equal(result.minAge, 0);
    assert.equal(result.maxAge, 12);
  });

  await t.test('YO (Young Adult) returns with approx flag', () => {
    const result = fns.getEventAgeCategory('A-YO Argent / Silver BALLROOM');
    assert.equal(result.label, 'Young Adult (approx.)');
    assert.equal(result.minAge, 19);
    assert.equal(result.maxAge, 25);
    assert.equal(result.approx, true);
  });

  await t.test('AD (Adult combined) returns Adult (19+) without approx', () => {
    const result = fns.getEventAgeCategory('A-AD Or / Gold BALLROOM');
    assert.equal(result.label, 'Adult (19+)');
    assert.equal(result.minAge, 19);
    assert.equal(result.approx, undefined);
  });

  await t.test('AD1 returns Adult I with approx flag', () => {
    const result = fns.getEventAgeCategory('AC-AD1 Silver AMATEUR');
    assert.equal(result.label, 'Adult I (approx.)');
    assert.equal(result.minAge, 19);
    assert.equal(result.maxAge, 25);
    assert.equal(result.approx, true);
  });

  await t.test('AD2 returns Adult II with approx flag', () => {
    const result = fns.getEventAgeCategory('A-AD2 Bronze BALLROOM');
    assert.equal(result.label, 'Adult II (approx.)');
    assert.equal(result.minAge, 26);
    assert.equal(result.maxAge, 35);
    assert.equal(result.approx, true);
  });

  await t.test('AD3 returns Adult III with approx flag', () => {
    const result = fns.getEventAgeCategory('A-AD3 Gold LATIN');
    assert.equal(result.label, 'Adult III (approx.)');
    assert.equal(result.minAge, 36);
    assert.equal(result.maxAge, 45);
    assert.equal(result.approx, true);
  });

  await t.test('AD4 returns Adult IV with approx flag', () => {
    const result = fns.getEventAgeCategory('AC-AD4 Open AMATEUR');
    assert.equal(result.label, 'Adult IV (approx.)');
    assert.equal(result.minAge, 46);
    assert.equal(result.maxAge, 55);
    assert.equal(result.approx, true);
  });

  await t.test('AD5 returns Adult V with approx flag', () => {
    const result = fns.getEventAgeCategory('A-AD5 Ouvert / Open BALLROOM');
    assert.equal(result.label, 'Adult V (approx.)');
    assert.equal(result.minAge, 56);
    assert.equal(result.approx, true);
  });
});

test('age-category: numeric brackets', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('6U returns 6 & Under', () => {
    const result = fns.getEventAgeCategory('A-6U Bronze BALLROOM');
    assert.equal(result.label, '6 & Under');
    assert.equal(result.minAge, 0);
    assert.equal(result.maxAge, 6);
  });

  await t.test('7U returns 7 & Under', () => {
    const result = fns.getEventAgeCategory('A-7U Silver LATIN');
    assert.equal(result.label, '7 & Under');
    assert.equal(result.minAge, 0);
    assert.equal(result.maxAge, 7);
  });

  await t.test('7 (range 7-11) returns Ages 7–11', () => {
    const result = fns.getEventAgeCategory('A-7-11 Gold BALLROOM');
    assert.equal(result.label, 'Ages 7–11');
    assert.equal(result.minAge, 7);
    assert.equal(result.maxAge, 11);
  });

  await t.test('11U returns 11 & Under', () => {
    const result = fns.getEventAgeCategory('AC-11U Open AMATEUR');
    assert.equal(result.label, '11 & Under');
    assert.equal(result.minAge, 0);
    assert.equal(result.maxAge, 11);
  });

  await t.test('12+ returns 12 & Over (open-ended)', () => {
    const result = fns.getEventAgeCategory('A-12+ Argent / Silver BALLROOM');
    assert.equal(result.label, '12 & Over');
    assert.equal(result.minAge, 12);
    assert.equal(result.maxAge, undefined);
  });

  await t.test('15- returns 15 & Under', () => {
    const result = fns.getEventAgeCategory('A-15- Argent / Silver BALLROOM SOLO (W/T/Q)');
    assert.equal(result.label, '15 & Under');
    assert.equal(result.minAge, 0);
    assert.equal(result.maxAge, 15);
  });

  await t.test('16+ returns 16 & Over', () => {
    const result = fns.getEventAgeCategory('A-16+ Ouvert / Open BALLROOM');
    assert.equal(result.label, '16 & Over');
    assert.equal(result.minAge, 16);
    assert.equal(result.maxAge, undefined);
  });

  await t.test('19+ returns 19 & Over', () => {
    const result = fns.getEventAgeCategory('A-19+ Argent / Silver BALLROOM SOLO Foxtrot');
    assert.equal(result.label, '19 & Over');
    assert.equal(result.minAge, 19);
    assert.equal(result.maxAge, undefined);
  });

  await t.test('30+ returns 30 & Over', () => {
    const result = fns.getEventAgeCategory('AC-30+ Silver AMATEUR BALLROOM');
    assert.equal(result.label, '30 & Over');
    assert.equal(result.minAge, 30);
    assert.equal(result.maxAge, undefined);
  });

  await t.test('36+ returns 36 & Over', () => {
    const result = fns.getEventAgeCategory('A-36+ Gold BALLROOM');
    assert.equal(result.label, '36 & Over');
    assert.equal(result.minAge, 36);
    assert.equal(result.maxAge, undefined);
  });

  await t.test('40+ returns 40 & Over', () => {
    const result = fns.getEventAgeCategory('AC-40+ Bronze AMATEUR LATIN');
    assert.equal(result.label, '40 & Over');
    assert.equal(result.minAge, 40);
    assert.equal(result.maxAge, undefined);
  });

  await t.test('50+ returns 50 & Over', () => {
    const result = fns.getEventAgeCategory('A-50+ Argent / Silver BALLROOM');
    assert.equal(result.label, '50 & Over');
    assert.equal(result.minAge, 50);
    assert.equal(result.maxAge, undefined);
  });
});

test('age-category: skill/section codes (NOT ages) return null', async (t) => {
  const fns = loadAllComFunctions();

  const skillCodes = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'JB', 'JU', 'PD'];

  for (const code of skillCodes) {
    await t.test(`${code} returns null (not an age code)`, () => {
      const result = fns.getEventAgeCategory(`G-${code} Bronze SOLO`);
      assert.equal(result, null, `Code ${code} should return null`);
    });
  }
});

test('age-category: events with no code return null', async (t) => {
  const fns = loadAllComFunctions();

  await t.test('event with empty code slot returns null', () => {
    const result = fns.getEventAgeCategory('G- Or / Gold Milonga');
    assert.equal(result, null);
  });

  await t.test('PRO event (no code) returns null', () => {
    const result = fns.getEventAgeCategory('PRO BALLROOM Championnat National Canadien');
    assert.equal(result, null);
  });

  await t.test('event with no prefix at all returns null', () => {
    const result = fns.getEventAgeCategory('Challenge Cup BALLROOM');
    assert.equal(result, null);
  });
});

test('age-category: tie-breaking on maxAge for sorting', async (t) => {
  const fns = loadAllComFunctions();

  // Test the specific case mentioned in the docs: Under 10 < Under 12 < 15 & Under
  // All have minAge: 0, but maxAge differs

  await t.test('JV1 (maxAge: 10) should have lower maxAge than JV (maxAge: 12)', () => {
    const jv1 = fns.getEventAgeCategory('A-JV1 Bronze');
    const jv = fns.getEventAgeCategory('A-JV Bronze');
    assert.equal(jv1.minAge, 0);
    assert.equal(jv.minAge, 0);
    assert.ok(jv1.maxAge < jv.maxAge, 'JV1 maxAge should be < JV maxAge');
  });

  await t.test('JV (maxAge: 12) should have lower maxAge than 15- (maxAge: 15)', () => {
    const jv = fns.getEventAgeCategory('A-JV Argent / Silver');
    const under15 = fns.getEventAgeCategory('A-15- Bronze BALLROOM');
    assert.equal(jv.minAge, 0);
    assert.equal(under15.minAge, 0);
    assert.ok(jv.maxAge < under15.maxAge, 'JV maxAge should be < 15- maxAge');
  });

  await t.test('Regression: all three Under X brackets should be ordered by maxAge', () => {
    const jv1 = fns.getEventAgeCategory('A-JV1 Bronze');
    const under12 = fns.getEventAgeCategory('AC-U12 Silver');
    const under15 = fns.getEventAgeCategory('A-15- Gold BALLROOM');

    assert.equal(jv1.minAge, 0);
    assert.equal(under12.minAge, 0);
    assert.equal(under15.minAge, 0);

    assert.ok(jv1.maxAge < under12.maxAge, 'JV1 (10) < U12 (12)');
    assert.ok(under12.maxAge < under15.maxAge, 'U12 (12) < 15- (15)');
  });
});
