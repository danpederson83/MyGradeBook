from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import csv
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gradebook.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'mygradebook-secret-key'
db = SQLAlchemy(app)


class Child(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    gradebooks = db.relationship('Gradebook', backref='child', lazy=True, cascade='all, delete-orphan')


class Gradebook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, default='Math')
    child_id = db.Column(db.Integer, db.ForeignKey('child.id'), nullable=False)
    homework_total = db.Column(db.Integer, default=30)
    test_total = db.Column(db.Integer, default=20)
    is_active = db.Column(db.Boolean, default=False)
    grades = db.relationship('Grade', backref='gradebook', lazy=True, cascade='all, delete-orphan')


class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gradebook_id = db.Column(db.Integer, db.ForeignKey('gradebook.id'), nullable=False)
    grade_type = db.Column(db.String(20), nullable=False)  # 'homework' or 'test'
    label = db.Column(db.String(100), nullable=False)  # 'Lesson 3' or 'Test 1'
    score = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    redo_number = db.Column(db.Integer, default=0)  # 0 = original, 1 = first redo, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def get_next_number(gradebook_id, grade_type):
    """Get the next lesson/test number based on the last entry."""
    last_grade = Grade.query.filter_by(
        gradebook_id=gradebook_id,
        grade_type=grade_type
    ).order_by(Grade.created_at.desc()).first()

    if not last_grade:
        return 1

    # Try to extract number from label like "Lesson 3" or "Test 2"
    label = last_grade.label
    parts = label.split()
    if parts:
        try:
            return int(parts[-1]) + 1
        except ValueError:
            pass
    return 1


def get_existing_grades(gradebook_id, label):
    """Get all existing grades for a specific label."""
    return Grade.query.filter_by(
        gradebook_id=gradebook_id,
        label=label
    ).order_by(Grade.redo_number.asc()).all()


def get_active_gradebook(child_id):
    """Get the active gradebook for a child, or create default if none exists."""
    gradebook = Gradebook.query.filter_by(child_id=child_id, is_active=True).first()
    if not gradebook:
        # Fall back to first gradebook and make it active
        gradebook = Gradebook.query.filter_by(child_id=child_id).first()
        if gradebook:
            gradebook.is_active = True
            db.session.commit()
    return gradebook


def build_children_data(grade_type):
    """Build children data for templates."""
    children = Child.query.all()
    children_data = []
    for child in children:
        gradebook = get_active_gradebook(child.id)
        if gradebook:
            next_num = get_next_number(gradebook.id, grade_type)
            children_data.append({
                'child': child,
                'gradebook': gradebook,
                'next_num': next_num
            })
    return children_data


@app.route('/')
def index():
    children_data = build_children_data('homework')
    success_gradebook = request.args.get('success')
    success_pct = request.args.get('pct')
    success_label = request.args.get('label')
    success_redo = request.args.get('redo')
    return render_template('index.html', children_data=children_data,
                           success_gradebook=success_gradebook, success_pct=success_pct,
                           success_label=success_label, success_redo=success_redo)


@app.route('/tests')
def tests():
    children_data = build_children_data('test')
    success_gradebook = request.args.get('success')
    success_pct = request.args.get('pct')
    success_label = request.args.get('label')
    success_redo = request.args.get('redo')
    return render_template('tests.html', children_data=children_data,
                           success_gradebook=success_gradebook, success_pct=success_pct,
                           success_label=success_label, success_redo=success_redo)


@app.route('/settings')
def settings():
    children = Child.query.all()
    children_data = []
    for child in children:
        gradebooks = Gradebook.query.filter_by(child_id=child.id).all()
        active_gradebook = get_active_gradebook(child.id)
        if gradebooks:
            children_data.append({
                'child': child,
                'gradebooks': gradebooks,
                'active_gradebook': active_gradebook
            })
    return render_template('settings.html', children_data=children_data)


@app.route('/add_grade', methods=['POST'])
def add_grade():
    gradebook_id = request.form.get('gradebook_id')
    grade_type = request.form.get('grade_type')
    label_prefix = request.form.get('label_prefix')
    label_num = request.form.get('label_num')
    score = request.form.get('score')
    total = request.form.get('total')

    redirect_to = 'index' if grade_type == 'homework' else 'tests'

    if not (gradebook_id and grade_type and label_prefix and label_num and score and total):
        return redirect(url_for(redirect_to))

    label = f"{label_prefix} {label_num}"

    score_val = float(score)
    total_val = float(total)

    # Check if grade with this label already exists
    existing_grades = get_existing_grades(int(gradebook_id), label)

    if existing_grades:
        # Show confirmation page
        gradebook = Gradebook.query.get(int(gradebook_id))
        child = gradebook.child
        current_grade = existing_grades[-1]  # Most recent attempt
        current_pct = round((current_grade.score / current_grade.total) * 100)
        new_pct = round((score_val / total_val) * 100)
        redo_count = len(existing_grades)

        return render_template('confirm_grade.html',
                               child=child,
                               label=label,
                               current_pct=current_pct,
                               new_pct=new_pct,
                               redo_count=redo_count,
                               gradebook_id=gradebook_id,
                               grade_type=grade_type,
                               score=score,
                               total=total)

    # No existing grade, just add it
    grade = Grade(
        gradebook_id=int(gradebook_id),
        grade_type=grade_type,
        label=label,
        score=score_val,
        total=total_val,
        redo_number=0
    )
    db.session.add(grade)
    db.session.commit()

    percentage = round((score_val / total_val) * 100)
    return redirect(url_for(redirect_to, success=gradebook_id, pct=percentage, label=label))


