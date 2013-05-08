from vote import models
from django.contrib import admin


class VoteAdmin(admin.ModelAdmin):
    list_display = ('screen_name', 'date', 'name')


class TrackAdmin(admin.ModelAdmin):
    list_display = ('id3_title', 'id3_artist')


class ManualVoteAdmin(admin.ModelAdmin):
    list_display = ('name', 'message', 'track', 'date')


class PlayAdmin(admin.ModelAdmin):
    list_display = ('track', 'datetime')


class BlockAdmin(admin.ModelAdmin):
    list_display = ('track', 'reason', 'date')


class DiscardShortlistAdmin(admin.ModelAdmin):
    list_display = ('track', 'date')


class ScheduleOverrideAdmin(admin.ModelAdmin):
    list_display = ('overridden_showdate', 'start', 'finish')


class RobotApocalypseAdmin(admin.ModelAdmin):
    list_display = ('overridden_showdate',)


class RequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'successful')


for model, modeladmin in [
        (models.Track, TrackAdmin),
        (models.Vote, VoteAdmin),
        (models.ManualVote, ManualVoteAdmin),
        (models.Play, PlayAdmin),
        (models.Block, BlockAdmin),
        (models.Shortlist, DiscardShortlistAdmin),
        (models.Discard, DiscardShortlistAdmin),
        (models.ScheduleOverride, ScheduleOverrideAdmin),
        (models.RobotApocalypse, RobotApocalypseAdmin),
        (models.Request, RequestAdmin)]:
    admin.site.register(model, modeladmin)
