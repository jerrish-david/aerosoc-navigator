import argparse
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time


DEFAULT_SOURCE = Path('/Users/davidpath/bible-translations/json/KJV')
DEFAULT_OUTPUT = Path(__file__).parent / 'kjv.index.json'
REFERENCE_PATTERN = re.compile(
    r'(?P<book>[1-3]?[\s._]*[a-zA-Z][a-zA-Z ._]*?)\s*'
    r'(?P<chapter>[0-9]+)(?:\s*:\s*|\s+)(?P<start>[0-9]+)'
    r'(?:\s*[-–—]\s*(?P<end>[0-9]+))?'
)


def alias_key(book):
    return re.sub(r'[\s._]+', '', book).casefold()


def load_aliases():
    with Path(__file__).with_name('book_aliases.json').open(encoding='utf-8') as stream:
        groups = json.load(stream)
    aliases = {}
    for canonical, names in groups.items():
        for name in [canonical, *names]:
            key = alias_key(name)
            if key in aliases and aliases[key] != canonical:
                raise ValueError(f'Ambiguous book alias: {name}')
            aliases[key] = canonical
    return aliases


BOOK_ALIASES = load_aliases()


def parse_reference(reference):
    match = REFERENCE_PATTERN.fullmatch(reference.strip())
    if match is None:
        raise ValueError('Use a single-chapter reference such as "1 cor 6 7-10"')
    book = BOOK_ALIASES.get(alias_key(match['book']))
    if book is None:
        raise ValueError(f'Unknown book abbreviation: {match["book"].strip()}')
    chapter, start = int(match['chapter']), int(match['start'])
    end = int(match['end']) if match['end'] else start
    if chapter < 1 or start < 1 or end < start:
        raise ValueError('Use positive chapter/verse numbers and an ascending range')
    return book, chapter, start, end


def book_key(book):
    return ' '.join(book.replace('_', ' ').split()).casefold()


def load_index(path):
    with Path(path).open(encoding='utf-8') as stream:
        index = json.load(stream)
    if index.get('version') != 1:
        raise ValueError('Unsupported index version')
    return index


def sync(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not source.is_dir():
        raise ValueError(f'Source folder does not exist: {source}')
    if output == source or source in output.parents:
        raise ValueError('Keep the output outside the source folder')
    previous = load_index(output) if output.exists() else {}
    if previous.get('source') != str(source):
        previous = {}
    files = sorted(source.rglob('*.json'))
    if not files:
        raise ValueError('No JSON files found; keeping any existing index')
    chapters, signatures = {}, {}
    parsed = 0
    for path in files:
        relative = path.relative_to(source)
        if len(relative.parts) != 3 or relative.parts[0] not in ('old', 'new'):
            raise ValueError(f'Expected testament/book/chapter.json: {relative}')
        chapter = int(path.stem)
        if chapter < 1:
            raise ValueError(f'Invalid chapter: {relative}')
        key = f'{book_key(path.parent.name)}:{chapter}'
        if key in chapters:
            raise ValueError(f'Duplicate chapter: {relative}')
        before = path.stat()
        signature = [before.st_mtime_ns, before.st_size]
        signatures[str(relative)] = signature
        if (previous.get('files', {}).get(str(relative)) == signature
                and key in previous.get('chapters', {})):
            chapters[key] = previous['chapters'][key]
            continue
        with path.open(encoding='utf-8') as stream:
            verses = json.load(stream)
        after = path.stat()
        if signature != [after.st_mtime_ns, after.st_size]:
            raise ValueError(f'File changed during reading; retry: {relative}')
        if not isinstance(verses, dict) or not verses:
            raise ValueError(f'Expected a nonempty verse object: {relative}')
        for verse, verse_text in verses.items():
            if (not verse.isdecimal() or int(verse) < 1 or str(int(verse)) != verse
                    or not isinstance(verse_text, str) or not verse_text.strip()):
                raise ValueError(f'Invalid verse {verse!r}: {relative}')
        chapters[key] = {
            'book': path.parent.name.replace('_', ' '),
            'chapter': chapter,
            'testament': relative.parts[0],
            'verses': dict(sorted(verses.items(), key=lambda item: int(item[0]))),
        }
        parsed += 1
    changed = signatures != previous.get('files')
    if changed:
        index = {
            'version': 1, 'translation': 'KJV', 'source': str(source),
            'files': signatures, 'chapters': chapters,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=output.parent, delete=False
            ) as stream:
                temporary = Path(stream.name)
                json.dump(index, stream, ensure_ascii=False, separators=(',', ':'))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, output)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
    return {
        'chapters': len(chapters),
        'verses': sum(len(entry['verses']) for entry in chapters.values()),
        'parsed_files': parsed, 'updated': changed, 'output': str(output),
    }


