from .models import Show


def nkdsu_context_processor(request):
    """
    Add common stuff to context.
    """

    return {
        'current_show': Show.current(),
        'path': request.path,
    }
