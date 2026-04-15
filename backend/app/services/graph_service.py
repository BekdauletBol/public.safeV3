"""
Graph generation service — produces PNG charts from analytics data.
Uses matplotlib with a dark, modern style to match the dashboard aesthetic.
"""

import io
import base64
from typing import List, Dict, Optional, Tuple

import matplotlib
matplotlib.use("Agg")  # non-interactive backend — safe in server context
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
import numpy as np
from datetime import datetime


# ── Shared style ──────────────────────────────────────────────────────────────

_BG = "#0f172a"
_GRID = "#1e293b"
_ACCENT = "#38bdf8"
_ACCENT2 = "#818cf8"
_TEXT = "#e2e8f0"
_SUBTEXT = "#94a3b8"


def _apply_dark_style(fig, ax):
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    ax.tick_params(colors=_SUBTEXT, labelsize=9)
    ax.xaxis.label.set_color(_SUBTEXT)
    ax.yaxis.label.set_color(_SUBTEXT)
    for spine in ax.spines.values():
        spine.set_edgecolor(_GRID)
    ax.grid(True, color=_GRID, linewidth=0.8, linestyle="--", alpha=0.6)
    ax.set_axisbelow(True)


# ── Traffic area/line chart ────────────────────────────────────────────────────

def generate_traffic_graph(
    time_series: List[Dict],
    camera_name: str = "",
    title: str = "Traffic Over Time",
    granularity: str = "hourly",
    figsize: Tuple[int, int] = (12, 5),
    dpi: int = 130,
) -> bytes:
    """
    Render a time-series traffic chart and return raw PNG bytes.

    Expects each item in `time_series` to have at least one of:
      - hour_bucket / day_bucket / timestamp  (datetime string)
      - avg_count / count                     (numeric)
    """
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    _apply_dark_style(fig, ax)

    if not time_series:
        ax.text(
            0.5, 0.5, "No data available",
            ha="center", va="center", color=_SUBTEXT,
            transform=ax.transAxes, fontsize=13,
        )
    else:
        # Parse timestamps and values
        times, counts, entering, exiting = [], [], [], []
        for row in time_series:
            ts_raw = (
                row.get("hour_bucket")
                or row.get("day_bucket")
                or row.get("timestamp")
            )
            if ts_raw is None:
                continue
            if isinstance(ts_raw, str):
                try:
                    ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")).replace(tzinfo=None)
                except ValueError:
                    continue
            else:
                ts = ts_raw

            val = row.get("avg_count") or row.get("count") or 0
            times.append(ts)
            counts.append(float(val))
            entering.append(float(row.get("total_entering", row.get("entering", 0)) or 0))
            exiting.append(float(row.get("total_exiting", row.get("exiting", 0)) or 0))

        if times:
            ax.fill_between(times, counts, alpha=0.18, color=_ACCENT)
            ax.plot(times, counts, color=_ACCENT, linewidth=2, label="Avg Count", zorder=3)

            if any(v > 0 for v in entering):
                ax.plot(times, entering, color=_ACCENT2, linewidth=1.4,
                        linestyle="--", label="Entering", zorder=2, alpha=0.8)
            if any(v > 0 for v in exiting):
                ax.plot(times, exiting, color="#f472b6", linewidth=1.4,
                        linestyle=":", label="Exiting", zorder=2, alpha=0.8)

            # X-axis date formatting
            if granularity == "daily":
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d %H:%M"))
            fig.autofmt_xdate(rotation=30, ha="right")

            ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
            ax.legend(
                frameon=False, labelcolor=_TEXT, fontsize=9,
                loc="upper left",
            )

    subtitle = f" — {camera_name}" if camera_name and camera_name != "All Cameras" else ""
    ax.set_title(
        title + subtitle,
        color=_TEXT, fontsize=13, fontweight="bold", pad=12,
    )
    ax.set_xlabel("Time", labelpad=8)
    ax.set_ylabel("People Count", labelpad=8)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=_BG)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ── Bar summary chart ──────────────────────────────────────────────────────────

def generate_bar_summary(
    labels: List[str],
    values: List[float],
    title: str = "Summary",
    ylabel: str = "Count",
    figsize: Tuple[int, int] = (10, 5),
    dpi: int = 130,
) -> bytes:
    """
    Render a horizontal bar chart and return raw PNG bytes.
    Useful for per-camera comparison summaries.
    """
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    _apply_dark_style(fig, ax)

    if not labels:
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                color=_SUBTEXT, transform=ax.transAxes, fontsize=13)
    else:
        y_pos = np.arange(len(labels))
        colors = [_ACCENT if i % 2 == 0 else _ACCENT2 for i in range(len(labels))]
        bars = ax.barh(y_pos, values, color=colors, alpha=0.85, height=0.55)

        # Value labels
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_width() + max(values) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{int(val):,}",
                va="center", color=_TEXT, fontsize=9,
            )

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, color=_TEXT, fontsize=9)
        ax.invert_yaxis()
        ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))

    ax.set_title(title, color=_TEXT, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel(ylabel, labelpad=8)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=_BG)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ── Hourly heatmap ─────────────────────────────────────────────────────────────

def generate_hourly_heatmap(
    hourly_by_day: Dict[str, List[float]],
    title: str = "Weekly Hourly Heatmap",
    figsize: Tuple[int, int] = (14, 5),
    dpi: int = 130,
) -> bytes:
    """
    Render a 7 × 24 heatmap (day vs hour) and return raw PNG bytes.

    `hourly_by_day` is expected to be:
        {"Monday": [avg_count_hour_0, ..., avg_count_hour_23], ...}
    """
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    matrix = np.array([
        hourly_by_day.get(day, [0.0] * 24) for day in day_names
    ])

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    _apply_dark_style(fig, ax)

    cmap = plt.cm.YlOrRd
    im = ax.imshow(matrix, aspect="auto", cmap=cmap, interpolation="nearest")

    ax.set_xticks(np.arange(24))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(24)], fontsize=7, rotation=45, ha="right", color=_SUBTEXT)
    ax.set_yticks(np.arange(len(day_names)))
    ax.set_yticklabels(day_names, color=_TEXT, fontsize=9)

    cbar = fig.colorbar(im, ax=ax, pad=0.02)
    cbar.ax.tick_params(colors=_SUBTEXT, labelsize=8)
    cbar.set_label("Avg People Count", color=_SUBTEXT, fontsize=9)

    ax.set_title(title, color=_TEXT, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Hour of Day", color=_SUBTEXT, labelpad=8)

    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=_BG)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ── Utility ────────────────────────────────────────────────────────────────────

def png_to_base64(png_bytes: bytes) -> str:
    """Encode raw PNG bytes as a base64 data-URI string."""
    return base64.b64encode(png_bytes).decode("utf-8")
