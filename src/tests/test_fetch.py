from navigator.fetch import keep_link, links, normalise_url, parse_robots, robots_allows

UNIBE = """User-Agent: *
Disallow: /error
Disallow: /*index.html
Disallow: /*search_eng.html$
Allow: /*index_eng.html
"""


def test_robots_wildcards():
    rules = parse_robots(UNIBE)
    assert not robots_allows(rules, "/research/index.html")
    assert robots_allows(rules, "/research/index_eng.html")
    assert not robots_allows(rules, "/x/search_eng.html")
    assert robots_allows(rules, "/x/search_eng.html.bak")
    assert not robots_allows(rules, "/error/404")


def test_robots_other_agents_ignored():
    rules = parse_robots("User-agent: Googlebot\nDisallow: /\n\nUser-agent: *\nDisallow: /private/\n")
    assert robots_allows(rules, "/public/a.html") and not robots_allows(rules, "/private/a.html")


def test_normalise_url():
    assert normalise_url("http://WWW.Artorg.unibe.ch/a/index_eng.html?x=1#top") == "https://www.artorg.unibe.ch/a/index_eng.html"
    assert normalise_url("https://www.dcberne.com") == "https://www.dcberne.com/"


def test_keep_link():
    assert keep_link("artorg.unibe.ch", "https://www.artorg.unibe.ch/research/index_eng.html")
    assert keep_link("artorg.unibe.ch", "https://www.artorg.unibe.ch/research/")
    assert not keep_link("artorg.unibe.ch", "https://www.artorg.unibe.ch/file.pdf")
    assert not keep_link("artorg.unibe.ch", "https://www.unibe.ch/index_eng.html")
    assert not keep_link("artorg.unibe.ch", "mailto:a@b.ch")


def test_links_resolves_relative():
    html = '<a href="./research/index_eng.html?q=1">r</a><a href="https://x.ch/a.html">x</a>'
    assert links("https://www.artorg.unibe.ch/index_eng.html", html, "artorg.unibe.ch") == [
        "https://www.artorg.unibe.ch/research/index_eng.html"]
