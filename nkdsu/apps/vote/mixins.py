import codecs
from copy import copy
import datetime
from os import path

from markdown import markdown

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import DetailView, TemplateView

from .models import Show, TwitterUser
from .utils import memoize


class CurrentShowMixin(object):
    def get_context_data(self):
        context = super(CurrentShowMixin, self).get_context_data()
        context['show'] = Show.current()
        return context


class ShowDetailMixin(object):
    """
    A view that will find a show for any date in the past, redirect to the
    showtime date if necessary, and then render a view with the correct show
    in context.
    """

    model = Show
    view_name = None

    @memoize
    def get_object(self):
        """
        Get the show relating to self.date or, if self.date is None, the most
        recent complete show.

        Doesn't use Show.at() because I don't want views creating Shows in the
        database.
        """

        if self.date is None:
            qs = self.model.objects.filter(end__lt=timezone.now())
            qs = qs.order_by('-end')
        else:
            qs = self.model.objects.filter(showtime__gt=self.date)
            qs = qs.order_by('showtime')

        try:
            return qs[0]
        except IndexError:
            raise Http404

    def get(self, request, *args, **kwargs):
        date_fmt = '%Y-%m-%d'
        date_str = kwargs.get('date')

        fell_back = False

        if date_str is None:
            self.date = None
        else:
            try:
                naive_date = datetime.datetime.strptime(kwargs['date'],
                                                        date_fmt)
            except ValueError:
                try:
                    naive_date = datetime.datetime.strptime(kwargs['date'],
                                                            '%d-%m-%Y')
                except ValueError:
                    raise Http404
                else:
                    fell_back = True

            self.date = timezone.make_aware(naive_date,
                                            timezone.get_current_timezone())

        self.object = self.get_object()

        if (
            not fell_back and
            self.date is not None and
            self.object.showtime.date() == self.date.date()
        ):
            return super(ShowDetailMixin, self).get(request, *args, **kwargs)
        else:
            new_kwargs = copy(kwargs)
            name = (self.view_name or
                    ':'.join([request.resolver_match.namespace,
                              request.resolver_match.url_name]))
            new_kwargs['date'] = self.object.showtime.date().strftime(date_fmt)
            url = reverse(name, kwargs=new_kwargs)
            return redirect(url)

    def get_context_data(self, *args, **kwargs):
        context = super(ShowDetailMixin, self).get_context_data(*args,
                                                                **kwargs)

        context['show'] = self.get_object()
        return context


class ThisShowDetailMixin(ShowDetailMixin):
    """
    Like ShowDetailMixin, but defaults to the show in progress when no date is
    provided.
    """

    @memoize
    def get_object(self):
        if self.date is None:
            qs = self.model.objects.order_by('-end')
            try:
                return qs[0]
            except IndexError:
                raise Http404
        else:
            return super(ThisShowDetailMixin, self).get_object()


class ShowDetail(ShowDetailMixin, DetailView):
    pass


class MarkdownView(TemplateView):
    template_name = 'markdown.html'

    def get_context_data(self):
        context = super(MarkdownView, self).get_context_data()

        words = markdown(codecs.open(
            path.join(settings.PROJECT_ROOT, self.filename),
            encoding='utf-8'
        ).read())

        context.update({
            'title': self.title,
            'words': words,
        })

        return context


class TwitterUserDetailMixin(object):
    model = TwitterUser

    @memoize
    def get_object(self):
        users = self.model.objects.filter(
            screen_name__iexact=self.kwargs['screen_name'])

        if not users.exists():
            raise Http404
        elif users.count() == 1:
            user = users[0]
        else:
            user = users.order_by('-updated')[0]

        if user.vote_set.exists():
            return user
        else:
            raise Http404
