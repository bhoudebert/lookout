"""Canonical form of a URL, so the same story from two sources is one item."""

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = frozenset({"fbclid", "gclid", "ref", "ref_src", "mc_cid", "mc_eid"})


def canonical_url(url: str) -> str:
    """Lower-case host, no fragment, no tracking parameters, no trailing slash on the path."""
    parts = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.startswith(_TRACKING_PREFIXES) and k not in _TRACKING_KEYS
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


_WEB_SCHEMES = frozenset({"http", "https"})
_USERINFO = re.compile(r"(https?://)[^\s/@]*@", re.IGNORECASE)
_QUERY = re.compile(r"(https?://[^\s?#]*)[?#][^\s,;)'\"]*?(?=[:.]?(?:[\s,;)'\"]|$))", re.IGNORECASE)


def is_web_url(url: str) -> bool:
    """True for an absolute http(s) address with a host: the only kind an item may link to."""
    parts = urlsplit(url.strip())
    return parts.scheme.lower() in _WEB_SCHEMES and bool(parts.hostname)


def redact_addresses(text: str) -> str:
    """The text with no credentials, query or fragment in the web addresses it quotes."""
    return _QUERY.sub(r"\1?…", _USERINFO.sub(r"\1", text))
