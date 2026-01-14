"""
SVG visualization generators following Edward Tufte's design principles.

Key Principles Applied:
- High data-ink ratio: Every pixel serves a purpose
- No chartjunk: No 3D, gradients, or decorative elements
- Sparklines: Tiny word-sized graphics for trends
- Small multiples: Repeated small charts for comparison
- Slope graphs: Show change between two points
"""

from typing import List, Optional, Tuple, Dict, Any


def generate_sparkline(
    values: List[float],
    width: int = 100,
    height: int = 20,
    color: str = "#333",
    show_endpoints: bool = True,
    show_min_max: bool = False
) -> str:
    """
    Generate an inline SVG sparkline.

    Tufte's sparkline: A small, word-sized graphic with typographic resolution.
    No axes, labels, or gridlines - just the data.

    Args:
        values: List of numeric values to plot
        width: SVG width in pixels
        height: SVG height in pixels
        color: Line color
        show_endpoints: Mark first and last points
        show_min_max: Mark minimum and maximum points

    Returns:
        SVG string that can be embedded inline
    """
    if not values or all(v is None for v in values):
        return '<span class="sparkline muted">--</span>'

    # Filter None values while preserving position info
    clean_values = [(i, v) for i, v in enumerate(values) if v is not None]
    if not clean_values:
        return '<span class="sparkline muted">--</span>'

    just_values = [v for _, v in clean_values]
    min_val = min(just_values)
    max_val = max(just_values)
    val_range = max_val - min_val or 1

    # Padding for dots
    padding = 2
    plot_height = height - (padding * 2)
    plot_width = width - (padding * 2)

    # Calculate points
    points = []
    x_step = plot_width / (len(values) - 1) if len(values) > 1 else plot_width
    for idx, val in clean_values:
        x = padding + (idx * x_step)
        y = padding + plot_height - ((val - min_val) / val_range * plot_height)
        points.append((x, y, val))

    # Build path
    path_d = "M " + " L ".join([f"{x:.1f},{y:.1f}" for x, y, _ in points])

    # Start SVG
    svg_parts = [
        f'<svg class="sparkline" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" style="vertical-align: middle;">'
    ]

    # Add the line
    svg_parts.append(
        f'<path d="{path_d}" fill="none" stroke="{color}" stroke-width="1.5" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )

    # Add endpoint dots (Tufte recommends marking first, last, min, max)
    if show_endpoints and len(points) >= 2:
        # First point (lighter)
        fx, fy, _ = points[0]
        svg_parts.append(f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="2" fill="#999"/>')
        # Last point (darker, current value)
        lx, ly, _ = points[-1]
        svg_parts.append(f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="2" fill="{color}"/>')

    if show_min_max and len(just_values) >= 2:
        # Find min and max positions
        min_idx = just_values.index(min_val)
        max_idx = just_values.index(max_val)
        if min_idx < len(points):
            mx, my, _ = points[min_idx]
            svg_parts.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="2" fill="#e74c3c"/>')
        if max_idx < len(points):
            mx, my, _ = points[max_idx]
            svg_parts.append(f'<circle cx="{mx:.1f}" cy="{my:.1f}" r="2" fill="#27ae60"/>')

    svg_parts.append('</svg>')
    return ''.join(svg_parts)


def generate_bar_sparkline(
    values: List[float],
    width: int = 100,
    height: int = 20,
    color: str = "#333",
    highlight_last: bool = True
) -> str:
    """
    Generate a bar-style sparkline (useful for discrete values like workout counts).

    Args:
        values: List of numeric values
        width: SVG width
        height: SVG height
        color: Bar color
        highlight_last: Make the last bar darker

    Returns:
        SVG string
    """
    if not values or all(v is None for v in values):
        return '<span class="sparkline muted">--</span>'

    clean_values = [v if v is not None else 0 for v in values]
    max_val = max(clean_values) or 1

    padding = 1
    bar_gap = 1
    available_width = width - (padding * 2)
    bar_width = (available_width - (bar_gap * (len(clean_values) - 1))) / len(clean_values)
    bar_width = max(bar_width, 2)  # Minimum bar width

    svg_parts = [
        f'<svg class="sparkline" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" style="vertical-align: middle;">'
    ]

    for i, val in enumerate(clean_values):
        bar_height = (val / max_val) * (height - padding * 2)
        x = padding + i * (bar_width + bar_gap)
        y = height - padding - bar_height
        bar_color = color if not highlight_last or i < len(clean_values) - 1 else "#000"
        opacity = 0.6 if not highlight_last or i < len(clean_values) - 1 else 1.0

        svg_parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" '
            f'height="{bar_height:.1f}" fill="{bar_color}" opacity="{opacity}"/>'
        )

    svg_parts.append('</svg>')
    return ''.join(svg_parts)


def generate_slope_graph(
    before: float,
    after: float,
    label: str,
    width: int = 120,
    height: int = 40,
    good_direction: str = "down"  # "up" or "down" - which direction is good
) -> str:
    """
    Generate a slope graph showing change between two values.

    Tufte's slope graph is ideal for showing before/after comparisons.
    The slope immediately conveys direction and magnitude of change.

    Args:
        before: Starting value
        after: Ending value
        label: Description of what's being measured
        width: SVG width
        height: SVG height
        good_direction: Whether "up" or "down" is positive (for coloring)

    Returns:
        HTML string with slope graph
    """
    if before is None or after is None:
        return f'<span class="slope-graph muted">{label}: --</span>'

    change = after - before
    pct_change = ((after - before) / before * 100) if before else 0

    # Determine if change is good or bad
    is_good = (change < 0 and good_direction == "down") or (change > 0 and good_direction == "up")
    color = "#27ae60" if is_good else "#e74c3c" if change != 0 else "#666"
    arrow = "+" if change > 0 else "" if change < 0 else ""

    # Create simple slope visualization
    padding = 5
    plot_width = width - padding * 2

    # Normalize to plot coordinates
    min_val = min(before, after)
    max_val = max(before, after)
    val_range = max_val - min_val or 1

    y1 = padding + (height - padding * 2) * (1 - (before - min_val) / val_range) if val_range else height / 2
    y2 = padding + (height - padding * 2) * (1 - (after - min_val) / val_range) if val_range else height / 2

    svg = f'''<svg class="slope" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
        <line x1="{padding}" y1="{y1:.1f}" x2="{width - padding}" y2="{y2:.1f}"
              stroke="{color}" stroke-width="2" stroke-linecap="round"/>
        <circle cx="{padding}" cy="{y1:.1f}" r="3" fill="#666"/>
        <circle cx="{width - padding}" cy="{y2:.1f}" r="3" fill="{color}"/>
    </svg>'''

    return f'''<div class="slope-graph">
        <span class="slope-label">{label}</span>
        <span class="slope-before">{before:.1f}</span>
        {svg}
        <span class="slope-after" style="color: {color}">{after:.1f}</span>
        <span class="slope-change" style="color: {color}">({arrow}{pct_change:.1f}%)</span>
    </div>'''


def generate_small_multiples(
    datasets: Dict[str, List[float]],
    width: int = 80,
    height: int = 30,
    columns: int = 3
) -> str:
    """
    Generate small multiples - repeated small charts for comparison.

    Tufte: "Small multiples are economical: once viewers understand the design
    of one slice, they have immediate access to the data in all other slices."

    Args:
        datasets: Dictionary of {"Label": [values], ...}
        width: Width of each sparkline
        height: Height of each sparkline
        columns: Number of columns in the grid

    Returns:
        HTML string with grid of small multiples
    """
    if not datasets:
        return '<div class="small-multiples muted">No data</div>'

    html_parts = ['<div class="small-multiples" style="display: grid; '
                  f'grid-template-columns: repeat({columns}, 1fr); gap: 8px;">']

    for label, values in datasets.items():
        sparkline = generate_sparkline(values, width, height)
        current = values[-1] if values and values[-1] is not None else "--"
        current_str = f"{current:.1f}" if isinstance(current, (int, float)) else current

        html_parts.append(f'''
            <div class="small-multiple" style="text-align: center;">
                <div class="sm-label" style="font-size: 11px; color: #666; margin-bottom: 2px;">{label}</div>
                <div class="sm-sparkline">{sparkline}</div>
                <div class="sm-value" style="font-size: 12px; font-weight: 500;">{current_str}</div>
            </div>
        ''')

    html_parts.append('</div>')
    return ''.join(html_parts)


def generate_data_table(
    rows: List[Dict[str, Any]],
    columns: List[Tuple[str, str]],  # [(key, display_name), ...]
    highlight_column: Optional[str] = None
) -> str:
    """
    Generate a clean, minimal data table (Tufte-style).

    No heavy borders, zebra striping kept subtle, numbers right-aligned.

    Args:
        rows: List of row dictionaries
        columns: List of (key, display_name) tuples
        highlight_column: Column key to highlight

    Returns:
        HTML table string
    """
    if not rows:
        return '<p class="muted">No data available</p>'

    html_parts = ['''
        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
        <thead>
            <tr style="border-bottom: 2px solid #333;">
    ''']

    for key, display in columns:
        align = "right" if key in ("value", "duration", "volume", "count") else "left"
        html_parts.append(f'<th style="text-align: {align}; padding: 6px 8px; font-weight: 500;">{display}</th>')

    html_parts.append('</tr></thead><tbody>')

    for i, row in enumerate(rows):
        bg = "#fafafa" if i % 2 == 1 else "transparent"
        html_parts.append(f'<tr style="background: {bg}; border-bottom: 1px solid #eee;">')

        for key, _ in columns:
            val = row.get(key, "")
            align = "right" if key in ("value", "duration", "volume", "count") else "left"
            weight = "600" if key == highlight_column else "normal"

            # Format numbers nicely
            if isinstance(val, float):
                val = f"{val:,.1f}"
            elif isinstance(val, int):
                val = f"{val:,}"

            html_parts.append(f'<td style="text-align: {align}; padding: 6px 8px; font-weight: {weight};">{val}</td>')

        html_parts.append('</tr>')

    html_parts.append('</tbody></table>')
    return ''.join(html_parts)
