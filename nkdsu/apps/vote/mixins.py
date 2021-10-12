from __future__ import annotations

import codecs
import datetime
from abc import abstractmethod
from collections import OrderedDict
from copy import copy
from os import path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

from django.conf import settings
from django.db.models import Model, QuerySet
from django.db.utils import NotSupportedError
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.base import ContextMixin
from markdown import markdown

from .models import Show, Track, TwitterUser
from .utils import BrowsableItem, memoize


class CurrentShowMixin(ContextMixin):
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['show'] = Show.current()
        return context


class LetMemoizeGetObject:
    def get_object(self, queryset: Optional[QuerySet] = None) -> Model:
        if queryset is None:
            return self._get_object()
        else:
            return super().get_object(queryset=queryset)  # type: ignore

    @abstractmethod
    def _get_object(self) -> Model:
        raise NotImplementedError()


class TrackListWithAnimeGrouping(ContextMixin):
    def get_track_queryset(self) -> QuerySet[Track]:
        raise NotImplementedError()

    def get_queryset(self) -> QuerySet:
        return self.get_track_queryset()

    def grouped_tracks(self) -> OrderedDict[str, List[Track]]:
        tracks = self.get_track_queryset()
        animes = sorted(set(
            rd.anime or "not from an anime"
            for t in tracks for rd in t.role_details
        ))
        grouped_tracks: OrderedDict[str, List[Track]] = OrderedDict()

        for anime in animes:
            grouped_tracks[anime] = [t for t in tracks if t.has_anime(anime)]

        return grouped_tracks

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update({
            'grouped_tracks': self.grouped_tracks,
            'tracks': self.get_track_queryset(),
        })

        return context


class ShowDetailMixin(LetMemoizeGetObject):
    """
    A view that will find a show for any date in the past, redirect to the
    showtime date if necessary, and then render a view with the correct show
    in context.
    """

    model = Show
    view_name: Optional[str] = None
    default_to_current = False

    @memoize
    def _get_object(self) -> Show:
        """
        Get the show relating to self.date or, if self.date is None, the most
        recent complete show. If self.default_to_current is True, get the show
        in progress rather than the most recent complete show.

        Doesn't use Show.at() because I don't want views creating Shows in the
        database.
        """

        assert self.model is not None

        if self.date is None:
            qs = self.model.objects.all()

            if not self.default_to_current:
                qs = qs.filter(end__lt=timezone.now())

            qs = qs.order_by('-end')
        else:
            qs = self.model.objects.filter(showtime__gt=self.date)
            qs = qs.order_by('showtime')

        try:
            return qs[0]
        except IndexError:
            raise Http404

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
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
        assert isinstance(self.object, Show)

        if (
            not fell_back and
            self.date is not None and
            self.object.showtime.date() == self.date.date()
        ):
            return super().get(request, *args, **kwargs)  # type: ignore
        else:
            assert request.resolver_match.url_name is not None
            new_kwargs = copy(kwargs)
            name = (self.view_name or
                    ':'.join([request.resolver_match.namespace,
                              request.resolver_match.url_name]))
            new_kwargs['date'] = self.object.showtime.date().strftime(date_fmt)
            url = reverse(name, kwargs=new_kwargs)
            return redirect(url)

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)  # type: ignore

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
            try:
                return self.model.at(timezone.now())
            except self.model.DoesNotExist:
                raise Http404
        else:
            return super().get_object()


class ShowDetail(ShowDetailMixin, DetailView):
    model = Show


class ArchiveList(ListView):
    model: Optional[Type[Model]] = Show
    exclude_current = True

    def year(self) -> int:
        year = int(
            self.kwargs.get('year') or
            self.get_queryset().latest('showtime').showtime.year
        )

        if year not in self.get_years():
            raise Http404("We don't have shows for that year")

        return year

    def get_years(self) -> List[int]:
        try:
            return list(
                self.get_queryset().order_by('showtime__year').distinct(
                    'showtime__year').values_list('showtime__year', flat=True)
            )
        except NotSupportedError:
            # we're probably running on sqlite
            return sorted(set(self.get_queryset().order_by('showtime__year')
                              .values_list('showtime__year', flat=True)))

    def get_queryset(self) -> QuerySet[Show]:
        assert self.model is not None
        assert issubclass(self.model, Show)

        qs = super().get_queryset().order_by('-showtime')

        if self.exclude_current:
            qs = qs.exclude(pk=self.model.current().pk)

        return qs

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        return {
            **super().get_context_data(**kwargs),
            'years': self.get_years(),
            'year': self.year(),
            'object_list': self.get_queryset().filter(
                showtime__year=self.year()
            ),
        }


class MarkdownView(TemplateView):
    template_name = 'markdown.html'
    filename: str
    title: str

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)

        words = markdown(codecs.open(
            path.join(settings.PROJECT_ROOT, self.filename),
            encoding='utf-8'
        ).read())

        context.update({
            'title': self.title,
            'words': words,
        })

        return context


class TwitterUserDetailMixin(LetMemoizeGetObject):
    model = TwitterUser

    @memoize
    def _get_object(self):
        user_id = self.kwargs.get('user_id')

        if user_id:
            return get_object_or_404(
                self.model, user_id=self.kwargs['user_id'],
            )

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


class BreadcrumbMixin:
    breadcrumbs: List[Tuple[Optional[str], str]] = []

    @abstractmethod
    def get_breadcrumbs(self) -> List[Tuple[Optional[str], str]]:
        return self.breadcrumbs

    def get_context_data(self, **k):
        return {
            **super().get_context_data(**k),
            'breadcrumbs': self.get_breadcrumbs(),
        }


class BrowseCategory(BreadcrumbMixin, TemplateView):
    template_name = "browse_category.html"
    context_category_name = "items"
    category_name: Optional[str] = None
    breadcrumbs = [(reverse_lazy("vote:browse"), "browse")]
    contents_required = True

    @abstractmethod
    def get_categories(self) -> Iterable[BrowsableItem]:
        raise NotImplementedError()

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        return {
            **super().get_context_data(**kwargs),
            'category_name': self.category_name,
            'contents_required': self.contents_required,
            self.context_category_name: sorted(
                self.get_categories(), key=lambda i: (i.group(), i.name.lower())
            ),
        }
