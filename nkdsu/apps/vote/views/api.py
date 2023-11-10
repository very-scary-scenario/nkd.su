import json
from abc import ABC, abstractmethod
from typing import TypeVar

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpRequest, HttpResponse
from django.views.generic import View
from django.views.generic.detail import SingleObjectMixin

from ..api_utils import JsonDict, JsonEncodable, JsonList, Serializable
from ..mixins import ShowDetailMixin, ThisShowDetailMixin, TwitterUserDetailMixin
from ..models import Track
from ..views import Search


S = TypeVar("S", bound=Serializable)


class APIView(View, ABC):
    @abstractmethod
    def get_api_stuff(self) -> JsonEncodable:
        raise NotImplementedError()

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        resp = HttpResponse(
            json.dumps(self.get_api_stuff(), cls=DjangoJSONEncoder, indent=2),
            content_type='application/json',
        )
        resp['Access-Control-Allow-Origin'] = '*'
        return resp


class DetailAPIView(APIView, SingleObjectMixin[S]):
    def get_api_stuff(self) -> JsonDict:
        return self.get_object().api_dict(verbose=True)


class ShowAPI(ThisShowDetailMixin, DetailAPIView):
    pass


class PrevShowAPI(ShowDetailMixin, DetailAPIView):
    view_name = 'vote:api:show'


class TrackAPI(SingleObjectMixin, APIView):
    model = Track


class SearchAPI(APIView, Search):
    def get_api_stuff(self, *a, **k) -> JsonList:
        return [t.api_dict() for t in self.get_queryset()]


class TwitterUserAPI(TwitterUserDetailMixin, APIView):
    pass
