"""Shared navigation component for all HTML pages.

Add new pages to the PAGES list and they will automatically appear in the navigation bar.
"""

from typing import List, Dict, Optional

# Central registry of all HTML pages
# Add new pages here and they'll automatically appear in the nav
PAGES: List[Dict[str, str]] = [
    {"path": "/dashboard", "name": "Dashboard", "icon": ""},
    {"path": "/metrics", "name": "Metrics", "icon": ""},
    {"path": "/api/reports/daily", "name": "Daily Report", "icon": ""},
    {"path": "/api/reports/weekly", "name": "Weekly Report", "icon": ""},
]


def get_nav_css() -> str:
    """Return CSS styles for the navigation bar."""
    return """
        .site-nav {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 12px 16px;
            background: #1a1a1a;
            margin: -20px -20px 20px -20px;
            flex-wrap: wrap;
        }
        .site-nav-brand {
            font-weight: 600;
            color: #fff;
            margin-right: 16px;
            font-size: 14px;
            text-decoration: none;
        }
        .site-nav a {
            color: #a3a3a3;
            text-decoration: none;
            font-size: 13px;
            padding: 6px 12px;
            border-radius: 6px;
            transition: background 0.15s, color 0.15s;
        }
        .site-nav a:hover {
            background: #333;
            color: #fff;
        }
        .site-nav a.active {
            background: #2563eb;
            color: #fff;
        }
        @media (max-width: 600px) {
            .site-nav {
                padding: 10px 12px;
                gap: 4px;
            }
            .site-nav a {
                font-size: 12px;
                padding: 5px 8px;
            }
        }
    """


def get_nav_html(current_path: Optional[str] = None) -> str:
    """
    Generate navigation bar HTML.

    Args:
        current_path: The path of the current page to highlight as active

    Returns:
        HTML string for the navigation bar
    """
    links = []
    for page in PAGES:
        active_class = ' class="active"' if current_path == page["path"] else ""
        icon = f'{page["icon"]} ' if page.get("icon") else ""
        links.append(f'<a href="{page["path"]}"{active_class}>{icon}{page["name"]}</a>')

    return f'''<nav class="site-nav">
        <a href="/dashboard" class="site-nav-brand">Training</a>
        {" ".join(links)}
    </nav>'''


def wrap_page_with_nav(html_content: str, current_path: Optional[str] = None) -> str:
    """
    Wrap existing HTML content with navigation.

    This is a convenience function for retrofitting navigation into existing pages.
    It injects the nav CSS into the head and the nav HTML after the body tag.

    Args:
        html_content: The existing HTML content
        current_path: The path of the current page to highlight as active

    Returns:
        HTML with navigation injected
    """
    nav_css = get_nav_css()
    nav_html = get_nav_html(current_path)

    # Inject CSS before </style> or </head>
    if "</style>" in html_content:
        # Find the last </style> tag and inject before it
        last_style_idx = html_content.rfind("</style>")
        html_content = html_content[:last_style_idx] + nav_css + html_content[last_style_idx:]
    elif "</head>" in html_content:
        html_content = html_content.replace("</head>", f"<style>{nav_css}</style></head>")

    # Inject nav after <body> or after <body ...>
    if "<body>" in html_content:
        html_content = html_content.replace("<body>", f"<body>{nav_html}")
    elif "<body " in html_content:
        # Handle <body class="..."> etc
        import re
        html_content = re.sub(r'(<body[^>]*>)', rf'\1{nav_html}', html_content)

    return html_content
