#!/usr/bin/env python3
"""Offline contact-path checks for generated editorial HTML. Python 3.10+."""
from __future__ import annotations

import argparse
from collections import deque
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import unquote, urljoin, urlsplit

VOID = frozenset('area base br col embed hr img input link meta param source track wbr'.split())
EXCLUDED = frozenset(('script', 'style', 'template', 'nav', 'footer'))


class MainLinks(HTMLParser):
    """Extract main-content anchors without executing scripts or loading assets."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.links = []
        self.form_present = False
        self.has_main = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        blocked = (tag in EXCLUDED or 'hidden' in attrs or
                   attrs.get('aria-hidden', '').lower() == 'true' or
                   any(item[1] for item in self.stack))
        in_main = tag == 'main' or any(item[0] == 'main' for item in self.stack)
        if tag == 'main' and not blocked:
            self.has_main = True
        if in_main and not blocked:
            if tag == 'a' and attrs.get('href'):
                self.links.append(attrs['href'].strip())
            if tag == 'form':
                self.form_present = True
        if tag not in VOID:
            self.stack.append((tag, blocked))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)


def normalize_route(route):
    parsed = urlsplit(route)
    decoded = unquote(parsed.path)
    if (parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or
            not decoded.startswith('/') or '\\' in decoded or
            any(part in ('.', '..') for part in decoded.split('/'))):
        raise ValueError('Routes must be absolute site paths without query, fragment or traversal.')
    if any(ord(char) < 32 for char in decoded):
        raise ValueError('Control characters are not allowed in routes.')
    clean = '/' + '/'.join(part for part in decoded.split('/') if part)
    if clean.endswith('/index.html'):
        clean = clean[:-10]
    elif not Path(clean).suffix:
        clean = clean.rstrip('/') + '/'
    return clean


def read_page(root, route):
    relative = route.lstrip('/')
    if route.endswith('/'):
        relative += 'index.html'
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'Page escapes build directory: {route}')
    try:
        if path.stat().st_size > 2_000_000:
            raise ValueError(f'Page exceeds 2 MB input limit: {route}')
        html = path.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as error:
        raise ValueError(f'Cannot read UTF-8 page: {route}') from error
    parser = MainLinks()
    parser.feed(html)
    parser.close()
    if not parser.has_main:
        raise ValueError(f'No visible <main> element: {route}; use generated page HTML.')
    return parser


def email_from_href(href):
    parsed = urlsplit(href)
    if parsed.scheme.lower() != 'mailto':
        return None
    email = unquote(parsed.path).strip()
    # Conservative single-mailbox syntax check, not SMTP/deliverability validation.
    if re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}", email):
        return email
    return None


def audit(root, routes, origin='https://looksmaxxing.guide'):
    origin_parts = urlsplit(origin)
    if (origin_parts.scheme not in ('http', 'https') or not origin_parts.hostname or
            origin_parts.username or origin_parts.password or
            origin_parts.path not in ('', '/') or origin_parts.query or origin_parts.fragment):
        raise ValueError('Origin must be an HTTP(S) origin, without credentials, path or query.')
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Build directory does not exist.')
    routes = list(dict.fromkeys(normalize_route(route) for route in routes))
    if not routes:
        raise ValueError('Select at least one policy page.')
    if len(routes) > 100:
        raise ValueError('At most 100 explicitly selected policy pages are supported.')
    parsed_pages = {route: read_page(root, route) for route in routes}
    graph = {route: [] for route in routes}
    contacts = {route: [] for route in routes}
    ignored = {route: 0 for route in routes}
    for route, page in parsed_pages.items():
        for href in page.links:
            email = email_from_href(href)
            if email:
                contacts[route].append(email)
                continue
            target = urlsplit(urljoin(origin.rstrip('/') + route, href))
            if (target.scheme.lower(), target.netloc.lower()) != (origin_parts.scheme.lower(), origin_parts.netloc.lower()):
                ignored[route] += 1
                continue
            try:
                destination = normalize_route(target.path)
            except ValueError:
                ignored[route] += 1
                continue
            if destination in graph:
                if destination not in graph[route]:
                    graph[route].append(destination)
            else:
                ignored[route] += 1
    results = []
    for start in routes:
        queue = deque([(start, [start])])
        seen = {start}
        visited = []
        found_email = None
        found_path = []
        while queue:
            current, path = queue.popleft()
            visited.append(current)
            if contacts[current]:
                found_email, found_path = contacts[current][0], path
                break
            for neighbor in graph[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        results.append({
            'route': start,
            'status': 'email_link_reachable' if found_email else 'needs_review',
            'contact': found_email,
            'path': found_path,
            'visited': visited,
            'form_present': any(parsed_pages[path].form_present for path in visited),
            'ignored_links': sum(ignored[path] for path in visited),
        })
    return {
        'ok': all(page['contact'] is not None for page in results),
        'scope': 'Selected pages only; mailto reachability is not delivery verification. Forms require manual review.',
        'pages': results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build_dir', type=Path)
    parser.add_argument('--page', action='append', required=True, help='Site route to include; repeat for each policy/contact page.')
    parser.add_argument('--origin', default='https://looksmaxxing.guide')
    args = parser.parse_args()
    try:
        report = audit(args.build_dir, args.page, args.origin)
    except ValueError as error:
        print(json.dumps({'ok': False, 'error': str(error)}, indent=2))
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
