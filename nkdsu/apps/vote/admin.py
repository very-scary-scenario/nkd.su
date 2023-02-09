from django.contrib import admin

from ..vote import models


class ShowAdmin(admin.ModelAdmin):
    list_display = ('showtime', 'end', 'voting_allowed')


class TwitterUserAdmin(admin.ModelAdmin):
    list_display = ('screen_name', 'is_abuser', 'is_patron')
    list_filter = ('is_abuser', 'is_patron')


class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge')
    list_filter = ('user', 'badge')


class VoteAdmin(admin.ModelAdmin):
    list_display = ('twitter_user', 'date')
    list_filter = ('kind', 'twitter_user')
    filter_horizontal = ('tracks',)


class TrackAdmin(admin.ModelAdmin):
    list_display = ('id3_title', 'id3_artist')


class PlayAdmin(admin.ModelAdmin):
    list_display = ('track', 'date')


class BlockAdmin(admin.ModelAdmin):
    list_display = ('track', 'reason', 'show')


class DiscardShortlistAdmin(admin.ModelAdmin):
    list_display = ('track', 'show')


class RequestAdmin(admin.ModelAdmin):
    list_display = ('created', 'successful')
    list_filter = ('successful',)


class NoteAdmin(admin.ModelAdmin):
    list_display = ('track', 'show', 'public', 'content')


admin.site.register(models.Show, ShowAdmin)
admin.site.register(models.TwitterUser, TwitterUserAdmin)
admin.site.register(models.UserBadge, UserBadgeAdmin)
admin.site.register(models.Track, TrackAdmin)
admin.site.register(models.Vote, VoteAdmin)
admin.site.register(models.Play, PlayAdmin)
admin.site.register(models.Block, BlockAdmin)
admin.site.register(models.Shortlist, DiscardShortlistAdmin)
admin.site.register(models.Discard, DiscardShortlistAdmin)
admin.site.register(models.Request, RequestAdmin)
admin.site.register(models.Note, NoteAdmin)
