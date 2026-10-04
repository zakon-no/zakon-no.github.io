#!/usr/bin/env python3
"""Сборка сайта: index.md -> index.html, offer.md -> offer.html.

Запуск:  python3 build.py
Выход:   index.html и offer.html — обычные статические страницы.
Их можно открыть двойным щелчком, сервер не нужен.
"""

import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

SECTIONS = [
dict(id="hero",       nav=None,              foot=None,                   bg="section--alt section--hero", heading="h1",
         feat="hero__facts", photo=False, body="", buttons="hero"),
    dict(id="about",      nav="О юристе",        foot="О юристе",             bg="",                          heading="h2",
         feat="",              photo=True,  body="section__body--about"),
    dict(id="principles", nav=None,              foot="Принципы работы",      bg="",                          heading="h2",
         feat="grid grid--icons", photo=False, body=""),
    dict(id="directions", nav="Направления",     foot="Направления практики", bg="section--alt",              heading="h2",
         feat="grid grid--dirs",   photo=False, body=""),
    dict(id="services",   nav="Услуги",          foot="Услуги",               bg="",                          heading="h2",
         feat="cards cards--numbered cards--tiles", photo=False, body=""),
    dict(id="process",    nav="Порядок работы",  foot="Порядок работы",       bg="section--alt",              heading="h2",
         feat="steps",            photo=False, body=""),
    dict(id="practice",   nav=None,              foot="Категории дел",        bg="",                          heading="h2",
         feat="cards",            photo=False, body="", disclaimer=True),
    dict(id="faq",        nav="Вопросы",         foot="Вопросы",              bg="section--alt",              heading="h2",
         feat="faq",              photo=False, body=""),
    dict(id="contacts",   nav="Контакты",        foot="Контакты",             bg="section--deep",             heading="h2",
         feat="contacts",         photo=False, body="section__body--contacts",
         buttons="contacts", disclaimer=True),
]

BUTTONS = {
    "hero": [("Получить консультацию", "#contacts", "btn btn--primary"),
             ("Услуги", "#services", "btn btn--ghost")],
    "contacts": [("Написать на e-mail", "mailto:{email}?subject={subject}&body={body}", "btn btn--primary"),
                 ("Позвонить", "{phone_link}", "btn btn--ghost")],
}

EMAIL_SUBJECT = "%D0%92%D0%BE%D0%BF%D1%80%D0%BE%D1%81%20%D1%81%20%D1%81%D0%B0%D0%B9%D1%82%D0%B0"
EMAIL_BODY = ("%D0%97%D0%B4%D1%80%D0%B0%D0%B2%D1%81%D1%82%D0%B2%D1%83%D0%B9%D1%82%D0%B5%2C%20"
              "%D0%98%D0%BC%D1%8F%0A%0A%D0%A2%D0%B5%D0%BB%D0%B5%D0%BC%D0%B0%3A%0A%0A"
              "%D0%9A%D1%80%D0%B0%D1%82%D0%BA%D0%BE%20%D0%BE%D0%BF%D0%B8%D1%81%D0%B0%D0%BD%D0%B8%D0%B5%20"
              "%D0%BF%D0%BE%D0%BE%D0%B1%D1%89%D0%B5%D0%BD%D0%B8%D0%B5%3A%0A")

LIST_RE = re.compile(r"^(\s*)([-*+]|\d+\.)\s+(.*)$")


def escape(text):
    return html.escape(text, quote=False)


def inline(text):
    s = escape(text)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(\s*([^)\s]+)\s*\)",
               lambda m: '<a href="%s">%s</a>' % (m.group(2), m.group(1)), s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    return s


