"""
Horrible hacks. Please ignore.
"""


def patch() -> None:
    _replace_password_validators_help_text_html()


def _replace_password_validators_help_text_html() -> None:
    """
    Don't use a ``<ul>`` to surface multiple password requirements against
    password fields. It's invalid HTML when used within an
    :meth:`~django.forms.Form.as_p`-rendered form, and browsers interpret the
    DOM structure wrong as a result. As far as Firefox is concerned, if we let
    Django do what it does by default, these help texts aren't within a
    ``.helptext`` element at all.

    I hope this is made unnecessary if we adopt the ``<div>``-based form
    renderer that becomes the default in Django 5.0.
    """

    from django.utils.functional import lazy
    from django.contrib.auth import password_validation

    # make sure we're replacing something that exists:
    assert password_validation.password_validators_help_text_html

    def replacement(password_validators=None) -> str:
        """
        Return an HTML string with all help texts of all configured validators,
        separated by `<br/>`.
        """

        from django.utils.html import format_html, format_html_join
        from django.utils.safestring import mark_safe

        help_texts = password_validation.password_validators_help_texts(
            password_validators
        )
        help_items = format_html_join(
            mark_safe('<br/>'), '{}', ((help_text,) for help_text in help_texts)
        )
        return format_html('{}', help_items)

    password_validation.password_validators_help_text_html = lazy(replacement, str)
