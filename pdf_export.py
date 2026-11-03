"""PDF Report Generation for Lumen Expense Tracker using ReportLab."""

from __future__ import annotations

import io
from datetime import date, datetime
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _safe_str(val: Any) -> str:
    if val is None:
        return ""
    return str(val)


def generate_expense_pdf(
    df: pd.DataFrame,
    title: str = "Financial Expense Report",
    subtitle: str = "",
    user_name: str = "User",
    currency: str = "$",
    budget_total: float = 0.0,
) -> bytes:
    """Generate a beautifully formatted PDF report from transactions dataframe."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#3B4CCA")
    accent_color = colors.HexColor("#7C3AED")
    income_color = colors.HexColor("#059669")
    expense_color = colors.HexColor("#DC2626")
    text_dark = colors.HexColor("#1F2937")
    text_muted = colors.HexColor("#6B7280")
    border_color = colors.HexColor("#E5E7EB")
    bg_light = colors.HexColor("#F9FAFB")

    # Custom typography styles
    style_title = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=primary_color,
    )
    style_sub = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=text_muted,
    )
    style_section = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceAfter=6,
    )
    style_cell = ParagraphStyle(
        "CellText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=text_dark,
    )
    style_cell_bold = ParagraphStyle(
        "CellTextBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=text_dark,
    )
    style_cell_num = ParagraphStyle(
        "CellNum",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        alignment=2,  # Right align
        textColor=text_dark,
    )
    style_cell_inc = ParagraphStyle(
        "CellInc",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        alignment=2,
        textColor=income_color,
    )
    style_cell_exp = ParagraphStyle(
        "CellExp",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        alignment=2,
        textColor=expense_color,
    )
    style_kpi_label = ParagraphStyle(
        "KPILabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=text_muted,
        alignment=1,
    )
    style_kpi_val = ParagraphStyle(
        "KPIVal",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        alignment=1,
    )

    story = []

    # 1. Header banner
    header_data = [
        [
            Paragraph(f"<b>LUMEN</b> · {title}", style_title),
            Paragraph(f"Generated: {datetime.now():%b %d, %Y %H:%M}<br/>Prepared for: <b>{user_name}</b>", style_sub),
        ]
    ]
    header_table = Table(header_data, colWidths=[350, 190])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(header_table)
    if subtitle:
        story.append(Paragraph(subtitle, style_sub))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceBefore=0, spaceAfter=12))

    # 2. Executive KPI summary
    if not df.empty:
        exp_df = df[df["type"] == "Expense"]
        inc_df = df[df["type"] == "Income"]
        total_exp = float(exp_df["amount"].sum()) if not exp_df.empty else 0.0
        total_inc = float(inc_df["amount"].sum()) if not inc_df.empty else 0.0
        net = total_inc - total_exp
        tx_count = len(df)
        savings_pct = (net / total_inc * 100) if total_inc > 0 else 0.0
    else:
        total_exp = 0.0
        total_inc = 0.0
        net = 0.0
        tx_count = 0
        savings_pct = 0.0

    cur_sym = currency

    kpi_inc_style = ParagraphStyle("KInc", parent=style_kpi_val, textColor=income_color)
    kpi_exp_style = ParagraphStyle("KExp", parent=style_kpi_val, textColor=expense_color)
    kpi_net_style = ParagraphStyle("KNet", parent=style_kpi_val, textColor=income_color if net >= 0 else expense_color)

    kpi_data = [
        [
            Paragraph("TOTAL INCOME", style_kpi_label),
            Paragraph("TOTAL EXPENSES", style_kpi_label),
            Paragraph("NET SAVINGS", style_kpi_label),
            Paragraph("SAVINGS RATE", style_kpi_label),
            Paragraph("TRANSACTIONS", style_kpi_label),
        ],
        [
            Paragraph(f"+{cur_sym}{total_inc:,.2f}", kpi_inc_style),
            Paragraph(f"-{cur_sym}{total_exp:,.2f}", kpi_exp_style),
            Paragraph(f"{'+' if net >= 0 else ''}{cur_sym}{net:,.2f}", kpi_net_style),
            Paragraph(f"{savings_pct:.0f}%", style_kpi_val),
            Paragraph(f"{tx_count:,}", style_kpi_val),
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[108, 108, 108, 108, 108])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg_light),
                ("BOX", (0, 0), (-1, -1), 1, border_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(kpi_table)
    story.append(Spacer(1, 14))

    # 3. Category Breakdown Table
    if not df.empty and total_exp > 0:
        story.append(Paragraph("Category Spending Breakdown", style_section))
        exp_df = df[df["type"] == "Expense"]
        cat_summary = (
            exp_df.groupby("category")
            .agg(count=("id", "count"), total=("amount", "sum"))
            .reset_index()
            .sort_values("total", ascending=False)
        )
        cat_data = [
            [
                Paragraph("<b>Category</b>", style_cell_bold),
                Paragraph("<b>Transactions</b>", style_cell_bold),
                Paragraph("<b>Total Spent</b>", style_cell_bold),
                Paragraph("<b>% of Expenses</b>", style_cell_bold),
            ]
        ]
        for _, row in cat_summary.iterrows():
            c_name = _safe_str(row["category"])
            c_cnt = int(row["count"])
            c_tot = float(row["total"])
            c_pct = (c_tot / total_exp * 100) if total_exp > 0 else 0
            cat_data.append(
                [
                    Paragraph(c_name, style_cell),
                    Paragraph(str(c_cnt), style_cell_num),
                    Paragraph(f"{cur_sym}{c_tot:,.2f}", style_cell_num),
                    Paragraph(f"{c_pct:.1f}%", style_cell_num),
                ]
            )

        cat_table = Table(cat_data, colWidths=[220, 100, 120, 100])
        cat_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
                    ("TOPPADDING", (0, 0), (-1, 0), 5),
                    ("GRID", (0, 0), (-1, -1), 0.5, border_color),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
                    ("TOPPADDING", (0, 1), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
                ]
            )
        )
        story.append(cat_table)
        story.append(Spacer(1, 14))

    # 4. Detailed Transactions Ledger
    story.append(Paragraph("Transactions Ledger", style_section))
    if df.empty:
        story.append(Paragraph("No transactions recorded for this period.", style_sub))
    else:
        sorted_df = df.sort_values("date", ascending=False)
        tx_data = [
            [
                Paragraph("<b>Date</b>", style_cell_bold),
                Paragraph("<b>Description</b>", style_cell_bold),
                Paragraph("<b>Category</b>", style_cell_bold),
                Paragraph("<b>Method</b>", style_cell_bold),
                Paragraph("<b>Amount</b>", style_cell_bold),
            ]
        ]
        for _, r in sorted_df.iterrows():
            d_str = r["date"].strftime("%Y-%m-%d") if hasattr(r["date"], "strftime") else str(r["date"])[:10]
            desc = _safe_str(r["description"]) or _safe_str(r["category"])
            cat = _safe_str(r["category"])
            pm = _safe_str(r["payment_method"])
            is_inc = r["type"] == "Income"
            amt = float(r["amount"])
            amt_style = style_cell_inc if is_inc else style_cell_exp
            amt_str = f"{'+' if is_inc else '-'}{cur_sym}{amt:,.2f}"

            tx_data.append(
                [
                    Paragraph(d_str, style_cell),
                    Paragraph(desc, style_cell),
                    Paragraph(cat, style_cell),
                    Paragraph(pm, style_cell),
                    Paragraph(amt_str, amt_style),
                ]
            )

        tx_table = Table(tx_data, colWidths=[70, 190, 120, 80, 80], repeatRows=1)
        tx_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF2FF")),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
                    ("TOPPADDING", (0, 0), (-1, 0), 5),
                    ("GRID", (0, 0), (-1, -1), 0.5, border_color),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, bg_light]),
                    ("TOPPADDING", (0, 1), (-1, -1), 3.5),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 3.5),
                ]
            )
        )
        story.append(tx_table)

    def _add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(text_muted)
        canvas.drawString(36, 20, "Lumen Personal Expense Tracker · Confidential")
        canvas.drawRightString(612 - 36, 20, f"Page {doc.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_add_footer, onLaterPages=_add_footer)
    return buf.getvalue()