@app.route('/confirm_grade', methods=['POST'])
def confirm_grade():
    action = request.form.get('action')
    gradebook_id = request.form.get('gradebook_id')
    grade_type = request.form.get('grade_type')
    label = request.form.get('label')
    score = request.form.get('score')
    total = request.form.get('total')

    redirect_to = 'index' if grade_type == 'homework' else 'tests'

    if action == 'cancel':
        return redirect(url_for(redirect_to))

    score_val = float(score)
    total_val = float(total)
    existing_grades = get_existing_grades(int(gradebook_id), label)

    if action == 'redo':
        # Add as a new redo attempt
        redo_number = len(existing_grades)
        grade = Grade(
            gradebook_id=int(gradebook_id),
            grade_type=grade_type,
            label=label,
            score=score_val,
            total=total_val,
            redo_number=redo_number
        )
        db.session.add(grade)
        db.session.commit()

        percentage = round((score_val / total_val) * 100)
        return redirect(url_for(redirect_to, success=gradebook_id, pct=percentage, label=label, redo=redo_number))

    elif action == 'overwrite':
        # Only overwrite the most recent score
        most_recent = existing_grades[-1]
        most_recent.score = score_val
        most_recent.total = total_val
        most_recent.created_at = datetime.utcnow()
        db.session.commit()

        percentage = round((score_val / total_val) * 100)
        return redirect(url_for(redirect_to, success=gradebook_id, pct=percentage, label=label))

    return redirect(url_for(redirect_to))


@app.route('/grades')
def view_grades():
    children = Child.query.all()
    children_data = []
    for child in children:
        gradebook = get_active_gradebook(child.id)
        if gradebook:
            # Get all grades grouped by label for the active gradebook only
            homework = Grade.query.filter_by(
                gradebook_id=gradebook.id, grade_type='homework'
            ).order_by(Grade.label, Grade.redo_number).all()

            tests = Grade.query.filter_by(
                gradebook_id=gradebook.id, grade_type='test'
            ).order_by(Grade.label, Grade.redo_number).all()

            # Calculate averages (as percentages)
            homework_avg = None
            if homework:
                homework_avg = sum((g.score / g.total) * 100 for g in homework) / len(homework)

            test_avg = None
            if tests:
                test_avg = sum((g.score / g.total) * 100 for g in tests) / len(tests)

            # Total score is average of the two averages (not all grades combined)
            total_avg = None
            if homework_avg is not None and test_avg is not None:
                total_avg = (homework_avg + test_avg) / 2
            elif homework_avg is not None:
                total_avg = homework_avg
            elif test_avg is not None:
                total_avg = test_avg

            children_data.append({
                'child': child,
                'gradebook': gradebook,
                'homework': homework,
                'tests': tests,
                'homework_avg': homework_avg,
                'test_avg': test_avg,
                'total_avg': total_avg
            })
    return render_template('grades.html', children_data=children_data)


@app.route('/children')
def manage_children():
    children = Child.query.all()
    return render_template('children.html', children=children)


@app.route('/add_child', methods=['POST'])
def add_child():
    name = request.form.get('name')
    if name:
        child = Child(name=name)
        db.session.add(child)
        db.session.commit()

        # Create default Math gradebook and set as active
        gradebook = Gradebook(name='Math', child_id=child.id, is_active=True)
        db.session.add(gradebook)
        db.session.commit()

    return redirect(url_for('manage_children'))


@app.route('/remove_child/<int:child_id>', methods=['POST'])
def remove_child(child_id):
    child = Child.query.get_or_404(child_id)
    db.session.delete(child)
    db.session.commit()
    return redirect(url_for('manage_children'))


@app.route('/update_totals/<int:gradebook_id>', methods=['POST'])
def update_totals(gradebook_id):
    gradebook = Gradebook.query.get_or_404(gradebook_id)
    homework_total = request.form.get('homework_total')
    test_total = request.form.get('test_total')

    if homework_total:
        gradebook.homework_total = int(homework_total)
    if test_total:
        gradebook.test_total = int(test_total)

    db.session.commit()
    return redirect(url_for('settings'))


