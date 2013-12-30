from .models import Show


def nkdsu_context_processor(request):
    """
    Add common stuff to context.
    """

    return {
        'this_week': Show.current(),
        'path': request.path,
    }
