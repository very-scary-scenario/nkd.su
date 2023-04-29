from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as StockUserAdmin
from django.contrib.auth.models import User as UserType

from ..vote import models
from ..vote.elfs import is_elf


User = get_user_model()


class UserAdmin(StockUserAdmin):
    list_display = ('username', 'display_name', 'email', 'is_elf', 'is_staff', 'is_superuser', 'has_usable_password')

    @admin.display()
    def display_name(self, obj: UserType):
        return obj.profile.display_name

    @admin.display(boolean=True)
    def is_elf(self, obj: UserType):
        return is_elf(obj)

    @admin.display(boolean=True)
    def has_usable_password(self, obj: UserType):
        return obj.has_usable_password()


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


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
    list_display = ('created', 'filled_by', 'claimant', 'submitted_by')
    list_filter = ('filled_by', 'claimant', 'submitted_by')


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