class Parser(object):
    def __init__(self, lines):
        self.lines = [l.replace("\t", "    ").rstrip() for l in lines]
        self.i = 0

    def peek(self):
        while self.i < len(self.lines) and not self.lines[self.i].strip():
            self.i += 1
        return self.lines[self.i] if self.i < len(self.lines) else None

    def indent_of(self, line):
        return len(line) - len(line.lstrip())

    def parse(self):
        blocks = []
        while True:
            line = self.peek()
            if line is None:
                return blocks
            stripped = line.strip()
            indent = self.indent_of(line)

            m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if m:
                self.i += 1
                lvl = len(m.group(1))
                blocks.append("<h%d>%s</h%d>" % (lvl, inline(m.group(2)), lvl))
                continue

            if LIST_RE.match(line):
                blocks.append(self.parse_list(indent))
                continue

            if stripped.startswith(">"):
                blocks.append(self.parse_quote())
                continue

            blocks.append(self.parse_paragraph(indent))

    def parse_paragraph(self, indent):
        buf = []
        while True:
            if self.i >= len(self.lines):
                break
            line = self.lines[self.i]
            if not line.strip():
                break
            cur = self.indent_of(line)
            s = line.strip()
            if cur < indent:
                break
            if cur == indent and (LIST_RE.match(line) or s.startswith("#") or s.startswith(">")):
                break
            buf.append(s)
            self.i += 1
        while self.i < len(self.lines) and not self.lines[self.i].strip():
            self.i += 1
        return "<p>%s</p>" % inline(" ".join(buf))

    def parse_quote(self):
        buf = []
        while True:
            line = self.peek()
            if line is None or not line.strip().startswith(">"):
                break
            buf.append(line.strip()[1:].strip())
            self.i += 1
        inner = "\n".join(Parser(buf).parse())
        return '<blockquote class="notice">\n%s\n</blockquote>' % inner

    def parse_list(self, indent):
        marker = LIST_RE.match(self.lines[self.i]).group(2)
        tag = "ol" if re.match(r"^\d+\.$", marker) else "ul"
        items = []

        while True:
            line = self.peek()
            if line is None:
                break
            m = LIST_RE.match(line)
            if not m or self.indent_of(line) != indent:
                break
            self.i += 1
            body = [m.group(3)]

            while True:
                if self.i >= len(self.lines):
                    break
                nxt = self.lines[self.i]
                if not nxt.strip():
                    save = self.i
                    while self.i < len(self.lines) and not self.lines[self.i].strip():
                        self.i += 1
                    if self.i < len(self.lines) and self.indent_of(self.lines[self.i]) > indent:
                        body.append("")
                        continue
                    self.i = save
                    break
                if self.indent_of(nxt) > indent:
                    body.append(nxt.rstrip())
                    self.i += 1
                    continue
                break

            items.append(dedent(body))

        rendered = []
        for body in items:
            sub = Parser(body).parse()
            if len(sub) == 1 and sub[0].startswith("<p>") and sub[0].endswith("</p>"):
                rendered.append("<li>%s</li>" % sub[0][3:-4])
            else:
                rendered.append("<li>%s</li>" % "\n".join(sub))
        return "<%s>\n%s\n</%s>" % (tag, "\n".join(rendered), tag)


def dedent(lines):
    real = [l for l in lines if l.strip()]
    if not real:
        return lines
    cut = min(self_indent(l) for l in real)
    return [l[cut:] if l.strip() else "" for l in lines]


def self_indent(line):
    return len(line) - len(line.lstrip())


def first_list_index(blocks):
    for n, block in enumerate(blocks):
        if block.startswith("<ul>") or block.startswith("<ol>"):
            return n
    return -1


def parse_front_matter(text):
    meta = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta[key.strip()] = value.strip().strip('"')
            body = parts[2]
    return meta, body.lstrip("\n")


def split_sections(body):
    sections = []
    current = None
    for line in body.splitlines():
        m = re.match(r"^##\s+(.*)$", line)
        if m:
            current = {"title": m.group(1).strip(), "lines": []}
            sections.append(current)
            continue
        if current is not None:
            current["lines"].append(line)
    return sections


