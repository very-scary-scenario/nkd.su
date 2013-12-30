import datetime

from django.http import Http404
from django.views.generic import DetailView

from .models import Show
from .utils import memoize


class CurrentShowMixin(object):
    def get_context_data(self):
        context = super(CurrentShowMixin, self).get_context_data()
        context['show'] = Show.current()
        context['show'].tracks_sorted_by_votes()  # XXX
        return context


class ShowDetail(DetailView):
    """
    A view that will find a show for any date in the past, redirect to the
    showtime date if necessary, and then render a view with the correct show
    in context.
    """

    model = Show

    @memoize
    def get_object(self):
        qs = self.model.objects.filter(end__gt=self.date)

        if not qs.exists():
            raise Http404

        return qs.order_by('end')[0]

    def get(self, request, *args, **kwargs):
        self.date = datetime.datetime.strptime(kwargs['date'], '%Y-%m-%d')
        self.object = self.get_object()

        if self.object.end.date() == self.date.date():
            return super(ShowDetail, self).get(request, *args, **kwargs)
        else:
            return NotImplementedError('We need a redirect')
