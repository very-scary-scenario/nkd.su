from .models import Show


def nkdsu_context_processor(request):
    """
    Add this_week and path to every context.
    """

    return {
        'this_week': Show.current(),
    }
