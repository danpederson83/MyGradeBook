# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MyGradeBook is a Flask web application for tracking children's school grades. It provides a mobile-optimized quick-entry interface for recording homework and test scores, with support for redos and CSV import/export.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server
python app.py
```

The app runs at http://127.0.0.1:5000 by default.

## Architecture

**Single-file Flask app** (`app.py`) with SQLite database (`instance/gradebook.db`).

### Database Models

- **Child**: A student (has many Gradebooks)
- **Gradebook**: A course for a child, e.g., "Math" (has many Grades). Stores default totals for homework (30) and tests (20).
- **Grade**: Individual score entry with type (homework/test), label (e.g., "Lesson 3"), score, total, and `redo_number` (0 = original, 1+ = redo attempts).

### Key Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Homework entry page |
| `/tests` | GET | Test entry page |
| `/grades` | GET | View all entered grades |
| `/children` | GET | Manage children (add/remove) |
| `/settings` | GET | Configure default totals, import/export CSV |
| `/add_grade` | POST | Submit a new grade (redirects to confirm if duplicate) |
| `/confirm_grade` | POST | Handle redo/overwrite/cancel for duplicate grades |
| `/export_csv` | GET | Download all grades as CSV |
| `/import_csv` | POST | Upload CSV to import grades |

### Redo System

When entering a grade for a label that already exists, a confirmation page appears with three options:
- **Mark as Redo**: Keeps previous scores, adds new score with incremented `redo_number`
- **Overwrite**: Replaces only the most recent score (preserves earlier redo history)
- **Cancel**: Returns without saving

### Auto-increment Logic

`get_next_number()` extracts the number from the last entry's label (e.g., "Lesson 3" → 4) to pre-populate the next entry.

### CSV Format

```csv
child,subject,type,label,score,total,redo_number,date
Emma,Math,homework,Lesson 1,28,30,0,2026-01-21 10:30:00
```

Import skips duplicates (same child + label + redo_number) and creates new children if needed.

## Templates

Jinja2 templates in `templates/`:
- `base.html` - Layout, nav, and mobile-responsive CSS
- `index.html` - Homework entry
- `tests.html` - Test entry
- `grades.html` - View all grades by child
- `children.html` - Add/remove children
- `settings.html` - Default totals and import/export
- `confirm_grade.html` - Redo/overwrite/cancel dialog

## UI Notes

- Mobile-first responsive design (stacked layout on phones, horizontal on desktop)
- Success messages appear as toast overlays in the child's card (no layout shift)
- Grade entry uses static "Lesson" / "Test" prefix with editable number field
- Total scores shown as static display (configured in Settings)