def render_section(section, cfg, meta):
    blocks = Parser(section["lines"]).parse()

    eyebrow = None
    lead = None
    if blocks:
        m = re.match(r"^<p><em>(.+)</em></p>$", blocks[0].strip())
        if m:
            eyebrow = m.group(1)
            blocks.pop(0)
    if blocks and blocks[0].startswith("<p>") and blocks[0].endswith("</p>"):
        lead = blocks[0][3:-4]
        blocks.pop(0)

    if cfg.get("feat"):
        idx = first_list_index(blocks)
        if idx >= 0:
            blocks[idx] = re.sub(r"^<(ul|ol)>", r'<\1 class="%s">' % cfg["feat"],
                                 blocks[idx], count=1)

    if cfg.get("disclaimer") and blocks and blocks[-1].startswith("<p>"):
        blocks[-1] = blocks[-1].replace("<p>", '<p class="disclaimer">', 1)

    if cfg.get("buttons"):
        links = []
        for label, href, cls in BUTTONS[cfg["buttons"]]:
            href = (href.replace("{email}", meta.get("email", ""))
                        .replace("{phone_link}", meta.get("phone_link", ""))
                        .replace("{subject}", EMAIL_SUBJECT)
                        .replace("{body}", EMAIL_BODY))
            links.append('<a class="%s" href="%s">%s</a>' % (cls, href, label))
        blocks.extend(links)

    head = ['<header class="section__head">']
    if eyebrow:
        head.append('<p class="eyebrow">%s</p>' % eyebrow)
    head.append('<%s class="section__title">%s</%s>' % (cfg["heading"], escape(section["title"]), cfg["heading"]))
    if lead:
        head.append('<p class="section__lead">%s</p>' % lead)
    head.append("</header>")

    body_parts = ['<div class="section__body%s">' % ((" " + cfg["body"]) if cfg.get("body") else "")]
    if cfg.get("photo"):
        body_parts.append('<div class="section__media">')
        body_parts.append('<img class="photo" src="assets/img/photo.jpg" alt="%s, юрист" width="877" height="1100">'
                          % escape(meta.get("name", "")))
        body_parts.append("</div>")
    body_parts.append('<div class="section__content">')
    body_parts.extend(blocks)
    body_parts.append("</div></div>")

    classes = "section" + ((" " + cfg["bg"]) if cfg["bg"] else "")
    return '<section id="%s" class="%s">\n<div class="container">\n%s\n%s\n</div>\n</section>' % (
        cfg["id"], classes, "\n".join(head), "\n".join(body_parts))


