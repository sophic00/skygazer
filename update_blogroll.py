# /// script
# dependencies = [
#   "feedparser",
#   "requests",
# ]
# ///

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urlunparse

import feedparser
import requests

# Standard User-Agent to prevent blogs from blocking automated requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/rss+xml, application/xml, text/xml, */*'
}

MAX_RETRIES = 2
RETRY_DELAY = 3  # seconds

FEEDS_FILE = 'feeds.txt'
DATA_DIR = 'data'
JSON_FILE = os.path.join(DATA_DIR, 'blogroll.json')
CONFIG_FILE = 'zola.toml'


def fetch_feed(url, headers):
    """GETs a feed URL and returns the requests.Response. Retries on failure."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=headers, timeout=15)
            # 304 Not Modified is a valid, cache-preserving response
            if r.status_code == 304:
                return r
            r.raise_for_status()
            return r
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
    raise last_error


def clean_url(url):
    """Ensures absolute URLs and trims whitespace."""
    if not url:
        return ""
    return url.strip()


def clean_feed_url_to_site(url):
    """If the URL looks like a feed file, strip the feed-specific parts to get the site URL."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        path = parsed.path

        # Suffixes to strip
        suffixes = [
            'feed.xml', 'feed.atom', 'atom.xml', 'index.xml', 'rss.xml',
            'feed/', 'feed', 'atom/', 'atom', 'rss/', 'rss'
        ]

        changed = True
        while changed:
            changed = False
            lower_path = path.lower()
            for suffix in suffixes:
                if lower_path.endswith(suffix):
                    path = path[:-len(suffix)]
                    changed = True
                    break

        return urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment))
    except Exception:
        return url


def hostname_title(url):
    """Derives a human-readable title from a URL's hostname."""
    try:
        host = urlparse(url).netloc.removeprefix('www.')
        return host or url
    except Exception:
        return url


def resolve_feed_title(feed_parsed, feed_url, site_url):
    """Returns the feed's title, falling back to the site hostname when missing or a raw URL."""
    title = (feed_parsed.feed.get('title') or '').strip()
    if not title or title.startswith(('http://', 'https://')):
        return hostname_title(site_url or feed_url)
    return title


def resolve_site_url(feed_parsed, feed_url):
    """Finds a valid HTTP/HTTPS URL for the website from parsed feed by filtering by rel, type, and origin."""
    feed_info = feed_parsed.feed
    links = feed_info.get('links', [])

    feed_parsed_url = urlparse(feed_url)
    feed_host = feed_parsed_url.netloc.lower()

    # Fallback to feed URL's site origin
    fallback_url = clean_feed_url_to_site(f"{feed_parsed_url.scheme}://{feed_parsed_url.netloc}")

    is_feedburner = 'feedburner' in feed_host

    candidates = []
    for l in links:
        href = l.get('href')
        if not href:
            continue

        # Resolve relative URLs
        if not (href.startswith('http://') or href.startswith('https://')):
            href = urljoin(feed_url, href)

        rel = l.get('rel', 'alternate')
        rel = rel.strip().lower() if rel else 'alternate'

        type_val = l.get('type', '')
        type_val = type_val.strip().lower() if type_val else ''

        # 1. Filter by rel (must be alternate)
        if rel != 'alternate':
            continue

        # 2. Filter by type (must not be a feed MIME type, stylesheet, etc.)
        feed_types = {
            'application/rss+xml', 'application/atom+xml', 'application/xml',
            'text/xml', 'application/rdf+xml'
        }
        if type_val in feed_types:
            continue
        if type_val and type_val != 'text/html' and type_val != 'text/plain':
            continue

        # 3. Filter by origin (allowing scheme and www subdomain differences)
        if not is_feedburner:
            href_parsed = urlparse(href)
            href_host_val = href_parsed.netloc.lower()

            h1 = feed_host.removeprefix('www.')
            h2 = href_host_val.removeprefix('www.')
            if h1 != h2:
                continue

        candidates.append(href)

    if candidates:
        return clean_feed_url_to_site(candidates[0])

    return fallback_url


def load_max_posts_config(default_val=100):
    """Loads the max post limit from zola.toml [extra] block, falling back to default."""
    try:
        import tomllib
    except ImportError:
        tomllib = None

    if tomllib is not None:
        try:
            with open(CONFIG_FILE, 'rb') as f:
                return tomllib.load(f).get('extra', {}).get('blogroll_max_posts', default_val)
        except Exception as e:
            print(f"Warning: Error reading blogroll_max_posts from {CONFIG_FILE}: {e}")
    else:
        # Fallback for Python < 3.11: simple line parsing
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('blogroll_max_posts') and '=' in line:
                        return int(line.split('=', 1)[1].strip())
        except (OSError, ValueError) as e:
            print(f"Warning: Error reading blogroll_max_posts from {CONFIG_FILE}: {e}")
    return default_val


def parse_entry_date(entry):
    """Extracts a YYYY-MM-DD publication date from a feed entry.

    Returns an empty string when no date can be parsed. The fallback must be
    deterministic across runs: stamping unparseable dates with today's date
    would churn the JSON (and the CI commit) every day. Empty dates sort last.
    """
    published_parsed = entry.get('published_parsed') or entry.get('updated_parsed')
    if published_parsed:
        return time.strftime('%Y-%m-%d', published_parsed)

    date_str = entry.get('published') or entry.get('updated')
    if date_str:
        try:
            dt = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
            return dt.strftime('%Y-%m-%d')
        except Exception:
            pass
    return ""


