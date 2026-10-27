# ✨ Lumen — Personal Expense Tracker

Lumen is an advanced, aesthetic personal finance and expense tracker built with **Python**, **Streamlit**, and **Plotly**. Designed to go far beyond basic spreadsheet-style expense trackers, Lumen combines glassmorphic UI design, animated background auroras, and curated dynamic themes with an analytics and budgeting engine.

---

## 🚀 Quick Start

### 1. Requirements
Ensure you have Python 3.10+ installed. Install the dependencies:

```bash
pip install -r requirements.txt
```

### 2. Run the App
Launch Lumen locally:

```bash
python -m streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`.

---

## 🎨 Themes & Design Aesthetics

Lumen includes 7 hand-crafted themes that dynamically re-style native Streamlit widgets, forms, tables, data editors, and Plotly charts in real time:

| Theme | Mood & Palette | Base |
|---|---|---|
| 🌌 **Midnight** | Deep indigo night sky with violet accents and soft neon cyan | Dark |
| 🌅 **Sunset** | Warm dusk gradients of coral, magenta, purple, and gold | Dark |
| 🦄 **Dream** | Soft pastel clouds of candy pink, lavender, and mint | Light |
| 🌿 **Aurora** | Northern lights with emerald, teal, and violet pulses | Dark |
| 🌊 **Ocean** | Deep sea sapphire and turquoise currents | Dark |
| 🌑 **Dark** | Sleek, minimal dark mode with crisp purple & neon accents | Dark |
| ☀️ **Light** | Crisp, bright daytime mode with royal indigo & amber | Light |

### Theme Switcher Features
- **Sidebar Quick-Switch**: Dropdown menu and a 1-tap **Dark Mode** toggle in the sidebar.
- **Theme Gallery in Settings**: Visual cards showcasing each theme's gradient swatch and palette dots.
- **Tri-Layer Synchronisation**: Changing themes synchronises Streamlit's native theme configuration, custom CSS glassmorphism and background aurora, and Plotly chart colorways simultaneously.

---

## 🌟 Key Features

### 1. 📊 Interactive Dashboard
- **Monthly Summary KPIs**: Total Income, Total Expenses, Net Savings, and Remaining Budget with delta percentages vs. previous month.
- **Spending Pace Chart**: Compare cumulative spending day-by-day against last month and your monthly budget limit.
- **Where It Went Donut**: Instant visual breakdown of expenses with an interactive center label.
- **Recent Activity Feed**: Sleek transaction list with category icons and formatted amounts.
- **Smart Insights Engine**: Automated rules detect top spend categories, month-over-month shifts, projected end-of-month spending, no-spend days, and savings rate milestones.

### 2. ⚡ Fast Transaction Logging
- **1-Tap Quick Add Dialog**: Accessible from the dashboard navigation or top bar.
- **Favourite / Frequent Expenses**: Automatic detection of your top recurring expenses (e.g. coffee, lunch, groceries) for 1-click logging.
- **Full Form**: Supports date, category (with emoji badges), payment methods (Card, Cash, UPI / Wallet, Bank Transfer, Other), tags, and descriptions.

### 3. 🔍 Transactions Table & Inline Editor
- **Multi-Filter Bar**: Real-time search across descriptions, categories, and tags; filter by Type, Date Range, Category multiselect, Payment Method multiselect, and Amount Slider.
- **Live Data Editor**: Powered by `st.data_editor` to edit date, category, type, amount, description, payment method, and tags directly inside the table with 1-click save.
- **Batch Selection & Delete**: Checkbox selection for multi-row deletion with confirmation modal.
- **Single-Row Edit Dialog**: Dedicated modal for full editing.
- **Filtered CSV Export**: Download exactly what you've filtered with one click.

### 4. 📈 Deep Analytics
- **Flexible Time Horizons**: Switch between `30D`, `90D`, `6M`, `YTD`, `1Y`, and `All`.
- **Cash Flow History**: Grouped bar chart comparing Income vs. Expenses month-by-month with net savings trend line.
- **Category Donut & Treemap**: Hierarchical spending map breaking down categories into specific merchants and descriptions.
- **Payment Method Distribution**: Horizontal bar visualization of spending methods.
- **Daily Spending & 7-Day Moving Average**: Identify spending spikes and trend lines.
- **Weekday Spend Distribution**: See which days of the week cost you the most.
- **Spending Heatmap Calendar**: GitHub-style weekly calendar matrix highlighting high-spend days.
- **Category Mix Over Time**: Stacked monthly bar chart revealing how your budget proportions evolve.
- **Top 10 Biggest Purchases**: Ranked table with embedded progress bars.

### 5. 🎯 Budgets & 🏆 Savings Goals
- **Overall & Category Budgets**: Set a master monthly spending target as well as individual limits per category.
- **Visual SVG Progress Rings**: Circular gauges showing percentage used, remaining budget, and warning colors when nearing or exceeding targets.
- **Savings Goals Tracker**: Set target amounts and target dates for long-term goals (Emergency Fund, Vacations, Gadgets).
- **Goal Contributions**: Increment savings with quick contribution buttons, countdown timers, required monthly savings rate, and celebratory balloon animations upon completion.

### 6. 🔁 Automated Recurring Rules
- **Subscriptions & Fixed Costs**: Define recurring rules for rent, utilities, subscriptions, or salaries on Weekly, Monthly, or Yearly cadences.
- **Auto-Posting on Launch**: Any due recurring transactions are automatically posted to your ledger whenever the app opens.
- **Pause / Resume**: Toggle individual rules active or inactive at any time.

### 7. 💾 Data Management & Privacy
- **Local SQLite Database**: All records are stored safely in `data/lumen.db` on your local filesystem — no external accounts or third-party cloud trackers required.
- **One-Click Demo Data**: Instantly seed ~6 months of realistic sample data to explore every feature.
- **Full JSON Backup & Restore**: Export and restore your complete setup (transactions, categories, budgets, goals, recurring rules, and preferences).
- **Custom Categories**: Add, edit, or delete expense and income categories with custom emoji badges.
- **Currency Customisation**: Switch between `$`, `€`, `£`, `₹`, `¥`, `₩`, `₽`, `R$`, `A$`, `C$`, `CHF`, and `د.إ`.

---

## 📁 Project Structure

```
personal expense tracker/
├── .streamlit/
│   └── config.toml      # Theme defaults and Streamlit configuration
├── assets/              # Dynamically generated SVG theme logos
├── data/
│   └── lumen.db         # Local SQLite database (auto-created)
├── app.py               # Main application entry point & navigation
├── db.py                # SQLite database layer, seed data & backup tools
├── themes.py            # 7 design themes, CSS styles & Plotly templates
├── ui.py                # Reusable HTML glassmorphism components & charts
├── views.py             # All 7 app pages & views
├── requirements.txt     # Python dependencies
└── README.md            # Documentation
```
