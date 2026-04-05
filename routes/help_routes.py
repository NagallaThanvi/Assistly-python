"""Help center and language preference routes."""

from flask import Blueprint, current_app, g, redirect, render_template, request, session, url_for

from utils.i18n import normalize_language


help_bp = Blueprint("help", __name__)


FAQ_ITEMS = [
    {
        "category": "Getting Started",
        "question_en": "How do I join a community?",
        "answer_en": "Open Communities, search for your area, and request access or join if it is public.",
        "question_es": "¿Cómo me uno a una comunidad?",
        "answer_es": "Abre Comunidades, busca tu zona y solicita acceso o únete si es pública.",
    },
    {
        "category": "Requests",
        "question_en": "How do I create a request?",
        "answer_en": "Go to New Request, choose your community, add details, and submit the form.",
        "question_es": "¿Cómo creo una solicitud?",
        "answer_es": "Ve a Nueva solicitud, elige tu comunidad, agrega detalles y envía el formulario.",
    },
    {
        "category": "Volunteer Work",
        "question_en": "How do volunteers accept a task?",
        "answer_en": "Open the dashboard, switch to volunteer mode, and accept a request that matches your community.",
        "question_es": "¿Cómo acepta un voluntario una tarea?",
        "answer_es": "Abre el panel, cambia a modo voluntario y acepta una solicitud que coincida con tu comunidad.",
    },
    {
        "category": "Accessibility",
        "question_en": "How do I use larger text or high contrast?",
        "answer_en": "Use the Accessibility button in the header to switch visual modes at any time.",
        "question_es": "¿Cómo uso texto grande o alto contraste?",
        "answer_es": "Usa el botón de Accesibilidad en el encabezado para cambiar el modo visual cuando quieras.",
    },
    {
        "category": "Language",
        "question_en": "Can I use Spanish?",
        "answer_en": "Yes. Switch the language using the Language menu and the interface will update for supported pages.",
        "question_es": "¿Puedo usar español?",
        "answer_es": "Sí. Cambia el idioma desde el menú Idioma y la interfaz se actualizará en las páginas compatibles.",
    },
]


@help_bp.route("/help")
def help_center():
    language = normalize_language(session.get("language", "en"))
    query = (request.args.get("q") or "").strip().lower()

    items = []
    for item in FAQ_ITEMS:
        question = item[f"question_{language}"]
        answer = item[f"answer_{language}"]
        if query and query not in question.lower() and query not in answer.lower() and query not in item["category"].lower():
            continue
        items.append({"category": item["category"], "question": question, "answer": answer})

    categories = sorted({item["category"] for item in FAQ_ITEMS})
    return render_template("help_center.html", faq_items=items, categories=categories, active_language=language)


@help_bp.route("/language/<language>")
def set_language(language):
    language = normalize_language(language)
    session["language"] = language
    next_url = request.args.get("next") or request.referrer or url_for("dashboard.index")
    return redirect(next_url)