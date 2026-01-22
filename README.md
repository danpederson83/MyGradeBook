# MyGradeBook

A mobile-optimized Flask web application for tracking children's school grades. Quickly record homework and test scores with support for redos and CSV import/export.

## Features

- **Quick Grade Entry** - Mobile-friendly interface for fast score input
- **Multiple Children** - Track grades for multiple students
- **Subject Management** - Organize grades by subject (Math, Reading, etc.)
- **Redo Tracking** - Record multiple attempts while preserving history
- **Auto-increment** - Automatically suggests the next lesson/test number
- **CSV Import/Export** - Backup and restore your data

## Installation

```bash
# Clone the repository
git clone https://github.com/danpederson83/MyGradeBook.git
cd MyGradeBook

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

The app runs at http://127.0.0.1:5000

## Usage

1. **Add Children** - Go to the Children page to add students
2. **Enter Grades** - Use the Homework or Tests page to record scores
3. **View Grades** - See all recorded grades organized by child
4. **Settings** - Configure default point totals and import/export data

## Redo System

When entering a grade for a lesson that already exists, you'll be prompted to:
- **Mark as Redo** - Keep the original score and add the new attempt
- **Overwrite** - Replace the most recent score
- **Cancel** - Return without saving

## CSV Format

Export and import grades using this format:

```csv
child,subject,type,label,score,total,redo_number,date
Emma,Math,homework,Lesson 1,28,30,0,2026-01-21 10:30:00
```

## Tech Stack

- Python / Flask
- SQLite database
- Jinja2 templates
- Mobile-responsive CSS

## License

MIT
