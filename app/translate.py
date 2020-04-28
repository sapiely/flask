from flask_babel import _
from googletrans import Translator


def translate(text, source, dest_language):
    try:
        translator = Translator(service_urls=['translate.google.com'])
        translation1 = translator.translate(text, dest=dest_language)
    except Exception:
        return _('Error: the translation service failed.')
    else:
        return translation1.text
