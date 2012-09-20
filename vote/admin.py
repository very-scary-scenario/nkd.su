from vote.models import Track, Vote
from django.contrib import admin

class VoteAdmin(admin.ModelAdmin):
    list_display=('screen_name', 'track')

class TrackAdmin(admin.ModelAdmin):
    list_display=('id3_title', 'id3_artist')

admin.site.register(Track, TrackAdmin)
admin.site.register(Vote, VoteAdmin)
