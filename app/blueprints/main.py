import os
import sys
from flask import Blueprint, render_template, request, make_response, flash
from app.models import Experiment
from app.utils import (
    calculate_experiment,
    build_therm_conductivity_steps,
    build_natural_convection_steps,
    format_theory_html,
)

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    experiments = Experiment.query.all()
    return render_template('index.html', experiments=experiments)

@bp.route('/experiment/<slug>')
def experiment_view(slug):
    experiment = Experiment.query.filter_by(slug=slug).first_or_404()
    return render_template('experiment.html', experiment=experiment)

@bp.route('/experiment/<slug>/report', methods=['POST'])
def generate_report(slug):
    experiment = Experiment.query.filter_by(slug=slug).first_or_404()
    
    # Get form data
    inputs = request.form.to_dict()
    
    # Perform Calc
    calc_data = calculate_experiment(slug, inputs)
    if "error" in calc_data:
        flash(calc_data["error"])
        return render_template('experiment.html', experiment=experiment)

    steps = []
    steps_by_trial = []
    if slug == "therm-conductivity-metal-rod":
        steps = build_therm_conductivity_steps(calc_data)
    elif slug == "natural-convection-vertical-tube":
        steps_by_trial = build_natural_convection_steps(calc_data)
    
    # Context for template
    context = {
        'experiment': experiment,
        'student': {
            'name': inputs.get('student_name', 'Student'),
            'usn': inputs.get('usn', 'N/A'),
            'date': inputs.get('date', 'N/A'),
            'instructor': inputs.get('instructor', 'N/A')
        },
        'data': calc_data,
        'raw_inputs': calc_data.get('raw_inputs', {}),
        'normalized': calc_data.get('normalized', {}),
        'results': calc_data['results'],
        'trace': calc_data.get('trace', {}),
        'warnings': calc_data.get('warnings', []),
        'steps': steps,
        'steps_by_trial': steps_by_trial,
        'explanation_blocks': calc_data.get('explanation_blocks', []),
        'final_explanation': calc_data.get('final_explanation', ''),
        'theory_html': format_theory_html(experiment.content.get('theory', ''))
    }
    
    # Custom filter for LaTeX -> MathML
    def latex_filter(s):
        try:
            import latex2mathml.converter
            return latex2mathml.converter.convert(s)
        except ImportError:
            return s
        except Exception:
            return s
            
    # Render HTML
    html = render_template('report.html', **context, latex=latex_filter)
    
    def render_with_xhtml2pdf():
        from xhtml2pdf import pisa
        from io import BytesIO

        pdf_io = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf_io, encoding="utf-8")
        if pisa_status.err:
            raise Exception("xhtml2pdf conversion failed")

        response = make_response(pdf_io.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=report_{slug}.pdf'
        return response

    def render_with_weasyprint():
        import weasyprint
        pdf = weasyprint.HTML(string=html).write_pdf()

        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=report_{slug}.pdf'
        return response

    # Convert to PDF (avoid WeasyPrint on Windows unless explicitly enabled)
    try:
        force_weasy = os.getenv("USE_WEASYPRINT", "").lower() in ["1", "true", "yes"]
        if sys.platform == "win32" and not force_weasy:
            return render_with_xhtml2pdf()
        try:
            return render_with_weasyprint()
        except Exception:
            return render_with_xhtml2pdf()
    except Exception as err:
        context["print_hint"] = True
        html_fallback = render_template('report.html', **context, latex=latex_filter)
        response = make_response(html_fallback)
        response.headers['Content-Type'] = 'text/html; charset=utf-8'
        return response
