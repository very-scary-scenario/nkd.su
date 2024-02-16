from __future__ import annotations

import datetime
import re
from abc import abstractmethod
from collections import OrderedDict
from copy import copy
from typing import Any, Iterable, Optional, Sequence, TypeVar, cast

from django.db.models import Model, QuerySet
from django.db.utils import NotSupportedError
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.base import ContextMixin
from django.views.generic.detail import SingleObjectMixin

from .models import Show, Track, TrackQuerySet, TwitterUser
from .utils import BrowsableItem, memoize


M = TypeVar("M", bound=Model)


class CurrentShowMixin(ContextMixin):
    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['show'] = Show.current()
        return context


class LetMemoizeGetObject(SingleObjectMixin[M]):
    """
    A view mixin that allows objects to be memoized if, and only if, the base
    queryset is not overridden, so we can be confident that sequential
    retrievals would have been the same.

    Helpful for views where
    :meth:`~django.views.generic.detail.SingleObjectMixin.get_object` is
    particularly expensive.
    """

    def get_object(self, queryset: Optional[QuerySet[M]] = None) -> M:
        if queryset is None:
            return self.get_memoizable_object()
        else:
            return super().get_object(queryset=queryset)

    @abstractmethod
    def get_memoizable_object(self) -> M:
        raise NotImplementedError()


class TrackListWithAnimeGrouping(ContextMixin):
    def get_track_queryset(self) -> Sequence[Track] | TrackQuerySet:
        raise NotImplementedError()

    def grouped_tracks(self) -> OrderedDict[str, list[Track]]:
        tracks = self.get_track_queryset()
        animes = sorted(
            set(
                rd.anime or "not from an anime" for t in tracks for rd in t.role_details
            )
        )
        grouped_tracks: OrderedDict[str, list[Track]] = OrderedDict()

        for anime in animes:
            anime_tracks = [t for t in tracks if t.has_anime(anime)]
            if anime_tracks:
                grouped_tracks[anime] = anime_tracks

        return grouped_tracks

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'grouped_tracks': self.grouped_tracks,
                'tracks': self.get_track_queryset(),
            }
        )

        return context


class TrackListWithAnimeGroupingListView(TrackListWithAnimeGrouping, ListView):
    def get_queryset(self) -> Sequence[Track] | TrackQuerySet:
        return self.get_track_queryset()


