"""Unit tests for the helper functions in update_blogroll.py."""

import importlib.util
import time
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "update_blogroll.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("update_blogroll", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


blogroll = _load_script()


class FakeFeed:
    """Minimal stand-in for a feedparser result: only .feed is used."""

    def __init__(self, feed_info):
        self.feed = feed_info


def test_clean_url_strips_whitespace():
    assert blogroll.clean_url(" https://a.dev/post ") == "https://a.dev/post"
    assert blogroll.clean_url(None) == ""
    assert blogroll.clean_url("") == ""


def test_clean_feed_url_to_site_strips_feed_suffixes():
    cases = {
        "https://example.com/feed.xml": "https://example.com/",
        "https://example.com/blog/feed/": "https://example.com/blog/",
        "https://example.com/atom.xml": "https://example.com/",
        "https://example.com/index.xml": "https://example.com/",
        "https://example.com/posts/rss": "https://example.com/posts/",
        "https://example.com/blog/": "https://example.com/blog/",
        "https://example.com/feed": "https://example.com/",
    }
    for url, expected in cases.items():
        assert blogroll.clean_feed_url_to_site(url) == expected, url


def test_clean_feed_url_to_site_preserves_query_and_fragment():
    assert (
        blogroll.clean_feed_url_to_site("https://example.com/feed.xml?utm=1#top")
        == "https://example.com/?utm=1#top"
    )


def test_hostname_title():
    assert blogroll.hostname_title("https://www.example.com/post") == "example.com"
    assert blogroll.hostname_title("https://example.com") == "example.com"
    assert blogroll.hostname_title("not a url") == "not a url"


def test_resolve_feed_title_uses_feed_title():
    assert blogroll.resolve_feed_title(FakeFeed({"title": "Dot Blog"}), "", "") == "Dot Blog"


def test_resolve_feed_title_falls_back_to_hostname():
    feed = FakeFeed({})
    assert (
        blogroll.resolve_feed_title(feed, "https://example.com/feed.xml", "https://www.example.com/x")
        == "example.com"
    )


def test_resolve_feed_title_rejects_url_as_title():
    feed = FakeFeed({"title": "https://spam.dev"})
    assert (
        blogroll.resolve_feed_title(feed, "https://example.com/feed.xml", "https://example.com")
        == "example.com"
    )


def test_resolve_site_url_prefers_alternate_link():
    feed = FakeFeed({"links": [{"href": "https://example.com/", "rel": "alternate", "type": "text/html"}]})
    assert (
        blogroll.resolve_site_url(feed, "https://example.com/feed.xml")
        == "https://example.com/"
    )


def test_resolve_site_url_resolves_relative_links():
    feed = FakeFeed({"links": [{"href": "/about", "rel": "alternate"}]})
    assert (
        blogroll.resolve_site_url(feed, "https://example.com/feed.xml")
        == "https://example.com/about"
    )


def test_resolve_site_url_ignores_self_and_foreign_links():
    feed = FakeFeed({"links": [
        {"href": "https://example.com/feed.xml", "rel": "self"},
        {"href": "https://other.dev/", "rel": "alternate"},
    ]})
    assert blogroll.resolve_site_url(feed, "https://example.com/feed.xml") == "https://example.com"


def test_resolve_site_url_ignores_feed_type_links():
    feed = FakeFeed({"links": [
        {"href": "https://example.com/rss.xml", "rel": "alternate", "type": "application/rss+xml"},
    ]})
    assert blogroll.resolve_site_url(feed, "https://example.com/feed.xml") == "https://example.com"


def test_resolve_site_url_allows_feedburner_cross_host():
    feed = FakeFeed({"links": [{"href": "https://martinkl.blogspot.com/", "rel": "alternate"}]})
    assert (
        blogroll.resolve_site_url(feed, "https://feeds.feedburner.com/martinkl")
        == "https://martinkl.blogspot.com/"
    )


def test_parse_entry_date_from_struct():
    entry = {"published_parsed": time.struct_time((2026, 1, 2, 3, 4, 5, 4, 2, 0))}
    assert blogroll.parse_entry_date(entry) == "2026-01-02"


def test_parse_entry_date_from_updated_struct():
    entry = {"updated_parsed": time.struct_time((2026, 1, 2, 3, 4, 5, 4, 2, 0))}
    assert blogroll.parse_entry_date(entry) == "2026-01-02"


def test_parse_entry_date_from_iso_string():
    assert blogroll.parse_entry_date({"published": "2026-01-02T03:04:05Z"}) == "2026-01-02"


def test_parse_entry_date_from_rfc822_string():
    assert blogroll.parse_entry_date({"published": "Mon, 02 Jan 2006 03:04:05 GMT"}) == "2006-01-02"


def test_parse_entry_date_unparseable_is_stable():
    assert blogroll.parse_entry_date({"published": "not a date"}) == ""
    assert blogroll.parse_entry_date({}) == ""


def test_load_max_posts_config_reads_zola_toml(tmp_path, monkeypatch):
    config = tmp_path / "zola.toml"
    config.write_text("[extra]\nblogroll_max_posts = 7\n", encoding="utf-8")
    monkeypatch.setattr(blogroll, "CONFIG_FILE", str(config))
    assert blogroll.load_max_posts_config() == 7


def test_load_max_posts_config_falls_back_to_default(tmp_path, monkeypatch):
    config = tmp_path / "zola.toml"
    config.write_text("[extra]\nother_key = 7\n", encoding="utf-8")
    monkeypatch.setattr(blogroll, "CONFIG_FILE", str(config))
    assert blogroll.load_max_posts_config() == 100
    assert blogroll.load_max_posts_config(default_val=5) == 5


def test_load_max_posts_config_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(blogroll, "CONFIG_FILE", str(tmp_path / "absent.toml"))
    assert blogroll.load_max_posts_config() == 100
