from django.core.exceptions import ValidationError
from django.utils.text import slugify


def sluggable(value: str) -> None:
    if not slugify(value):
        raise ValidationError(
            'you must provide a name with letters or numbers in it, sorry'
        )
