"""Lightweight free multilingual support for Assistly."""

TRANSLATIONS = {
    "en": {
        "nav.help": "Help Center",
        "nav.language": "Language",
        "nav.accessibility": "Accessibility",
        "nav.home": "Home",
        "nav.platform": "Platform",
        "nav.capabilities": "Capabilities",
        "hero.title": "Community Support Made Simple",
        "hero.subtitle": "Connect residents, volunteers, and leaders in one trusted platform.",
        "hero.primary": "Join Your Community",
        "hero.secondary": "Sign In",
        "help.title": "Help Center",
        "help.subtitle": "Answers, guidance, and accessibility tips for Assistly.",
        "help.search": "Search help articles",
        "accessibility.toggle": "Accessibility",
        "accessibility.default": "Default",
        "accessibility.large": "Large Text",
        "accessibility.contrast": "High Contrast",
    },
    "es": {
        "nav.help": "Centro de ayuda",
        "nav.language": "Idioma",
        "nav.accessibility": "Accesibilidad",
        "nav.home": "Inicio",
        "nav.platform": "Plataforma",
        "nav.capabilities": "Funciones",
        "hero.title": "Apoyo comunitario, simplificado",
        "hero.subtitle": "Conecta residentes, voluntarios y líderes en una sola plataforma confiable.",
        "hero.primary": "Unirse a su comunidad",
        "hero.secondary": "Iniciar sesión",
        "help.title": "Centro de ayuda",
        "help.subtitle": "Respuestas, guía y consejos de accesibilidad para Assistly.",
        "help.search": "Buscar artículos de ayuda",
        "accessibility.toggle": "Accesibilidad",
        "accessibility.default": "Predeterminado",
        "accessibility.large": "Texto grande",
        "accessibility.contrast": "Alto contraste",
    },
}


def normalize_language(language: str | None) -> str:
    language = (language or "en").strip().lower()
    return language if language in TRANSLATIONS else "en"


def translate(key: str, language: str = "en") -> str:
    language = normalize_language(language)
    return TRANSLATIONS.get(language, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))