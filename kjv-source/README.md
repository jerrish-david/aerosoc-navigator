# KJV source index

This standalone Python 3 utility reads the existing `old|new/Book/chapter.json`
layout and creates `kjv.index.json`. The original Bible files stay untouched.
It requires no extra packages and does not connect to Zoom or an AI provider.

## Build once

```sh
cd '/Users/davidpath/Documents/New project/kjv-source'
python3 kjv_source.py build
```

## Continuously refresh when source files change

```sh
python3 kjv_source.py build --watch --interval 5
```

Keep this command running in a terminal; Ctrl+C stops it. It checks every five
seconds, parses only new or changed chapter files, removes deleted chapters from
the next index, and replaces the output atomically after a successful scan.
Invalid input leaves the last good output in place. An empty or missing source is
treated as an error, not an instruction to clear the index. Change detection uses
file size and modification time; edits that preserve both require rebuilding
to a new output path. Only run one writer for a given output file.

The KJV text normally does not change, so a single build is usually sufficient.
This watcher checks local files; it does not download updates.

## Query and format

For abbreviated input and numbered messages matching your meeting format:

```sh
python3 kjv_source.py reference '1 cor 6 7-10'
```

This returns `reference`, `translation`, `messages`, `lengths`, `limit`, and
`length_unit`. Each string in `messages` is a separate chat message. It uses:

```text
📖 1 Corinthians 6:7-10 — KJV [1/2]

6:7 ...

6:8 ...
```

The formatter keeps whole verses together when they fit, splits a verse only if
it cannot fit on an empty page, and repeats the verse number on continuation
pages. It recalculates pagination until the total page count is stable. Headers,
emoji, spaces, newlines, and page numbers all count toward the limit.
Lengths use UTF-16 code units, matching JavaScript string `.length`; the book emoji
counts as two. This is a configurable budgeting convention, not verification of
Zoom's particular client or API limit. No text is paraphrased or omitted.

`book_aliases.json` covers all 66 books and is loaded once when the module loads.
Add aliases there and restart the engine to use them. Case, periods, underscores,
and spaces are normalized: `1Cor.6:7-10`, `1 cor 6 7-10`, and
`1 Corinthians 6:7–10` resolve to the same passage. Both `Psalm` and `Psalms` work.
Unknown abbreviations, nonexistent verses, and reversed ranges return errors.
Only a single chapter per request is supported; cross-chapter and multiple-passage
syntax is deliberately rejected. Aliases are explicit, not guessed from prefixes.

The older one-verse-per-message command is also available:

```sh
python3 kjv_source.py query John 3 16 --end 18
python3 kjv_source.py query '1 Corinthians' 13 4 --end 7 --limit 500
```

The result includes original verse records and an array of ready-to-copy message
strings. Each message includes a reference and translation label within the
configured limit. Long verses split at spaces where possible, repeat the
reference, and preserve their text across chunks. Each verse starts a new message.
The default 500 is your requested budget, not a verified platform-wide Zoom limit.
Length counts Python Unicode code points. Validate the final strings using your
engine's counting convention if you add emoji or other Unicode-rich formatting.

## Connect your existing engine

For the abbreviated-reference flow, initialize once and call the function for
each request:

```python
from kjv_source import DEFAULT_OUTPUT, load_index, render_reference

index = load_index(DEFAULT_OUTPUT)

def handle_reference(user_input):
    return render_reference(index, user_input, limit=500)
```

Call `handle_reference('1 cor 6 7-10')` and pass each returned `messages` item to
your existing output layer separately. Do not concatenate the messages. The CLI
examples start a new process and load JSON each time, so use the function inside
your running engine for interactive performance.

The runtime path is abbreviation map → parsed reference → in-memory chapter and
verse lookup → exact text formatting → numbered messages. Parsing depends on
input length; retrieval and formatting depend on the requested passage, not the
size of the entire Bible. There is no model call in this path.

### Mapping versus MCP

Use the mapping and a direct function call when the engine and this code run in
the same process. MCP is an optional protocol adapter for exposing the same
function to compatible AI applications; it does not replace the alias map or
index. See the [official MCP architecture](https://modelcontextprotocol.io/specification/2025-06-18/architecture).

If your engine needs MCP, expose one tool, `format_bible_reference`, with
`reference` (string) and `limit` (integer, default 500). Load the index once in the
server and have the handler call `render_reference`. Return its structured result
directly, including the separate message strings. An MCP server is not included
in this utility. Use the model for requests that actually need interpretation;
route recognized explicit Bible references directly to this function.

Load the JSON once at startup and keep it in memory. Reading and parsing the whole
file on every query would lose the main performance benefit. For example, in
JavaScript with the parsed JSON held in `index`:

```js
const verseText = index.chapters['john:3'].verses['16'];
```

Book keys are lowercase with spaces (e.g. `1 corinthians:13`). Chapter and verse
keys are strings. Chapter entries also contain book name, chapter number, and
testament. The `files` property is ingestion metadata; your engine can ignore it.

For a Python engine with this directory on its module path:

```python
from kjv_source import load_index, lookup, format_messages

index = load_index('kjv.index.json')
records = lookup(index, 'John', 3, 16, 18)
messages = format_messages(records, limit=500)
```

If the source changes, reload the JSON after its modification time changes and
replace your engine's cached index only after parsing succeeds. The extraction
watcher does not automatically refresh another process's in-memory cache.

Direct reference lookups use dictionary keys; they do not scan all chapter files.
This is not a keyword or semantic search index. For topic queries, add a separate
search index and return the original verse text from this source.

## Verification

```sh
python3 -m unittest discover -s . -p 'test_kjv_source.py'
```

Tests cover the example passage, alias coverage, invalid references, all indexed
chapters, exact text preservation, long verses, multi-digit pagination, and emoji
length accounting. They read the local index and do not contact external services.
