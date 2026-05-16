"""Low-level HTML utilities using BeautifulSoup."""

from typing import Iterator, List, Optional

from bs4 import Tag


def get_text(tag: Tag, selector: str, default: Optional[str] = None) -> Optional[str]:
    """Get text content from tag matching selector."""
    found = tag.select_one(selector)
    if found:
        return found.get_text(strip=True)
    return default


def get_attr(tag: Tag, selector: str, attr: str, default: Optional[str] = None) -> Optional[str]:
    """Get attribute value from tag matching selector."""
    found = tag.select_one(selector)
    if found and found.has_attr(attr):
        return found.get(attr)
    return default


def get_attrs_multi(tag: Tag, selector: str, attr: str, priority: tuple = ("data-src", "src")) -> Optional[str]:
    """Get attribute value, trying multiple attribute names in priority order."""
    found = tag.select_one(selector)
    if not found:
        return default
    for attr_name in priority:
        if found.has_attr(attr_name):
            return found.get(attr_name)
    return None


def get_links(tag: Tag, selector: str) -> List[Tag]:
    """Get all tags matching selector."""
    return tag.select(selector)


def iter_until_next_marker(
    start_tag: Tag,
    stop_selector: str,
    included_tags: Optional[List[str]] = None,
) -> Iterator[Tag]:
    """Iterate from start_tag until next marker tag matching stop_selector.

    Args:
        start_tag: Starting tag
        stop_selector: CSS selector for stop marker
        included_tags: Only yield these tag names (e.g., ["tr", "td"])
    """
    current = start_tag.next_sibling
    while current:
        if isinstance(current, Tag):
            if current.select_one(stop_selector):
                break
            if included_tags is None or current.name in included_tags:
                yield current
        current = current.next_sibling


def normalize_br(text: str) -> str:
    """Normalize <br> tags in text to spaces."""
    return text.replace("<br>", " ").replace("<br/>", " ").replace("<br />", " ")


def get_text_with_br(tag: Tag) -> str:
    """Get text content preserving <br> as spaces."""
    result = ""
    for child in tag.children:
        if isinstance(child, str):
            result += child
        elif child.name == "br":
            result += " "
        elif isinstance(child, Tag):
            result += get_text_with_br(child)
    return result.strip()