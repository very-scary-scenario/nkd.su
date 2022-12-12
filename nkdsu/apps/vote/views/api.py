# -*- coding: utf-8 -*-
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest, HttpResponse
from django.views.generic import View
from django.views.generic.detail import SingleObjectMixin

from ..mixins import ShowDetailMixin, ThisShowDetailMixin, TwitterUserDetailMixin
from ..models import Track
from ..views import Search


JsonEncodable = (
    None | bool | int | float | str | dict[str, 'JsonEncodable'] | list['JsonEncodable']
)
JsonDict = dict[str, JsonEncodable]


class APIView(View):
    def get_api_stuff(self):
        return self.get_object().api_dict(verbose=True)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        resp = HttpResponse(
            json.dumps(self.get_api_stuff(), cls=DjangoJSONEncoder, indent=2),
            content_type='application/json',
        )
        resp['Access-Control-Allow-Origin'] = '*'
        return resp


class ShowAPI(ThisShowDetailMixin, APIView):
    pass


class PrevShowAPI(ShowDetailMixin, APIView):
    view_name = 'vote:api:show'


class TrackAPI(SingleObjectMixin, APIView):
    model = Track


class SearchAPI(APIView, Search):
    def get_api_stuff(self, *a, **k) -> list[JsonDict]:
        return [t.api_dict() for t in self.get_queryset()]


class TwitterUserAPI(TwitterUserDetailMixin, APIView):
    pass