@app.route('/set_active_course/<int:gradebook_id>', methods=['POST'])
def set_active_course(gradebook_id):
    gradebook = Gradebook.query.get_or_404(gradebook_id)
    # Deactivate all other gradebooks for this child
    Gradebook.query.filter_by(child_id=gradebook.child_id).update({'is_active': False})
    # Activate the selected one
    gradebook.is_active = True
    db.session.commit()
    return redirect(url_for('settings'))


@app.route('/add_course/<int:child_id>', methods=['POST'])
def add_course(child_id):
    child = Child.query.get_or_404(child_id)
    name = request.form.get('course_name', '').strip()
    if name:
        # Check if course already exists for this child
        existing = Gradebook.query.filter_by(child_id=child_id, name=name).first()
        if not existing:
            gradebook = Gradebook(name=name, child_id=child_id, is_active=False)
            db.session.add(gradebook)
            db.session.commit()
    return redirect(url_for('settings'))


@app.route('/rename_course/<int:gradebook_id>', methods=['POST'])
def rename_course(gradebook_id):
    gradebook = Gradebook.query.get_or_404(gradebook_id)
    new_name = request.form.get('new_name', '').strip()
    if new_name:
        # Check if name already exists for this child
        existing = Gradebook.query.filter_by(child_id=gradebook.child_id, name=new_name).first()
        if not existing or existing.id == gradebook_id:
            gradebook.name = new_name
            db.session.commit()
    return redirect(url_for('settings'))


@app.route('/delete_course/<int:gradebook_id>', methods=['POST'])
def delete_course(gradebook_id):
    gradebook = Gradebook.query.get_or_404(gradebook_id)
    child_id = gradebook.child_id
    was_active = gradebook.is_active

    # Don't allow deleting the last course
    course_count = Gradebook.query.filter_by(child_id=child_id).count()
    if course_count > 1:
        db.session.delete(gradebook)
        db.session.commit()

        # If we deleted the active course, activate another one
        if was_active:
            next_gradebook = Gradebook.query.filter_by(child_id=child_id).first()
            if next_gradebook:
                next_gradebook.is_active = True
                db.session.commit()

    return redirect(url_for('settings'))


@app.route('/export_csv')
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow(['child', 'subject', 'type', 'label', 'score', 'total', 'redo_number', 'date'])

    # Data rows
    children = Child.query.all()
    for child in children:
        for gradebook in child.gradebooks:
            for grade in gradebook.grades:
                writer.writerow([
                    child.name,
                    gradebook.name,
                    grade.grade_type,
                    grade.label,
                    grade.score,
                    grade.total,
                    grade.redo_number,
                    grade.created_at.strftime('%Y-%m-%d %H:%M:%S') if grade.created_at else ''
                ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=gradebook_export.csv'}
    )


@app.route('/import_csv', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(url_for('settings'))

    file = request.files['file']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('settings'))

    if not file.filename.endswith('.csv'):
        flash('Please upload a CSV file')
        return redirect(url_for('settings'))

    try:
        stream = io.StringIO(file.stream.read().decode('utf-8'))
        reader = csv.DictReader(stream)

        imported_count = 0
        for row in reader:
            child_name = row.get('child', '').strip()
            subject = row.get('subject', 'Math').strip()
            grade_type = row.get('type', '').strip()
            label = row.get('label', '').strip()
            score = row.get('score', '').strip()
            total = row.get('total', '').strip()
            redo_number = row.get('redo_number', '0').strip()

            if not all([child_name, grade_type, label, score, total]):
                continue

            # Find or create child
            child = Child.query.filter_by(name=child_name).first()
            if not child:
                child = Child(name=child_name)
                db.session.add(child)
                db.session.commit()

            # Find or create gradebook
            gradebook = Gradebook.query.filter_by(child_id=child.id, name=subject).first()
            if not gradebook:
                gradebook = Gradebook(name=subject, child_id=child.id)
                db.session.add(gradebook)
                db.session.commit()

            # Check if this exact grade already exists
            existing = Grade.query.filter_by(
                gradebook_id=gradebook.id,
                label=label,
                redo_number=int(redo_number)
            ).first()

            if not existing:
                grade = Grade(
                    gradebook_id=gradebook.id,
                    grade_type=grade_type,
                    label=label,
                    score=float(score),
                    total=float(total),
                    redo_number=int(redo_number)
                )
                db.session.add(grade)
                imported_count += 1

        db.session.commit()
        flash(f'Imported {imported_count} grades')

    except Exception as e:
        flash(f'Error importing file: {str(e)}')

    return redirect(url_for('settings'))


with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)
