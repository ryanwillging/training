"""
Data Analyst Agent - Generates Tufte-style training reports.

This module creates clean, data-dense HTML reports following Edward Tufte's
principles of information design:
- High data-ink ratio
- No chartjunk
- Small multiples for comparison
- Sparklines for trends
- Integrated text and graphics
"""

from analyst.report_generator import TrainingReportGenerator
from analyst.visualizations import (
    generate_sparkline,
    generate_small_multiples,
    generate_slope_graph,
    generate_bar_sparkline
)

__all__ = [
    'TrainingReportGenerator',
    'generate_sparkline',
    'generate_small_multiples',
    'generate_slope_graph',
    'generate_bar_sparkline'
]
