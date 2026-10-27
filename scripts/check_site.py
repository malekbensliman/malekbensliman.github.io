# /// script
# requires-python = ">=3.12"
# dependencies = ["beautifulsoup4"]
# ///
"""Static checks for the site: files, copy, links, and CSS rules.

Run: uv run --no-project --script scripts/check_site.py [page.html ...] [check_name ...]
With no arguments every check runs on every page that exists.
"""

import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "projects.html", "teaching.html", "research.html"]

INTRO = (
    "I work on how organizations can use AI to learn from unconventional data, "
    "from paintings and auction records to factory sensors and text. I am now a "
    "Lecturer in Discipline in the Marketing division at Columbia Business School, "
    "where I teach MBA and EMBA courses on generative AI, marketing, and analytics, "
    "and run workshops on AI topics. Prior to joining the faculty full-time, I was a "
    "data scientist at Sotheby's, pricing artworks, and at Oden Technologies, "
    "improving factory production lines. I like building the tools I teach with, "
    "and I advise organizations that want to put data and AI to use. I'm an engineer "
    "by training, with an M.S. in Engineering from École Centrale Paris and an M.S. "
    "in Operations Research from Columbia, and I hold a Ph.D. in Quantitative "
    "Marketing from Columbia Business School."
)
ROLE = "Lecturer in Discipline · Marketing · Columbia Business School"

# (tag class, name, href) in display order
PROJECTS = [
    ("tag-ai", "The A(I) List", "https://the-ai-list.io/"),
    ("tag-ai", "GEO Brand Tracker", "https://geo-brand-tracker--geo-brand-tracker.us-central1.hosted.app/"),
    ("tag-teaching", "MBA Copilot", "https://github.com/malekbensliman/mba-copilot"),
    ("tag-teaching", "CBS Concept Lab", "https://cbs-concept-lab.web.app/"),
    ("tag-experiment", "Copa Machina", "https://copa-machina.vercel.app/"),
]

NAV = [
    ("Teaching", "teaching.html"),
    ("Projects", "projects.html"),
    ("Research", "research.html"),
    ("CV", "cv.pdf"),
]

FORBIDDEN = [
    "UA-101743443-1", "Ph.D. Candidate", "Friendship Paradox", "Adaptive Customization",
    "Zero to Deployed", "MKT 337", "teach business leaders",
    "less than a year after ChatGPT", "a few are below",
]

TAG_COLORS = ["#1d3a6e", "#9cc3e4", "#0f2445", "#e3eef8"]


ONLY_PAGES = [a for a in sys.argv[1:] if a.endswith(".html")]
ONLY_CHECKS = [a for a in sys.argv[1:] if a.startswith("check_")]


def existing_pages():
    return [p for p in (ONLY_PAGES or PAGES) if (ROOT / p).is_file()]


def soup(page: str) -> BeautifulSoup:
    return BeautifulSoup((ROOT / page).read_text(encoding="utf-8"), "html.parser")


