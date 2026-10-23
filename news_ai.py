"""AI-written versions of the home page articles, with the template text from
news.py as the fallback.

write_news.py asks Claude to rewrite each (tier, week)'s template articles and
saves the results in news_ai.json, keyed by tier and week and stamped with a
hash of the template text they were written from. The app shows an AI article
only when its stamp still matches (so a change to news.py never serves prose
about facts that have since changed) and it passes check(): it may name no
team or player and use no number that its template article doesn't."""

import hashlib
import json
import os
import re

STORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'news_ai.json')

# Number words are checked as numbers. 'one', 'first' and 'second' are left
# out: they turn up in ordinary phrasing ("one of", "first title").
WORD_NUMBERS = {word: str(n) for n, word in enumerate(
    ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
     'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen',
     'eighteen', 'nineteen', 'twenty']) if n >= 2}
WORD_NUMBERS.update({word: str(n) for n, word in enumerate(
    ['zeroth', 'first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth',
     'ninth', 'tenth', 'eleventh', 'twelfth', 'thirteenth', 'fourteenth', 'fifteenth',
     'sixteenth', 'seventeenth', 'eighteenth', 'nineteenth', 'twentieth']) if n >= 3})
WORD_RE = re.compile(r'\b(' + '|'.join(WORD_NUMBERS) + r')\b', re.IGNORECASE)
NUMBER_RE = re.compile(r'\d+(?:\.\d+)?')


def key(tier, week):
    return f"{tier}|{week:g}"


def source_hash(articles):
    """A stamp for the template articles an AI rewrite was made from."""
    text = json.dumps([[a['kind'], a['headline'], a['paragraphs']] for a in articles],
                      ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def article_text(article):
    return ' '.join([article['headline']] + list(article['paragraphs']))


def numbers(text):
    text = WORD_RE.sub(lambda m: WORD_NUMBERS[m.group(1).lower()], text)
    return set(NUMBER_RE.findall(text))


def tier_names(tier_data):
    """Every team and player name in a tier, as articles write them."""
    teams = tier_data['teams']
    return ({t.team_name for t in teams} |
            {p.name.title() for t in teams for p in t.players})


def names_in(text, names):
    """The names a text uses. Longest names are matched first and blanked out,
    so a player named 'Raleigh Abernathy' doesn't also count as the team
    'Raleigh'."""
    used = set()
    for n in sorted(names, key=len, reverse=True):
        pattern = r'(?<!\w)' + re.escape(n) + r'(?!\w)'
        if re.search(pattern, text):
            used.add(n)
            text = re.sub(pattern, ' ', text)
    return used


def check(rewrite, source, names, allowed_numbers=()):
    """Problems with an AI rewrite of one template article, [] if none: every
    number and every team or player name it uses must appear in the source
    article (numbers may also come from allowed_numbers, e.g. the week)."""
    problems = []
    if not isinstance(rewrite.get('headline'), str) or not rewrite['headline'].strip():
        problems.append('missing headline')
    paragraphs = rewrite.get('paragraphs')
    if not isinstance(paragraphs, list) or not paragraphs or not all(
            isinstance(p, str) and p.strip() for p in paragraphs):
        problems.append('missing paragraphs')
    if problems:
        return problems

    text, src = article_text(rewrite), article_text(source)
    extra = numbers(text) - numbers(src) - {str(n) for n in allowed_numbers}
    if extra:
        problems.append(f"numbers not in the source: {', '.join(sorted(extra))}")
    missing = sorted(names_in(text, names) - names_in(src, names))
    if missing:
        problems.append(f"names not in the source: {', '.join(missing)}")
    return problems


def week_numbers(tier, week, next_week):
    """Numbers any article for a week may use: the tier and the weeks."""
    found = set(NUMBER_RE.findall(tier))
    found |= {f"{w:g}" for w in (week, next_week) if w is not None}
    return found


def load():
    """The saved rewrites, {key: entry}; empty if there are none."""
    try:
        with open(STORE, encoding='utf-8') as f:
            return json.load(f).get('entries', {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def merge(articles, entry, names, allowed_numbers=()):
    """The template articles with each one replaced by its AI rewrite where
    the rewrite is current and passes check()."""
    if not entry or entry.get('source_hash') != source_hash(articles):
        return articles
    rewrites = entry.get('articles', [])
    if len(rewrites) != len(articles):
        return articles
    merged = []
    for source, rewrite in zip(articles, rewrites):
        if check(rewrite, source, names, allowed_numbers):
            merged.append(source)
        else:
            merged.append({'kind': source['kind'], 'headline': rewrite['headline'],
                           'paragraphs': rewrite['paragraphs'], 'ai': True})
    return merged
