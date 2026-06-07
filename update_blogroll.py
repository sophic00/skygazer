# /// script
# dependencies = [
#   "feedparser",
# ]
# ///

import os
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
import feedparser

# Custom User-Agent to prevent blogs from blocking automated requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 skygazer-blogroll-bot'
}

def fetch_feed(url):
    """Fetches a feed URL and returns its byte content."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read()

def clean_url(url):
    """Ensures absolute URLs and trims whitespace."""
    if not url:
        return ""
    return url.strip()

def clean_feed_url_to_site(url):
    """If the URL looks like a feed file, strip the feed-specific parts to get the site URL."""
    if not url:
        return ""
    from urllib.parse import urlparse, urlunparse
    try:
        parsed = urlparse(url)
        path = parsed.path
        
        # Suffixes to strip
        suffixes = [
            'feed.xml', 'feed.atom', 'atom.xml', 'index.xml', 'rss.xml',
            'feed/', 'feed', 'atom/', 'atom', 'rss/', 'rss'
        ]
        
        lower_path = path.lower()
        for suffix in suffixes:
            if lower_path.endswith(suffix):
                path = path[:-len(suffix)]
                break
                
        return urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment))
    except Exception:
        return url

def resolve_site_url(feed_parsed, feed_url):
    """Finds a valid HTTP/HTTPS URL for the website from parsed feed."""
    feed_info = feed_parsed.feed
    
    # Try searching in links list for an alternate link first
    links = feed_info.get('links', [])
    for l in links:
        href = l.get('href')
        if href and (href.startswith('http://') or href.startswith('https://')):
            if l.get('rel') == 'alternate':
                return clean_feed_url_to_site(href.strip())
                
    # Fallback to feed_info.get('link') if it's a valid HTTP URL
    link = feed_info.get('link')
    if link and (link.startswith('http://') or link.startswith('https://')):
        return clean_feed_url_to_site(link.strip())
            
    # Try first valid http link from links list
    for l in links:
        href = l.get('href')
        if href and (href.startswith('http://') or href.startswith('https://')):
            return clean_feed_url_to_site(href.strip())
            
    # Fallback: parse the feed's URL to get the base domain
    try:
        return clean_feed_url_to_site(feed_url)
    except Exception:
        return feed_url

def load_max_posts_config(default_val=100):
    """Loads the max post limit from zola.toml [extra] block, falling back to default."""
    if not os.path.exists('zola.toml'):
        return default_val
    try:
        # Try using standard library's tomllib (Python 3.11+)
        try:
            import tomllib
            with open('zola.toml', 'rb') as f:
                data = tomllib.load(f)
                return data.get('extra', {}).get('blogroll_max_posts', default_val)
        except (ImportError, Exception):
            # Fallback for Python < 3.11: simple line parsing
            with open('zola.toml', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('blogroll_max_posts') and '=' in line:
                        parts = line.split('=')
                        return int(parts[1].strip())
    except Exception as e:
        print(f"Warning: Error reading blogroll_max_posts from zola.toml: {e}")
    return default_val

def main():
    feeds_file = 'feeds.txt'
    data_dir = 'data'
    json_file = os.path.join(data_dir, 'blogroll.json')

    # Ensure the data directory exists
    os.makedirs(data_dir, exist_ok=True)

    # Load existing data to merge and preserve history in case a feed goes offline temporarily
    existing_data = {}
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            print(f"Loaded existing data with {len(existing_data.get('posts', []))} posts.")
        except Exception as e:
            print(f"Warning: Could not read existing JSON file: {e}")

    # Map existing posts by URL to ease updating/merging
    posts_cache = {p['url']: p for p in existing_data.get('posts', [])}

    if not os.path.exists(feeds_file):
        print(f"Error: {feeds_file} not found. Please create it.")
        return

    # Read feeds from feeds.txt
    with open(feeds_file, 'r', encoding='utf-8') as f:
        feed_urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

    new_feeds = []
    
    for url in feed_urls:
        print(f"Fetching: {url}")
        try:
            xml_data = fetch_feed(url)
            parsed = feedparser.parse(xml_data)
            
            feed_info = parsed.feed
            # Extract feed name and main site URL
            feed_title = feed_info.get('title', url)
            site_url = resolve_site_url(parsed, url)

            new_feeds.append({
                'title': feed_title,
                'feed_url': url,
                'site_url': site_url,
                'status': 'ok',
                'error': None
            })

            print(f"Successfully parsed feed: '{feed_title}' with {len(parsed.entries)} entries.")

            for entry in parsed.entries:
                post_url = clean_url(entry.get('link'))
                if not post_url:
                    continue
                
                post_title = entry.get('title', 'Untitled')

                # Find publication date
                published_parsed = entry.get('published_parsed') or entry.get('updated_parsed')
                if published_parsed:
                    published_date = time.strftime('%Y-%m-%d', published_parsed)
                else:
                    # Parse date string or fallback to today
                    date_str = entry.get('published') or entry.get('updated')
                    if date_str:
                        try:
                            # Let feedparser try parsing the string or default to current date
                            # (some feeds have odd strings, so a robust fallback is needed)
                            dt = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
                            published_date = dt.strftime('%Y-%m-%d')
                        except Exception:
                            published_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                    else:
                        published_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

                posts_cache[post_url] = {
                    'title': post_title,
                    'url': post_url,
                    'published': published_date,
                    'feed_title': feed_title,
                    'site_url': site_url
                }

        except Exception as e:
            print(f"Error fetching/parsing {url}: {e}")
            # Try to retrieve name/site URL from existing cache to avoid losing details
            feed_title = url
            site_url = url
            for f in existing_data.get('feeds', []):
                if f['feed_url'] == url:
                    feed_title = f['title']
                    site_url = f['site_url']
                    break
            
            new_feeds.append({
                'title': feed_title,
                'feed_url': url,
                'site_url': site_url,
                'status': 'error',
                'error': str(e)
            })

    # Filter posts to only keep those from feeds currently listed in feeds.txt
    active_feed_titles = {f['title'] for f in new_feeds}
    filtered_posts = [p for p in posts_cache.values() if p['feed_title'] in active_feed_titles]

    # Sort posts by date (descending)
    filtered_posts.sort(key=lambda x: x['published'], reverse=True)

    # Cap list to top N posts configured in zola.toml
    max_posts = load_max_posts_config()
    final_posts = filtered_posts[:max_posts]

    # Compile the final dictionary
    output_data = {
        'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'feeds': new_feeds,
        'posts': final_posts
    }

    # Write back to JSON file
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"Updated blogroll JSON file with {len(final_posts)} posts.")

if __name__ == '__main__':
    main()
