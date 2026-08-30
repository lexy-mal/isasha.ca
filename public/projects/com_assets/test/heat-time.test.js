'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { loadComFunctions } = require('./extract-com-functions');

const TIME_SYMBOLS = [
  'parseHeatTime',
  'parsedHour24',
  'parseLocalDate',
  'formatDisplayTime',
  'getEventDateFromTimeString',
  'compareEventsByTime',
  'isEventCompleted',
  'formatDurationMs',
  'truncateEventName',
  'getNextAwardsForPerson',
  'formatAwardsCountdownTime',
  'buildPersonAwardsCountdownText',
];

const NATIONAL_2026_PRELUDE = `
let competitionStartDate = new Date(2026, 7, 27);
let competitionEndDate = new Date(2026, 7, 30);
competitionEndDate.setHours(23, 59, 59, 999);
`;

test('parseHeatTime: 12-hour and 24-hour formats', async (t) => {
  const fns = loadComFunctions(TIME_SYMBOLS);

  await t.test('parses Imperial Cup 12-hour times', () => {
    const parsed = fns.parseHeatTime('03:38PM Sunday');
    assert.equal(parsed.hour, 3);
    assert.equal(parsed.minute, 38);
    assert.equal(parsed.meridiem, 'PM');
    assert.equal(parsed.dayName, 'Sunday');
    assert.equal(fns.parsedHour24(parsed), 15);
  });

  await t.test('parses National 2026 24-hour times', () => {
    const parsed = fns.parseHeatTime('10:23 Sunday Later rounds: 7@10:41 Sunday');
    assert.equal(parsed.hour, 10);
    assert.equal(parsed.minute, 23);
    assert.equal(parsed.meridiem, null);
    assert.equal(parsed.dayName, 'Sunday');
    assert.equal(fns.parsedHour24(parsed), 10);
  });

  await t.test('parses evening 24-hour times', () => {
    const parsed = fns.parseHeatTime('20:23 Friday Later rounds: 4@21:11 Friday');
    assert.equal(fns.parsedHour24(parsed), 20);
    assert.equal(parsed.dayName, 'Friday');
  });

  await t.test('parses awards-style 24-hour times', () => {
    const parsed = fns.parseHeatTime('22:10 Friday');
    assert.equal(fns.parsedHour24(parsed), 22);
    assert.equal(parsed.minute, 10);
    assert.equal(parsed.dayName, 'Friday');
  });

  await t.test('returns null for empty input', () => {
    assert.equal(fns.parseHeatTime(''), null);
    assert.equal(fns.parseHeatTime(null), null);
  });
});

test('formatDisplayTime', async (t) => {
  const fns = loadComFunctions(TIME_SYMBOLS);

  await t.test('formats 12-hour times unchanged', () => {
    assert.equal(fns.formatDisplayTime('03:38PM Sunday'), '3:38PM Sunday');
  });

  await t.test('formats 24-hour times', () => {
    assert.equal(
      fns.formatDisplayTime('10:23 Sunday Later rounds: 7@10:41 Sunday'),
      '10:23 Sunday'
    );
  });

  await t.test('formats awards times', () => {
    assert.equal(fns.formatDisplayTime('09:16 Sunday'), '9:16 Sunday');
  });

  await t.test('returns TBD for missing time', () => {
    assert.equal(fns.formatDisplayTime(''), 'TBD');
  });
});

test('compareEventsByTime', async (t) => {
  const fns = loadComFunctions(TIME_SYMBOLS, NATIONAL_2026_PRELUDE);

  await t.test('orders events chronologically within the competition week', () => {
    const earlier = { heat: 'Heat 713', event: 'A', time: '10:23 Sunday' };
    const later = { heat: 'Heat 714', event: 'B', time: '10:27 Sunday' };
    assert.ok(fns.compareEventsByTime(earlier, later) < 0);
    assert.ok(fns.compareEventsByTime(later, earlier) > 0);
  });

  await t.test('maps Sunday events to competition Sunday, not calendar week Sunday', () => {
    const sunday = fns.getEventDateFromTimeString('10:23 Sunday');
    assert.equal(sunday.getFullYear(), 2026);
    assert.equal(sunday.getMonth(), 7);
    assert.equal(sunday.getDate(), 30);
    assert.equal(sunday.getDay(), 0);
  });

  await t.test('maps awards times onto competition dates', () => {
    const awards = fns.getEventDateFromTimeString('22:10 Friday');
    assert.equal(awards.getFullYear(), 2026);
    assert.equal(awards.getMonth(), 7);
    assert.equal(awards.getDate(), 28);
    assert.equal(awards.getHours(), 22);
    assert.equal(awards.getMinutes(), 10);
  });
});

test('getNextAwardsForPerson', async (t) => {
  // Use a future competition week so award times are always ahead of wall clock.
  const futurePrelude = `
let competitionStartDate = new Date(2099, 7, 27);
let competitionEndDate = new Date(2099, 7, 30);
competitionEndDate.setHours(23, 59, 59, 999);
`;
  const fns = loadComFunctions(TIME_SYMBOLS, futurePrelude);

  await t.test('picks earliest future awards time', () => {
    const personData = {
      entries: [
        { heat: 'Heat 2', event: 'Later Event', time: '20:00 Sunday', awards: '22:00 Sunday' },
        { heat: 'Heat 1', event: 'Earlier Event', time: '08:00 Sunday', awards: '09:00 Sunday' },
        { heat: 'Heat 3', event: 'No Awards', time: '10:00 Sunday', awards: null },
      ]
    };
    const next = fns.getNextAwardsForPerson(personData);
    assert.equal(next.heat, 'Heat 1');
    assert.equal(next.event, 'Earlier Event');
    assert.equal(next.originalTime, '09:00 Sunday');
  });

  await t.test('returns null when awards missing', () => {
    assert.equal(fns.getNextAwardsForPerson({ entries: [] }), null);
    assert.equal(
      fns.getNextAwardsForPerson({
        entries: [{ heat: 'H', event: 'E', time: '10:00 Sunday', awards: null }]
      }),
      null
    );
    assert.equal(fns.getNextAwardsForPerson(null), null);
  });
});

test('formatAwardsCountdownTime / buildPersonAwardsCountdownText', async (t) => {
  const fns = loadComFunctions(TIME_SYMBOLS, NATIONAL_2026_PRELUDE);

  await t.test('formats awards countdown text', () => {
    const future = new Date(Date.now() + 90 * 60 * 1000);
    const text = fns.formatAwardsCountdownTime({
      heat: 'Heat 672',
      event: 'AC-JV Pre-Champ BALLROOM',
      time: future
    });
    assert.match(text, /^🏆 Awards in /);
    assert.match(text, /Heat 672/);
    assert.match(text, /AC-JV Pre-Champ/);
  });

  await t.test('returns empty string when no next awards', () => {
    assert.equal(fns.formatAwardsCountdownTime(null), '');
    assert.equal(
      fns.buildPersonAwardsCountdownText({
        entries: [{ heat: 'H', event: 'E', time: '10:00 Sunday', awards: null }]
      }),
      ''
    );
  });
});
