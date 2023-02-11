from __future__ import annotations

import datetime
from typing import Optional, Protocol, TYPE_CHECKING, _ProtocolMeta

from django.db.models import BooleanField, CharField, QuerySet
from django.db.models.base import ModelBase
from django.utils import timezone
from .utils import memoize

if TYPE_CHECKING:
    from .models import UserBadge, Vote, Show, Track, Profile, TwitterUser

    # to check to see that their VoterProtocol implementations are complete:
    Profile()
    TwitterUser()


class ModelVoterMeta(_ProtocolMeta, ModelBase):
    pass


class Voter(Protocol, metaclass=ModelVoterMeta):
    name: str | CharField
    pk: int
    is_abuser: bool | BooleanField
    is_patron: bool | BooleanField

    def _twitter_user_and_profile(
        self,
    ) -> tuple[Optional[TwitterUser], Optional[Profile]]:
        ...

    @property
    def voter_id(self) -> tuple[Optional[int], Optional[int]]:
        """
        A unique identifier that will be the same for TwitterUser and Profile
        instances that represent the same accounts.
        """

        twu, pr = self._twitter_user_and_profile()
        return (None if twu is None else twu.pk, None if pr is None else pr.pk)

    @property
    def badges(self) -> QuerySet[UserBadge]:
        ...

    def unordered_votes(self) -> QuerySet[Vote]:
        ...

    def get_toggle_abuser_url(self) -> str:
        ...

    def votes(self) -> QuerySet[Vote]:
        return self.unordered_votes().order_by('-date').prefetch_related('tracks')

    @memoize
    def votes_with_liberal_preselection(self) -> QuerySet[Vote]:
        return self.votes().prefetch_related(
            'show',
            'show__play_set',
            'show__play_set__track',  # doesn't actually appear to work :<
        )

    @memoize
    def votes_for(self, show: Show) -> QuerySet[Vote]:
        return self.votes().filter(show=show)

    @memoize
    def tracks_voted_for_for(self, show: Show) -> list[Track]:
        tracks = []
        track_pk_set = set()

        for vote in self.votes_for(show):
            for track in vote.tracks.all():
                if track.pk not in track_pk_set:
                    track_pk_set.add(track.pk)
                    tracks.append(track)

        return tracks

    @memoize
    def is_new(self) -> bool:
        from .models import Show

        return not self.votes().exclude(show=Show.current()).exists()

    @memoize
    def is_placated(self) -> bool:
        from .models import Show

        return (
            self.votes()
            .filter(
                tracks__play__show=Show.current(),
                show=Show.current(),
            )
            .exists()
        )

    @memoize
    def is_shortlisted(self) -> bool:
        from .models import Show

        return (
            self.votes()
            .filter(
                tracks__shortlist__show=Show.current(),
                show=Show.current(),
            )
            .exists()
        )

    def _batting_average(
        self,
        cutoff: Optional[datetime.datetime] = None,
        minimum_weight: float = 1,
    ) -> Optional[float]:
        from .models import Show

        def ba(
            pk, current_show_pk, cutoff: Optional[datetime.datetime]
        ) -> tuple[float, float]:
            score: float = 0
            weight: float = 0

            for vote in self.votes().filter(date__gt=cutoff).prefetch_related('tracks'):
                success = vote.success()
                if success is not None:
                    score += success * vote.weight()
                    weight += vote.weight()

            return (score, weight)

        score, weight = ba(self.pk, Show.current().pk, cutoff)

        if weight >= minimum_weight:
            return score / weight
        else:
            # there were no worthwhile votes
            return None

        return score

    @memoize
    def batting_average(self, minimum_weight: float = 1) -> Optional[float]:
        """
        Return a user's batting average for the past six months.
        """

        from .models import Show

        return self._batting_average(
            cutoff=Show.at(timezone.now() - datetime.timedelta(days=31 * 6)).end,
            minimum_weight=minimum_weight,
        )

    def _streak(self, ls=[]) -> int:
        from .models import Show

        show = Show.current().prev()
        streak = 0

        while True:
            if show is None:
                return streak
            elif not show.voting_allowed:
                show = show.prev()
            elif show.votes().filter(twitter_user=self).exists():
                streak += 1
                show = show.prev()
            else:
                break

        return streak

    @memoize
    def streak(self) -> int:
        from .models import Show

        def streak(pk, current_show):
            return self._streak()

        return streak(self.pk, Show.current())

    def all_time_batting_average(self, minimum_weight: float = 1) -> Optional[float]:
        return self._batting_average(minimum_weight=minimum_weight)