def squash(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def text(page: str) -> str:
    # get_text(" ") separates inline tags too ("email me ."); rejoin punctuation
    return re.sub(r" ([.,;:!?)])", r"\1", squash(soup(page).get_text(" ")))


def check_files():
    for f in ["cv.pdf", "photo-stage.jpg", "photo-headshot.jpg"]:
        assert (ROOT / f).is_file(), f"missing {f}"
    gone = ["Malek Ben Sliman CV.pdf", "Malek Ben Sliman Resume.pdf",
            "Malek_BenSliman_CV_Spring2019.pdf", "Malek_BenSliman_ShortJan20.pdf",
            "Malek_BenSliman_ShortNov2019.pdf", "Malek_BenSliman.jpg",
            "WhatsApp Image 2026-10-27 at 05.39.12.jpeg", "code.html"]
    for f in gone:
        assert not (ROOT / f).exists(), f"should be deleted: {f}"


def check_home_intro():
    s = soup("index.html")
    assert "Malek Ben Sliman" in squash(s.h1.get_text()), "h1 is not the name"
    role = s.select_one(".hero .role")
    assert role and squash(role.get_text()) == ROLE, f"role line: {role and squash(role.get_text())!r}"
    intro = s.select_one(".hero .intro")
    assert intro, "no .hero .intro"
    got = squash(intro.get_text())
    assert got == INTRO, f"intro differs:\n  got: {got}\n want: {INTRO}"


def check_home_projects():
    rows = soup("index.html").select("#projects .project")
    assert len(rows) == len(PROJECTS), f"{len(rows)} project rows, want {len(PROJECTS)}"
    for row, (tag, name, href) in zip(rows, PROJECTS):
        got_name = squash(row.select_one(".project-name").get_text())
        assert got_name == name, f"row order/name: {got_name!r} != {name!r}"
        assert row.select_one("a")["href"] == href, f"{name}: href {row.select_one('a')['href']}"
        tags = [c for t in row.select(".tag") for c in t["class"] if c.startswith("tag-")]
        assert tags == [tag], f"{name}: tags {tags}, want [{tag}]"


def check_nav():
    for page in existing_pages():
        header = soup(page).select_one("header.site-header")
        assert header, f"{page}: no header.site-header"
        name = header.select_one(".site-name")
        assert name and name.get("href") == "index.html", f"{page}: name link"
        links = [(squash(a.get_text()), a["href"]) for a in header.select("nav a")]
        assert links == NAV, f"{page}: nav {links}"


def check_footer():
    want = ["mailto:mab2343@columbia.edu", "linkedin.com/in/malekbensliman",
            "scholar.google.com/citations?user=B9X_WdcAAAAJ", "github.com/malekbensliman"]
    for page in existing_pages():
        footer = soup(page).select_one("footer.site-footer")
        assert footer, f"{page}: no footer.site-footer"
        hrefs = " ".join(a["href"] for a in footer.select("a"))
        for w in want:
            assert w in hrefs, f"{page}: footer missing {w}"


def check_forbidden_strings():
    for page in existing_pages() + ["style.css"]:
        raw = (ROOT / page).read_text(encoding="utf-8")
        for bad in FORBIDDEN:
            assert bad not in raw, f"{page} contains {bad!r}"


def check_css_rules():
    css = (ROOT / "style.css").read_text(encoding="utf-8").lower()
    for bad in ["border-radius", "box-shadow", "gradient", "prefers-color-scheme"]:
        assert bad not in css, f"style.css uses {bad}"
    for color in TAG_COLORS:
        assert color in css, f"style.css missing {color}"
    assert "archivo" in css, "style.css missing Archivo"


def check_local_links_resolve():
    for page in existing_pages():
        for el in soup(page).select("[href], [src]"):
            ref = el.get("href") or el.get("src")
            if re.match(r"^(https?:|mailto:|data:|#)", ref):
                continue
            path = re.split(r"[?#]", ref)[0]
            assert (ROOT / path).is_file(), f"{page}: broken local link {ref!r}"


def check_external_links_new_tab():
    for page in existing_pages():
        for a in soup(page).select('a[href^="http"]'):
            assert a.get("target") == "_blank", f"{page}: {a['href']} not target=_blank"
            assert "noopener" in (a.get("rel") or []), f"{page}: {a['href']} missing noopener"


def check_anchor_targets_exist():
    for page in existing_pages():
        for a in soup(page).select("a[href]"):
            m = re.match(r"^([\w-]+\.html)#([\w-]+)$", a["href"])
            if m and (ROOT / m[1]).is_file():
                assert soup(m[1]).find(id=m[2]), f"{page}: {a['href']} has no target"


COURSES = ["Generative AI for Business", "Marketing / Marketing Strategy", "Marketing Analytics",
           "Business Analytics", "Statistical Modeling and Decision Making"]
MATERIALS = ("I'm happy to share materials from any of these courses with other instructors. "
             "Just email me.")
ADVISING = ("Through Columbia Business School's Entrepreneurship and Competitiveness programs, "
            "which support owners of mid-sized companies in Latin America and Africa, I've advised:")


def check_teaching():
    page = "teaching.html"
    s, t = soup(page), text(page)
    titles = [squash(h.get_text()) for h in s.select(".course h3")]
    assert titles == COURSES, f"course titles {titles}"
    assert MATERIALS in t, "materials line missing"
    assert t.index(MATERIALS) < t.index(COURSES[0]), "materials line must precede first course"
    email = [a for a in s.select("a") if squash(a.get_text()) == "email me"]
    assert email and email[0]["href"] == "mailto:mab2343@columbia.edu", "email me link"
    for needle in ["since Fall 2023", "co-designed with Olivier Toubia",
                   "As generative AI was going mainstream", "AI for Academic Research",
                   "AI for Business & Finance", ADVISING]:
        assert needle in t, f"missing {needle!r}"
    hrefs = [a["href"] for a in s.select("a[href]")]
    for url in ["https://capitaria.com/", "https://www.mamy-opticians.com/"]:
        assert url in hrefs, f"missing link {url}"
    for bad in ["B6601", "B5601", "B8609", "B8709", "SJDM"]:
        assert bad not in t, f"contains {bad}"


DIGITAL_TWINS_AUTHORS = (
    "Tianyi Peng, Melanie Brucks, George Gui, Daniel J. Merlau, Grace Jiarui Fan, "
    "Malek Ben Sliman, Eric J. Johnson, Abdullah Althenayyan, Silvia Bellezza, Dante Donati, "
    "Hortense Fong, Elizabeth Friedman, Ariana Guevara, Mohamed Hussein, Kinshuk Jerath, "
    "Bruce Kogut, Akshit Kumar, Kristen Lane, Hannah Li, Vicki Morwitz, Oded Netzer, "
    "Patryk Perkowski, and Olivier Toubia"
)


def check_research():
    page = "research.html"
    s, t = soup(page), text(page)
    labels = [squash(h.get_text()).lower() for h in s.select("h2.label")]
    assert labels == ["publications", "working paper", "work in progress"], f"sections {labels}"
    for needle in ["R2M Index 1.0", "Digital twins are funhouse mirrors",
                   "The Impact of Auction Houses on Art Valuation",
                   "Luxury Education Foundation Award", "Mixture of LLMs for Market Research"]:
        assert needle in t, f"missing {needle!r}"
    assert s.find(id="art-valuation"), "no #art-valuation"
    assert len(s.select("details")) >= 2, "abstracts should be in <details>"
    assert not s.select("script"), "no scripts on research page"
    assert "Research Overview" not in t, "old overview paragraph"
    twins = [a for a in s.select(".pub") if "Digital twins" in a.get_text()][0]
    meta = squash(twins.select_one(".meta").get_text())
    assert meta.startswith(DIGITAL_TWINS_AUTHORS), f"digital twins authors: {meta[:120]}..."
    assert "orcid" not in meta.lower() and "et al" not in meta, "author list should be full and clean"
    hrefs = [a["href"] for a in s.select("a[href]")]
    for doi in ["https://doi.org/10.1177/00222429211028145", "https://doi.org/10.1126/sciadv.aeh8260"]:
        assert doi in hrefs, f"missing {doi}"


def check_no_street_address_in_repo():
    # The repo is public: no street address (e.g. "<number> West ...") in any tracked text file.
    import subprocess
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    pattern = re.compile(r"\b\d{2,5} (West|East|W\.|E\.)\b")
    for f in tracked:
        if Path(f).suffix in {".html", ".css", ".py", ".md", ".txt", ""}:
            hit = pattern.search((ROOT / f).read_text(encoding="utf-8", errors="ignore"))
            assert not hit, f"{f}: street-address-like text {hit[0]!r}"


def check_stylesheet_versioned():
    # GitHub Pages caches style.css for 10 minutes; a version tag makes browsers refetch it.
    for page in existing_pages():
        hrefs = [l["href"] for l in soup(page).select('link[rel="stylesheet"]') if "style.css" in l["href"]]
        assert hrefs and all(re.fullmatch(r"style\.css\?v=\d+", h) for h in hrefs), f"{page}: {hrefs}"


# (id, name, tag class, [(link label, href)], used-in text or None)
PROJECT_PAGE = [
    ("the-ai-list", "The A(I) List", "tag-ai", [("Live", "https://the-ai-list.io/")], "Generative AI for Business"),
    ("geo-brand-tracker", "GEO Brand Tracker", "tag-ai",
     [("Live", "https://geo-brand-tracker--geo-brand-tracker.us-central1.hosted.app/")], "Generative AI for Business"),
    ("mba-copilot", "MBA Copilot", "tag-teaching", [("Code", "https://github.com/malekbensliman/mba-copilot")],
     "Generative AI for Business"),
    ("cbs-concept-lab", "CBS Concept Lab", "tag-teaching", [("Live", "https://cbs-concept-lab.web.app/")],
     "marketing and statistics courses"),
    ("copa-machina", "Copa Machina", "tag-experiment", [("Live", "https://copa-machina.vercel.app/")], None),
]


def check_projects_page():
    s = soup("projects.html")
    entries = s.select(".project-entry")
    assert len(entries) == len(PROJECT_PAGE), f"{len(entries)} entries"
    for el, (pid, name, tag, links, used) in zip(entries, PROJECT_PAGE):
        assert el.get("id") == pid, f"{name}: id {el.get('id')}"
        assert squash(el.h2.get_text()) == name, f"order/name: {squash(el.h2.get_text())}"
        assert el.select_one(f".tag.{tag}"), f"{name}: tag {tag}"
        got = [(squash(a.get_text()).rstrip(" ↗→"), a["href"]) for a in el.select(".project-links a")]
        assert got == links, f"{name}: links {got}"
        assert len(squash(el.select_one(".project-summary").get_text())) > 120, f"{name}: summary too short"
        if used:
            assert used in squash(el.get_text()), f"{name}: used-in {used!r}"
        assert el.select_one("img.project-shot, .project-shot"), f"{name}: no image/block"


def check_home_publication():
    sec = soup("index.html").select_one("#publication")
    assert sec, "no #publication section on homepage"
    t = squash(sec.get_text())
    assert "Digital twins are funhouse mirrors" in t and "Science Advances" in t, f"publication text: {t[:100]}"
    links = [a["href"] for a in sec.select("a[href]")]
    assert "https://doi.org/10.1126/sciadv.aeh8260" in links, f"links {links}"
    assert "Art valuation" not in text("index.html"), "art valuation should not be on homepage"


def check_home_links_to_projects_page():
    s = soup("index.html")
    more = [a for a in s.select("#projects a") if a["href"] == "projects.html"]
    assert more and "See all projects" in squash(more[0].get_text()), "no 'See all projects' link"


def check_teaching_headshot():
    img = soup("teaching.html").select_one("img.headshot")
    assert img and img["src"] == "photo-headshot.jpg", "teaching page headshot"


def check_favicon():
    assert (ROOT / "favicon.svg").is_file(), "missing favicon.svg"
    for page in existing_pages():
        icons = [l["href"] for l in soup(page).select('link[rel="icon"]')]
        assert icons == ["favicon.svg"], f"{page}: icons {icons}"


def check_head():
    for page in existing_pages():
        s = soup(page)
        assert s.html.get("lang") == "en", f"{page}: lang"
        assert s.select_one('meta[name="description"]'), f"{page}: description"
        for prop in ["og:title", "og:description", "og:image"]:
            assert s.select_one(f'meta[property="{prop}"]'), f"{page}: {prop}"
        og = s.select_one('meta[property="og:image"]')["content"]
        assert og.endswith("photo-headshot.jpg"), f"{page}: og:image {og}"
        for img in s.select("img"):
            assert img.get("alt", "").strip(), f"{page}: img without alt"
    gsv = soup("index.html").select_one('meta[name="google-site-verification"]')
    assert gsv and gsv["content"] == "Wvb4ztsXDy-5L_1OYWuLPOG2adjC0HiQER0uwKYzLbo", "site verification"


def main():
    checks = [(n, f) for n, f in globals().items()
              if n.startswith("check_") and callable(f) and (not ONLY_CHECKS or n in ONLY_CHECKS)]
    failed = 0
    for name, fn in checks:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as e:  # a crash in a check is a failure, not a pass
            failed += 1
            print(f"FAIL {name}: {type(e).__name__}: {e}")
    print(f"{len(checks) - failed}/{len(checks)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
