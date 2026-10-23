"""Write the AI versions of the home page articles into news_ai.json.

For each tier and week, the template articles from news.py go to Claude, which
rewrites them as short sports-desk pieces using only the facts they contain.
Each rewrite is checked with news_ai.check() before it is saved; one that
fails is left out, and the app shows the template text in its place.

Run it after simulating a season or changing news.py. Entries whose template
text hasn't changed are skipped, so re-running only pays for what changed:

    python write_news.py                    # every tier and week
    python write_news.py --tiers "Tier 1" --weeks 10,11
    python write_news.py --dry-run          # print the first request, no API call
    python write_news.py --force            # rewrite even up-to-date entries

Needs the anthropic package and credentials (ANTHROPIC_API_KEY, or a profile
from `ant auth login`). The web app itself needs neither.
"""

import argparse
import json
import pickle
import sys

import anthropic

import news_ai
from awards import TierAwards
from league import PLAYOFF_WEEKS
from news import Season, league_news
from show_standings import WEEKS
from tourney import backfill_game_records

MODEL = 'claude-opus-5-5'

SYSTEM = """You are the news desk for a simulated dodgeball league. Each request gives you \
one tier's home page articles for one week, as draft text generated from the season's \
results. Rewrite every draft into a short, lively sports article.

Rules:
- Use only facts stated in that article's draft. Don't add results, records, history, \
injuries, quotes, coaches or anything else the draft doesn't say, and don't move facts \
between articles.
- Every number you write must appear in that article's draft (or be the tier or week \
number). Keep scores in the draft's form, such as 3–2.
- Write team and player names exactly as the draft does. Teams are singular: \
"Seattle is", "Seattle won its title".
- Return the articles in the same order, one for each draft.
- Headline: at most 10 words. Body: two to four short paragraphs, about 60 to 120 words \
in all; the first article (the lead story) may run to 150 words.
- For an "Around the league" roundup, write one sentence per result, one result per \
paragraph.
- Vary the openings and verbs across articles so the page doesn't read like a template."""

SCHEMA = {
    'type': 'object',
    'properties': {
        'articles': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'headline': {'type': 'string'},
                    'paragraphs': {'type': 'array', 'items': {'type': 'string'}},
                },
                'required': ['headline', 'paragraphs'],
                'additionalProperties': False,
            },
        },
    },
    'required': ['articles'],
    'additionalProperties': False,
}


def request(tier, week, articles):
    drafts = [{'kind': a['kind'], 'headline': a['headline'], 'paragraphs': a['paragraphs']}
              for a in articles]
    label = 'Preseason' if week == 0 else f"Week {week:g}"
    return dict(
        model=MODEL,
        max_tokens=16000,
        # Rewriting short drafts doesn't need deep reasoning
        output_config={'effort': 'medium', 'format': {'type': 'json_schema', 'schema': SCHEMA}},
        system=[{'type': 'text', 'text': SYSTEM, 'cache_control': {'type': 'ephemeral'}}],
        messages=[{'role': 'user', 'content': (
            f"{tier}, as of {label}. Drafts, lead story first:\n\n"
            + json.dumps(drafts, ensure_ascii=False, indent=2))}],
        # On a safety decline, re-run on Anthropic's recommended fallback model
        betas=['server-side-fallback-2026-07-01'],
        fallbacks='default',
    )


def rewrite(client, tier, week, articles):
    """Claude's rewrites, or None if it declined or ran out of room."""
    response = client.beta.messages.create(**request(tier, week, articles))
    if response.stop_reason in ('refusal', 'max_tokens'):
        print(f"  stopped: {response.stop_reason}")
        return None
    text = next(b.text for b in response.content if b.type == 'text')
    return json.loads(text)['articles']


def save(store):
    with open(news_ai.STORE, 'w', encoding='utf-8') as f:
        json.dump(store, f, ensure_ascii=False, indent=1)
        f.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--tiers', help='comma-separated, e.g. "Tier 1,Tier 2" (default: all)')
    parser.add_argument('--weeks', help='comma-separated, e.g. 0,1.5,10 (default: all)')
    parser.add_argument('--force', action='store_true', help='rewrite up-to-date entries too')
    parser.add_argument('--dry-run', action='store_true', help='print the first request and stop')
    args = parser.parse_args()

    with open('season_all_tiers.pkl', 'rb') as f:
        all_tiers_data = pickle.load(f)
    for tier_data in all_tiers_data.values():
        backfill_game_records(tier_data['teams'], tier_data['schedule'], tier_data['all_tourneys'])

    tiers = args.tiers.split(',') if args.tiers else list(all_tiers_data)
    weeks = ([float(w) for w in args.weeks.split(',')] if args.weeks
             else [0] + WEEKS + PLAYOFF_WEEKS)
    weeks = [int(w) if w == int(w) else w for w in weeks]

    store = {'model': MODEL, 'entries': news_ai.load()}
    client = None if args.dry_run else anthropic.Anthropic()
    written = failed = skipped = 0

    for tier in tiers:
        data = all_tiers_data[tier]
        awards = TierAwards(data['teams'], data['schedule'], data['all_tourneys'],
                            data.get('playoff_rounds', []))
        names = news_ai.tier_names(data)
        for week in weeks:
            articles = league_news(tier, data, awards, week)
            if not articles:
                continue
            k, stamp = news_ai.key(tier, week), news_ai.source_hash(articles)
            if not args.force and store['entries'].get(k, {}).get('source_hash') == stamp:
                skipped += 1
                continue
            if args.dry_run:
                req = request(tier, week, articles)
                print(json.dumps({key: req[key] for key in ('model', 'output_config', 'messages')},
                                 ensure_ascii=False, indent=2))
                return

            print(f"{tier}, week {week:g}: {len(articles)} articles")
            try:
                rewrites = rewrite(client, tier, week, articles)
            except anthropic.APIStatusError as e:
                if e.status_code < 500 and e.status_code != 429:
                    raise                    # a bad request won't fix itself on the next entry
                print(f"  API error {e.status_code}; skipped")
                failed += 1
                continue
            except anthropic.APIConnectionError:
                print("  connection error; skipped")
                failed += 1
                continue
            if rewrites is None or len(rewrites) != len(articles):
                failed += 1
                continue

            s = Season(tier, data, awards, week)
            allowed = news_ai.week_numbers(tier, week, s.next_week)
            kept = []
            for source, new in zip(articles, rewrites):
                problems = news_ai.check(new, source, names, allowed)
                if problems:
                    print(f"  kept the template for '{source['headline']}': {'; '.join(problems)}")
                    kept.append(None)    # the app falls back to the template text
                else:
                    kept.append(new)
            store['entries'][k] = {'source_hash': stamp,
                                   'articles': [new or {'headline': '', 'paragraphs': []}
                                                for new in kept]}
            save(store)                  # after every entry, so an interrupted run keeps its work
            written += 1

    print(f"Done: {written} written, {skipped} already up to date, {failed} failed.")
    if failed:
        sys.exit(1)


if __name__ == '__main__':
    main()