def page(meta, sections_html, title=None, description=None, body_class="", body=None):
    nav_items = [c for c in SECTIONS if c["nav"]]
    nav = "\n".join('<li><a class="nav__link" href="#%s">%s</a></li>' % (c["id"], c["nav"])
                    for c in nav_items)
    email = meta.get("email", "")
    footer_nav = "\n".join('          <li><a href="#%s">%s</a></li>' % (c["id"], c["foot"])
                           for c in SECTIONS if c.get("foot"))
    year = "2026"

    main = body if body is not None else '<div class="container">\n%s\n</div>' % sections_html

    source = "index.md" if body is None else "offer.md"

    return """<!DOCTYPE html>
<!-- Файл собран автоматически из {source} скриптом build.py.
     Правьте {source} и сохраняйте: этот файл перезаписывается при каждой сборке. -->
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<meta name="author" content="{author}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="website">
<meta property="og:locale" content="ru_RU">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{canonical}assets/img/photo.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="assets/img/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="assets/css/styles.css">
</head>
<body>
<a class="skip-link" href="#main">Перейти к основному содержанию</a>
<header class="header">
  <div class="container header__inner">
    <a class="brand" href="#main">
      <span class="brand__mark" aria-hidden="true">АФ</span>
      <span class="brand__text">
        <span class="brand__name">{short_name}</span>
        <span class="brand__caption">Юридическая помощь бизнесу и гражданам</span>
      </span>
    </a>
    <nav class="nav" id="nav" aria-label="Основная навигация">
      <ul class="nav__list">
{nav}
      </ul>
    </nav>
    <div class="header__aside">
      <a class="header__phone" href="{phone_link}">{phone}</a>
      <a class="btn btn--primary btn--sm" href="#contacts">Написать</a>
      <button class="burger" type="button" aria-label="Открыть меню" aria-expanded="false" aria-controls="nav" id="burger">
        <span class="burger__line"></span>
        <span class="burger__line"></span>
        <span class="burger__line"></span>
      </button>
    </div>
  </div>
</header>
<main id="main" class="main{body_class}">
{main}
</main>
<footer class="footer">
  <div class="container">
    <div class="footer__top">
      <div class="footer__brand">
        <span class="footer__mark" aria-hidden="true">АФ</span>
        <div>
          <p class="footer__name">{author}</p>
          <p class="footer__role">{role}</p>
        </div>
      </div>
      <nav class="footer__nav" aria-label="Навигация в подвале">
        <ul>
{footer_nav}
        </ul>
      </nav>
    </div>
    <div class="footer__legal">
      <p class="footer__disclaimer">Информация, размещённая на сайте, не является публичной офертой и не может рассматриваться как заключение какого-либо договора. Перечень услуг приведён справочно и не является публичной офертой. Сайт носит исключительно информационный характер и не является рекламой. Условия оказания услуг определяются договором оказания юридических услуг.</p>
      <p class="footer__copy">&copy; <span id="year">{year}</span> ИП Филин А.С. Все права защищены.</p>
    </div>
  </div>
</footer>
<script src="assets/js/main.js"></script>
</body>
</html>
""".format(
        source=source,
        title=escape(title or meta.get("title", "")),
        description=escape(description or meta.get("description", "")),
        author=escape(meta.get("name", "")),
        short_name=escape(meta.get("name", "").replace("Филин Александр Сергеевич", "Филин А.С. — юрист")),
        role=escape(meta.get("role", "")),
        canonical="https://zakon-no.github.io/",
        body_class=(" " + body_class) if body_class else "",
        nav=nav,
        phone=escape(meta.get("phone", "")),
        phone_link=escape(meta.get("phone_link", "")),
        email=email,
        main=main,
        footer_nav=footer_nav,
        year=year,
    )


def build_index():
    meta, body = parse_front_matter(open(os.path.join(ROOT, "index.md"), encoding="utf-8").read())
    sections = split_sections(body)
    rendered = []
    for n, section in enumerate(sections):
        cfg = SECTIONS[n] if n < len(SECTIONS) else dict(
            id="section-%d" % (n + 1), nav=None, bg="", heading="h2", feat="", photo=False, body="")
        rendered.append(render_section(section, cfg, meta))
    html_out = page(meta, "\n".join(rendered))
    write(os.path.join(ROOT, "index.html"), html_out)
    return len(sections)


def build_offer():
    path = os.path.join(ROOT, "offer.md")
    if not os.path.exists(path):
        return False
    meta, body = parse_front_matter(open(path, encoding="utf-8").read())
    inner = "\n".join(Parser(body.splitlines()).parse())
    html_out = page(meta, None,
                    title="Отказ от юридической оферты — Филин А.С., юрист",
                    description="Сайт не является публичной офертой. Условия оказания юридических услуг определяются договором.",
                    body_class="main--legal",
                    body='<div class="container">\n<h1 class="section__title">Отказ от юридической оферты</h1>\n%s\n</div>' % inner)
    write(os.path.join(ROOT, "offer.html"), html_out)
    return True


def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    size = os.path.getsize(path) / 1024.0
    print("  ✓ %-12s %6.1f КБ" % (os.path.basename(path), size))


def main():
    print("Сборка сайта:")
    count = build_index()
    print("  разделов в index.md: %d" % count)
    if count != len(SECTIONS):
        print("  ⚠ Ожидалось %d разделов. Оформление определяется порядком, "
              "проверьте, не потерян ли раздел." % len(SECTIONS))
    build_offer()
    print("Готово. Сервер на http://localhost:8080/ покажет изменения сам.")


if __name__ == "__main__":
    sys.exit(main())