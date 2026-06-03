import shutil
from datetime import date
from pathlib import Path

import pytest

from daily_bluesky_post import match

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def content_dirs(tmp_path):
    people = tmp_path / "people"
    events = tmp_path / "events"
    people.mkdir()
    events.mkdir()
    shutil.copy(FIXTURES / "person_okubo.md", people / "okubo-toshimichi.md")
    shutil.copy(FIXTURES / "person_no_portrait.md", people / "hoshi-shinichi.md")
    shutil.copy(FIXTURES / "event_with_persons.md", events / "1860-03-24-sakuradamongai.md")
    shutil.copy(FIXTURES / "event_empty_persons.md", events / "1853-07-08-perry-raiko.md")
    return people, events


def test_match_person_by_death_anniversary(content_dirs):
    people, events = content_dirs
    matches = match.match_today(date(2026, 5, 14), people, events)
    slugs = [m.slug for m in matches]
    assert "okubo-toshimichi" in slugs


def test_match_event_by_anniversary(content_dirs):
    people, events = content_dirs
    matches = match.match_today(date(2026, 3, 24), people, events)
    slugs = [m.slug for m in matches]
    assert "1860-03-24-sakuradamongai" in slugs


def test_event_with_empty_personslugs_is_excluded(content_dirs):
    """ペリー来航(personSlugs 未設定 = 空)は投稿対象外"""
    people, events = content_dirs
    matches = match.match_today(date(2026, 7, 8), people, events)
    assert matches == []


def test_no_match_returns_empty(content_dirs):
    people, events = content_dirs
    matches = match.match_today(date(2026, 1, 1), people, events)
    assert matches == []


def test_match_includes_url_frontmatter_body(content_dirs):
    people, events = content_dirs
    matches = match.match_today(date(2026, 5, 14), people, events)
    m = matches[0]
    assert m.kind == "person"
    assert m.url == "https://aoyama-cemetery.pages.dev/people/okubo-toshimichi"
    assert m.frontmatter["name"] == "大久保 利通"
    assert isinstance(m.body, str)
    assert "本文" in m.body
    assert m.body != ""


def test_match_caps_to_max_per_day(content_dirs, tmp_path):
    """6 人同じ命日なら 5 件まで"""
    people, events = content_dirs
    template = (FIXTURES / "person_okubo.md").read_text()
    for i in range(6):
        (people / f"x{i}.md").write_text(
            template.replace("大久保 利通", f"テスト{i}")
        )
    matches = match.match_today(date(2026, 5, 14), people, events)
    assert len(matches) == 5


def test_event_returns_with_event_kind(content_dirs):
    people, events = content_dirs
    matches = match.match_today(date(2026, 3, 24), people, events)
    assert matches[0].kind == "event"