def lookup(index, book, chapter, start, end=None):
    end = start if end is None else end
    if chapter < 1 or start < 1 or end < start:
        raise ValueError('Use positive chapter/verse numbers and an ascending range')
    entry = index['chapters'].get(f'{book_key(book)}:{chapter}')
    if entry is None:
        raise ValueError(f'Chapter not found: {book} {chapter}')
    if end - start + 1 > len(entry['verses']) or any(
        str(verse) not in entry['verses'] for verse in range(start, end + 1)
    ):
        raise ValueError(f'Verse range not found: {book} {chapter}:{start}-{end}')
    return [
        {'reference': f"{entry['book']} {chapter}:{verse}",
         'text': entry['verses'][str(verse)]}
        for verse in range(start, end + 1)
    ]


def format_messages(records, limit=500):
    messages = []
    for record in records:
        prefix = f"{record['reference']} (KJV)\n"
        capacity = limit - len(prefix)
        if capacity < 1:
            raise ValueError('Message limit must leave space after the reference')
        remaining = record['text']
        while remaining:
            cut = min(capacity, len(remaining))
            if len(remaining) > capacity:
                boundary = remaining.rfind(' ', 0, capacity)
                if boundary > 0:
                    cut = boundary + 1
            messages.append(prefix + remaining[:cut])
            remaining = remaining[cut:]
    return messages


def message_length(text):
    return len(text.encode('utf-16-le')) // 2


def split_prefix(text, capacity):
    used, cut = 0, 0
    for position, character in enumerate(text):
        width = 2 if ord(character) > 0xFFFF else 1
        if used + width > capacity:
            break
        used += width
        cut = position + 1
    if cut == 0:
        raise ValueError('Message limit leaves no room for verse text')
    if cut < len(text):
        boundary = text.rfind(' ', 0, cut)
        if boundary > 0:
            cut = boundary + 1
    return text[:cut], text[cut:]


def pack_passage(records, reference, limit, total):
    messages, body = [], ''
    for record in records:
        label = record['reference'].rsplit(' ', 1)[1] + ' '
        remaining = record['text']
        while remaining:
            header = f'📖 {reference} — KJV [{len(messages) + 1}/{total}]\n\n'
            candidate = (body + '\n\n' if body else '') + label + remaining
            if message_length(header + candidate) <= limit:
                body = candidate
                break
            if body:
                messages.append(header + body)
                body = ''
                continue
            capacity = limit - message_length(header + label)
            piece, remaining = split_prefix(remaining, capacity)
            messages.append(header + label + piece)
    if body:
        header = f'📖 {reference} — KJV [{len(messages) + 1}/{total}]\n\n'
        messages.append(header + body)
    return messages


def render_reference(index, reference, limit=500):
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError('Message limit must be a positive integer')
    book, chapter, start, end = parse_reference(reference)
    records = lookup(index, book, chapter, start, end)
    canonical = f'{book} {chapter}:{start}' + (f'-{end}' if end != start else '')
    total = 1
    while True:
        messages = pack_passage(records, canonical, limit, total)
        if len(messages) == total:
            return {
                'reference': canonical, 'translation': 'KJV', 'messages': messages,
                'lengths': [message_length(message) for message in messages],
                'limit': limit, 'length_unit': 'utf16_code_units',
            }
        total = len(messages)


def main():
    parser = argparse.ArgumentParser(description='Build and query a KJV JSON index')
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('build')
    build.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    build.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    build.add_argument('--watch', action='store_true')
    build.add_argument('--interval', type=float, default=5)
    query = commands.add_parser('query')
    query.add_argument('book')
    query.add_argument('chapter', type=int)
    query.add_argument('verse', type=int)
    query.add_argument('--end', type=int)
    query.add_argument('--index', type=Path, default=DEFAULT_OUTPUT)
    query.add_argument('--limit', type=int, default=500)
    reference = commands.add_parser('reference')
    reference.add_argument('text')
    reference.add_argument('--index', type=Path, default=DEFAULT_OUTPUT)
    reference.add_argument('--limit', type=int, default=500)
    args = parser.parse_args()
    if args.command == 'reference':
        result = render_reference(load_index(args.index), args.text, args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == 'query':
        records = lookup(load_index(args.index), args.book, args.chapter, args.verse, args.end)
        print(json.dumps({'verses': records, 'messages': format_messages(records, args.limit)},
                         ensure_ascii=False, indent=2))
        return
    if not math.isfinite(args.interval) or args.interval <= 0:
        parser.error('--interval must be finite and positive')
    while True:
        try:
            print(json.dumps(sync(args.source, args.output)), flush=True)
        except (OSError, ValueError) as error:
            if not args.watch:
                raise
            print(f'Sync failed; keeping last good index: {error}', file=sys.stderr, flush=True)
        if not args.watch:
            break
        time.sleep(args.interval)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, KeyError) as error:
        sys.exit(f'Error: {error}')
