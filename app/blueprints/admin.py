from flask import Blueprint, render_template, request, flash, redirect, url_for
from app.models import Experiment, StudentRun
from app.extensions import db
import json

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
def dashboard():
    experiments = Experiment.query.all()
    # Simple stats
    stats = {
        'total_experiments': len(experiments),
        'total_runs': StudentRun.query.count()
    }
    return render_template('admin/dashboard.html', experiments=experiments, stats=stats)

@bp.route('/experiment/<int:id>/edit', methods=['GET', 'POST'])
def edit_experiment(id):
    experiment = Experiment.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Update basic fields
            experiment.title = request.form['title']
            experiment.slug = request.form['slug']
            
            # Update Content JSON
            json_content = request.form['content_json']
            experiment.content = json.loads(json_content)
            
            db.session.commit()
            flash('Experiment updated successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        except json.JSONDecodeError:
            flash('Invalid JSON format in content field.', 'danger')
        except Exception as e:
            flash(f'Error updating experiment: {str(e)}', 'danger')
            
    return render_template('admin/edit_experiment.html', experiment=experiment)

@bp.route('/experiment/new', methods=['GET', 'POST'])
def new_experiment():
    if request.method == 'POST':
        try:
            title = request.form['title']
            slug = request.form['slug']
            json_content = request.form['content_json']
            content = json.loads(json_content)
            
            exp = Experiment(title=title, slug=slug, content=content)
            db.session.add(exp)
            db.session.commit()
            
            flash('Experiment created successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        except Exception as e:
            flash(f'Error creating experiment: {str(e)}', 'danger')
            
    # Default template for new experiment
    default_content = {
        "aim": "Aim...",
        "apparatus": "...",
        "theory": "...",
        "procedure": ["Step 1"],
        "inputs": [],
        "constants": {},
        "viva": []
    }
    
    return render_template('admin/edit_experiment.html', experiment=None, default_json=json.dumps(default_content, indent=4))
