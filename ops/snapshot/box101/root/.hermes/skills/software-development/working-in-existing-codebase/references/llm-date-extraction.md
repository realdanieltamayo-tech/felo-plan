# Giving an LLM the current date for relative-date extraction

When a prompt asks a model to extract dates/times from free text (emails,
messages, notes) and the text contains relative references ("Tuesday",
"tomorrow", "next Friday", "in two weeks"), the model has no ground truth
for "today" unless you supply it. Without this, the model guesses, and
wrong guesses are not obviously wrong — they parse as valid dates, just the
wrong ones (e.g. a Tuesday reference resolving to a Tuesday in the past).

## 1. Compute date context server-side, not client-side or hardcoded

Derive the user's local date, day-of-week, and UTC offset at request time.
Do NOT hardcode a fixed UTC offset for a timezone that observes DST —
it will be silently wrong for half the year.

```javascript
function getCentralTimeContext(now) {
  const isoDate = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Chicago', year: 'numeric', month: '2-digit', day: '2-digit'
  }).format(now);
  const dayOfWeek = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Chicago', weekday: 'long'
  }).format(now);
  const offsetParts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Chicago', timeZoneName: 'longOffset'
  }).formatToParts(now);
  const utcOffset = (offsetParts.find(p => p.type === 'timeZoneName') || {}).value
    .replace('GMT', '') || '-06:00';
  return { isoDate, dayOfWeek, utcOffset };
}
```

`Intl.DateTimeFormat` with `timeZoneName: 'longOffset'` returns the correct
offset for the given instant automatically (`-05:00` in summer / CDT,
`-06:00` in winter / CST for America/Chicago) — no seasonal bug to remember.

## 2. State the date context explicitly in the prompt, and what to do with it

Don't just mention the date — tell the model which reference date to resolve
against and which timezone to assume for bare times:

> Today is {dayOfWeek}, {isoDate}, and the user is in {timezone name}
> (currently UTC{utcOffset}). Resolve any relative date reference against
> this current date, not any date implied elsewhere in the source text.
> When given a bare time like "3pm" with no timezone, assume local time and
> convert to an absolute UTC timestamp.

## 3. Add a past-date rejection gate as a safety net (prompt fixes alone are not enough)

Even with correct date context in the prompt, a model can still misresolve
a date. Add a validation step that rejects (skips with a clear reason, does
not silently write) any extracted event whose start time is unreasonably in
the past relative to the same `now` used for the prompt:

```javascript
const PAST_DATE_TOLERANCE_MS = 6 * 60 * 60 * 1000; // tune per use case
if (Date.parse(ev.start_time) < now.getTime() - PAST_DATE_TOLERANCE_MS) {
  return 'start_time is in the past, likely a misparsed relative date';
}
```

Use a tolerance window, not an exact "now" cutoff — an event earlier the
same day is plausible (the source text may have been processed hours after
it arrived); a tolerance of several hours is a reasonable default, tune
down for stricter protection or up if same-day processing lag is common.
This only catches resolutions landing in the past — a date resolved wrong
but still in the future (e.g. the wrong Tuesday) will not be caught by this
gate; it is a safety net for the prompt fix, not a replacement for it.

## 4. Testing: pin "now" with an env var override, not by mocking global Date

```javascript
function getNow() {
  if (process.env.MOCK_NOW) return new Date(process.env.MOCK_NOW);
  return new Date();
}
```

Set `MOCK_NOW` before requiring the app module in your test harness so every
date-resolution and past-date-rejection assertion is deterministic. Never
set `MOCK_NOW` outside tests.

To prove the prompt actually carries the date context (not just that the
code compiles), have the mock LLM server capture the request body it
received and assert on its content directly:

```javascript
let LAST_PROMPT = null;
const mockLLM = http.createServer((req, res) => {
  let body = '';
  req.on('data', c => { body += c; });
  req.on('end', () => {
    LAST_PROMPT = JSON.parse(body).prompt;
    res.end(JSON.stringify({ response: SCRIPTED_RESPONSE }));
  });
});
// after calling the endpoint under test:
assert(LAST_PROMPT.includes('2026-09-07'), 'prompt includes today\'s date');
```
