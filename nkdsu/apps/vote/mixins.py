from .models import Show


class CurrentShowMixin(object):
    def get_context_data(self):
        context = super(CurrentShowMixin, self).get_context_data()
        context['show'] = Show.current()
        context['show'].tracks_sorted_by_votes()  # XXX
        return context