class ShowDetailMixin(LetMemoizeGetObject[Show]):
    """
    A view that will find a show for any date in the past, redirect to the
    showtime date if necessary, and then render a view with the correct show
    in context.
    """

    model = Show
    view_name: Optional[str] = None
    default_to_current = False
    date: Optional[datetime.datetime] = None

    @memoize
    def get_memoizable_object(self) -> Show:
        """
        Get the show relating to :attr:`.date` or, if :attr:`.date` is
        :data:`None`, the most recent complete show. If self.default_to_current
        is True, get the show in progress rather than the most recent complete
        show.

        Doesn't use :meth:`.Show.at` because I don't want views creating
        :class:`.Show` instances in the database.
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
            raise Http404()

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        date_fmt = '%Y-%m-%d'
        date_str = kwargs.get('date')

        fell_back = False

        if date_str is None:
            self.date = None
        else:
            try:
                naive_date = datetime.datetime.strptime(kwargs['date'], date_fmt)
            except ValueError:
                try:
                    naive_date = datetime.datetime.strptime(kwargs['date'], '%d-%m-%Y')
                except ValueError:
                    raise Http404()
                else:
                    fell_back = True

            self.date = timezone.make_aware(naive_date, timezone.get_current_timezone())

        self.object = self.get_object()
        assert isinstance(self.object, Show)

        if (
            not fell_back
            and self.date is not None
            and self.object.showtime.date() == self.date.date()
        ):
            return super().get(request, *args, **kwargs)  # type: ignore
        else:
            assert (
                request.resolver_match is not None
                and request.resolver_match.url_name is not None
            )
            new_kwargs = copy(kwargs)
            name = self.view_name or ':'.join(
                [request.resolver_match.namespace, request.resolver_match.url_name]
            )
            new_kwargs['date'] = self.object.showtime.date().strftime(date_fmt)
            url = reverse(name, kwargs=new_kwargs)
            return redirect(url)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        context['show'] = self.get_object()
        return context


class ThisShowDetailMixin(ShowDetailMixin):
    """
    Like ShowDetailMixin, but defaults to the show in progress when no date is
    provided.
    """

    @memoize
    def get_object(self, queryset: Optional[QuerySet[Show]] = None) -> Show:
        if queryset is not None:
            raise NotImplementedError('Show detail mixins cannot be restricted')

        if self.date is None:
            try:
                return self.model.at(timezone.now())
            except self.model.DoesNotExist:
                raise Http404()
        else:
            return super().get_object()


class ShowDetail(ShowDetailMixin, DetailView[Show]):
    model = Show
    object: Show


class ArchiveList(ListView):
    model: Optional[type[Model]] = Show
    exclude_current = True

    def year(self) -> int:
        year = int(
            self.kwargs.get('year')
            or self.get_queryset().latest('showtime').showtime.year
        )

        if year not in self.get_years():
            raise Http404("We don't have shows for that year")

        return year

    def get_years(self) -> list[int]:
        try:
            return list(
                self.get_queryset()
                .order_by('showtime__year')
                .distinct('showtime__year')
                .values_list('showtime__year', flat=True)
            )
        except NotSupportedError:
            # we're probably running on sqlite
            return sorted(
                set(
                    self.get_queryset()
                    .order_by('showtime__year')
                    .values_list('showtime__year', flat=True)
                )
            )

    def get_queryset(self) -> QuerySet[Show]:
        assert self.model is not None
        assert issubclass(self.model, Show)

        qs = cast(QuerySet[Show], super().get_queryset()).order_by('-showtime')

        if self.exclude_current:
            qs = qs.exclude(pk=self.model.current().pk)

        return qs

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        return {
            **super().get_context_data(**kwargs),
            'years': self.get_years(),
            'year': self.year(),
            'object_list': self.get_queryset().filter(showtime__year=self.year()),
        }


class TwitterUserDetailMixin(LetMemoizeGetObject[TwitterUser]):
    model = TwitterUser

    @memoize
    def get_memoizable_object(self) -> TwitterUser:
        assert hasattr(self, 'kwargs')
        user_id = self.kwargs.get('user_id')

        if user_id:
            return get_object_or_404(
                self.model,
                user_id=self.kwargs['user_id'],
            )

        users = self.model.objects.filter(
            screen_name__iexact=self.kwargs['screen_name']
        )

        if not users.exists():
            raise Http404()
        elif users.count() == 1:
            user = users[0]
        else:
            user = users.order_by('-updated')[0]

        if user.vote_set.exists():
            return user
        else:
            raise Http404()


class BreadcrumbMixin:
    breadcrumbs: list[tuple[Optional[str], str]] = []

    @abstractmethod
    def get_breadcrumbs(self) -> list[tuple[Optional[str], str]]:
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
    searchable = True

    @abstractmethod
    def get_categories(self) -> Iterable[BrowsableItem]:
        raise NotImplementedError()

    def filter_categories(
        self, items: Iterable[BrowsableItem]
    ) -> Iterable[BrowsableItem]:
        query = self.request.GET.get('q', '')
        if not query:
            yield from items
        for item in items:
            if not re.findall(query, item.name, re.IGNORECASE):
                item.visible = False
            yield item

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        return {
            **super().get_context_data(**kwargs),
            'category_name': self.category_name,
            'contents_required': self.contents_required,
            'searchable': self.searchable,
            'query': self.request.GET.get('q', ''),
            self.context_category_name: sorted(
                self.filter_categories(self.get_categories()),
                key=lambda i: (i.group(), i.name.lower()),
            ),
        }
