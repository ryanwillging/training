"""Shared navigation component for all HTML pages.

Add new pages to the PAGES list and they will automatically appear in the navigation bar.
"""

from typing import List, Dict, Optional

# Central registry of all HTML pages
# Add new pages here and they'll automatically appear in the nav
PAGES: List[Dict[str, str]] = [
    {"path": "/dashboard", "name": "Dashboard", "icon": ""},
    {"path": "/upcoming", "name": "Upcoming", "icon": ""},
    {"path": "/reviews", "name": "Reviews", "icon": ""},
    {"path": "/metrics", "name": "Metrics", "icon": ""},
    {"path": "/api/reports/daily", "name": "Daily Report", "icon": ""},
    {"path": "/api/reports/weekly", "name": "Weekly Report", "icon": ""},
]


def wrap_page_with_nav(html_content: str, current_path: Optional[str] = None) -> str:
    """
    Wrap existing HTML content with Material Design navigation.

    DEPRECATED: For new pages, use design_system.wrap_page() instead.
    This function is kept for backward compatibility with existing pages.

    Args:
        html_content: The existing HTML content
        current_path: The path of the current page to highlight as active

    Returns:
        HTML with navigation injected
    """
    from api.design_system import get_base_css, get_nav_css

    base_css = get_base_css()
    nav_css = get_nav_css()

    # Build navigation links
    nav_links = []
    mobile_links = []
    for page in PAGES:
        active = ' active' if current_path == page['path'] else ''
        nav_links.append(f'<a href="{page["path"]}" class="md-nav-link{active}">{page["name"]}</a>')
        mobile_links.append(f'<a href="{page["path"]}" class="md-nav-link{active}">{page["name"]}</a>')

    nav_html = f'''
    <nav class="md-nav">
        <div class="md-nav-container">
            <a href="/dashboard" class="md-nav-brand">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M13.5 5.5c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zM9.8 8.9L7 23h2.1l1.8-8 2.1 2v6h2v-7.5l-2.1-2 .6-3C14.8 12 16.8 13 19 13v-2c-1.9 0-3.5-1-4.3-2.4l-1-1.6c-.4-.6-1-1-1.7-1-.3 0-.5.1-.8.1L6 8.3V13h2V9.6l1.8-.7"/>
                </svg>
                Training
            </a>
            <div class="md-nav-links">
                {' '.join(nav_links)}
            </div>
            <button class="md-nav-menu-btn" onclick="document.getElementById('mobile-menu').classList.toggle('open')" aria-label="Menu">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
                </svg>
            </button>
        </div>
        <div id="mobile-menu" class="md-nav-mobile">
            {' '.join(mobile_links)}
        </div>
    </nav>
    '''

    # Inject base CSS and nav CSS
    full_css = f"<style>{base_css}\n{nav_css}</style>"

    # Inject CSS before </head>
    if "</head>" in html_content:
        html_content = html_content.replace("</head>", f"{full_css}</head>")

    # Inject nav after <body> or after <body ...>
    if "<body>" in html_content:
        html_content = html_content.replace("<body>", f"<body>{nav_html}<div class='md-container'>")
        html_content = html_content.replace("</body>", "</div></body>")
    elif "<body " in html_content:
        import re
        html_content = re.sub(r'(<body[^>]*>)', rf'\1{nav_html}<div class="md-container">', html_content)
        html_content = html_content.replace("</body>", "</div></body>")

    return html_content


# Keep these for backward compatibility
def get_nav_css() -> str:
    """Return CSS styles for the navigation bar. DEPRECATED: Use design_system instead."""
    from api.design_system import get_nav_css as ds_nav_css
    return ds_nav_css()


def get_nav_html(current_path: Optional[str] = None) -> str:
    """Generate navigation bar HTML. DEPRECATED: Use design_system.wrap_page instead."""
    nav_links = []
    for page in PAGES:
        active = ' active' if current_path == page['path'] else ''
        nav_links.append(f'<a href="{page["path"]}" class="md-nav-link{active}">{page["name"]}</a>')

    return f'''
    <nav class="md-nav">
        <div class="md-nav-container">
            <a href="/dashboard" class="md-nav-brand">Training</a>
            <div class="md-nav-links">{' '.join(nav_links)}</div>
        </div>
    </nav>
    '''
