# -*- coding: utf-8 -*-
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.views.generic import View
from django.views.generic.detail import SingleObjectMixin

from ..models import Track
from ..mixins import ShowDetailMixin
from ..views import Search


class APIView(View):
    def get_api_stuff(self):
        return self.get_object().api_dict(verbose=True)

    def get(self, request, *args, **kwargs):
        self.request = request
        self.kwargs = kwargs

        return HttpResponse(
            json.dumps(self.get_api_stuff(),
                       cls=DjangoJSONEncoder,
                       indent=2),
            content_type='application/json',
        )


class ShowAPI(ShowDetailMixin, APIView):
    pass


class PrevShowAPI(ShowAPI):
    view_name = 'vote:api:show'

    def get_object(self):
        return super(PrevShowAPI, self).get_object().prev()


class TrackAPI(SingleObjectMixin, APIView):
    model = Track


class SearchAPI(APIView, Search):
    def get_api_stuff(self):
        return [t.api_dict() for t in self.get_queryset()]