def process_feed(url, cached_feed):
    """Fetch and parse a single feed.

    Returns (feed_result, posts). posts is None when cached posts must be
    preserved (feed not modified, or fetch failed).
    """
    print(f"Fetching: {url}")
    cached_feed = cached_feed or {}

    headers = dict(HEADERS)
    etag = cached_feed.get('etag')
    last_modified = cached_feed.get('last_modified')
    if etag:
        headers['If-None-Match'] = etag
    if last_modified:
        headers['If-Modified-Since'] = last_modified

    try:
        r = fetch_feed(url, headers)

        if r.status_code == 304:
            print(f"  = not modified, using cache")
            feed_result = dict(cached_feed)
            feed_result['status'] = 'ok'
            feed_result['error'] = None
            return feed_result, None

        parsed = feedparser.parse(r.content)

        site_url = resolve_site_url(parsed, url)
        feed_title = resolve_feed_title(parsed, url, site_url)

        feed_result = {
            'title': feed_title,
            'feed_url': url,
            'site_url': site_url,
            'status': 'ok',
            'error': None,
            'etag': r.headers.get('ETag'),
            'last_modified': r.headers.get('Last-Modified'),
        }

        print(f"  ✓ '{feed_title}' — {len(parsed.entries)} entries")

        posts = []
        for entry in parsed.entries:
            post_url = clean_url(entry.get('link'))
            if not post_url:
                continue

            posts.append({
                'title': entry.get('title', 'Untitled'),
                'url': post_url,
                'published': parse_entry_date(entry),
                'feed_url': url,
                'feed_title': feed_title,
                'site_url': site_url
            })

        return feed_result, posts

    except Exception as e:
        print(f"  ✗ {url}: {e}")
        # Preserve metadata from cache when available
        feed_result = {
            'title': cached_feed.get('title') or hostname_title(url),
            'feed_url': url,
            'site_url': cached_feed.get('site_url') or clean_feed_url_to_site(url),
            'status': 'error',
            'error': str(e),
            'etag': etag,
            'last_modified': last_modified,
        }
        return feed_result, None


def load_existing_data(json_file):
    """Loads the existing blogroll JSON, returning an empty dict on any failure."""
    if not os.path.exists(json_file):
        return {}
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Loaded existing data with {len(data.get('posts', []))} posts.")
        return data
    except Exception as e:
        print(f"Warning: Could not read existing JSON file: {e}")
        return {}


def write_json_atomic(path, data):
    """Writes JSON to a temp file then atomically renames it into place."""
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def main():
    # Ensure the data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)

    # Load existing data to merge and preserve history in case a feed goes offline temporarily
    existing_data = load_existing_data(JSON_FILE)

    # Index existing state by feed_url — the stable identity of a feed
    cached_feeds = {f['feed_url']: f for f in existing_data.get('feeds', [])}

    # Backfill feed_url on legacy posts (written before per-post feed_url existed)
    title_to_feed = {f['title']: f['feed_url'] for f in existing_data.get('feeds', [])}
    cached_posts_by_feed = {}
    for p in existing_data.get('posts', []):
        if not p.get('feed_url'):
            p['feed_url'] = title_to_feed.get(p.get('feed_title'), '')
        if p['feed_url']:
            cached_posts_by_feed.setdefault(p['feed_url'], []).append(p)

    if not os.path.exists(FEEDS_FILE):
        print(f"Error: {FEEDS_FILE} not found. Please create it.")
        return

    # Read feeds from feeds.txt
    with open(FEEDS_FILE, 'r', encoding='utf-8') as f:
        feed_urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

    new_feeds = []
    posts_by_feed = {}  # feed_url -> list of posts, or None to preserve cache

    # Fetch all feeds concurrently
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(process_feed, url, cached_feeds.get(url)): url
            for url in feed_urls
        }
        for future in as_completed(futures):
            feed_result, posts = future.result()
            new_feeds.append(feed_result)
            posts_by_feed[feed_result['feed_url']] = posts

    # Preserve feed ordering from feeds.txt
    feed_order = {url: i for i, url in enumerate(feed_urls)}
    new_feeds.sort(key=lambda f: feed_order.get(f['feed_url'], len(feed_urls)))

    # Merge fresh posts with cached posts for unmodified/failed feeds,
    # keeping only posts from feeds currently listed in feeds.txt
    all_posts = []
    for url in feed_urls:
        posts = posts_by_feed.get(url)
        if posts is None:
            posts = cached_posts_by_feed.get(url, [])
        all_posts.extend(posts)

    # Deduplicate by post URL
    posts_by_url = {p['url']: p for p in all_posts}

    # Sort posts by date (descending)
    filtered_posts = sorted(posts_by_url.values(), key=lambda x: x['published'], reverse=True)

    # Cap list to top N posts configured in zola.toml
    max_posts = load_max_posts_config()
    final_posts = filtered_posts[:max_posts]

    # Compile the final dictionary
    output_data = {
        'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'feeds': new_feeds,
        'posts': final_posts
    }

    # Skip the write (and the CI commit) entirely when nothing changed
    if (existing_data.get('feeds') == output_data['feeds']
            and existing_data.get('posts') == output_data['posts']):
        print(f"\nNo changes — {len(final_posts)} posts from {len(new_feeds)} feeds are up to date.")
        return

    # Write back to JSON file
    write_json_atomic(JSON_FILE, output_data)

    print(f"\nUpdated blogroll JSON file with {len(final_posts)} posts from {len(new_feeds)} feeds.")


if __name__ == '__main__':
    main()
