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
});
