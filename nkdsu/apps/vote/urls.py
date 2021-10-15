from django.urls import include, re_path as url

from nkdsu.apps.vote import views
from nkdsu.apps.vote.views import admin, api, js


app_name = 'vote'

admin_patterns = ([
    url(r'^upload/$',
        admin.LibraryUploadView.as_view(), name='upload_library'),
    url(r'^upload/confirm/$',
        admin.LibraryUploadConfirmView.as_view(), name='confirm_upload'),

    url(r'^requests/$',
        admin.RequestList.as_view(), name='requests'),
    url(r'^requests/fill/(?P<pk>[^/]+)/$',
        admin.FillRequest.as_view(), name='fill_request'),
    url(r'^requests/claim/(?P<pk>[^/]+)/$',
        admin.ClaimRequest.as_view(), name='claim_request'),

    url(r'^play/(?P<pk>.+)/$', admin.Play.as_view(), name='play'),

    url(r'^add-manual-vote/(?P<pk>.+)/$',
        admin.ManualVote.as_view(), name='manual_vote'),

    url(r'^block/(?P<pk>[^/]+)/reason$',
        admin.MakeBlockWithReason.as_view(), name='block_with_reason'),
    url(r'^block/(?P<pk>[^/]+)/$',
        admin.MakeBlock.as_view(), name='block'),
    url(r'^unblock/(?P<pk>[^/]+)/$',
        admin.Unblock.as_view(), name='unblock'),

    url(r'^hidden/$', admin.HiddenTracks.as_view(), name='hidden'),
    url(r'^hide/(?P<pk>.+)/$', admin.Hide.as_view(), name='hide'),
    url(r'^unhide/(?P<pk>.+)/$', admin.Unhide.as_view(), name='unhide'),

    url(r'^lm/(?P<pk>.+)/$', admin.LockMetadata.as_view(),
        name='lock_metadata'),
    url(r'^ulm/(?P<pk>.+)/$', admin.UnlockMetadata.as_view(),
        name='unlock_metadata'),

    url(r'^hide-selection/$', admin.HideSelection.as_view(),
        name='hide_selection'),
    url(r'^unhide-selection/$', admin.UnhideSelection.as_view(),
        name='unhide_selection'),

    url(r'^inudesu/$', admin.InuDesuTracks.as_view(), name='inudesu'),
    url(r'^artless/$', admin.ArtlessTracks.as_view(), name='artless'),

    url(r'^trivia/$', admin.BadTrivia.as_view(), name='bad_trivia'),

    url(r'^shortlist/(?P<pk>.+)/$',
        admin.MakeShortlist.as_view(), name='shortlist'),
    url(r'^shortlist-order/$',
        admin.OrderShortlist.as_view(), name='shortlist_order'),
    url(r'^discard/(?P<pk>.+)/$', admin.MakeDiscard.as_view(), name='discard'),
    url(r'^reset/(?P<pk>.+)/$',
        admin.ResetShortlistAndDiscard.as_view(), name='reset'),

    url(r'^shortlist-selection/$',
        admin.ShortlistSelection.as_view(), name='shortlist_selection'),
    url(r'^discard-selection/$',
        admin.DiscardSelection.as_view(), name='discard_selection'),
    url(r'^reset-shortlist-discard-selection/$',
        admin.ResetShortlistAndDiscardSelection.as_view(),
        name='reset_shortlist_discard_selection'),

    url(r'^abuse/(?P<user_id>.+)/$',
        admin.ToggleAbuser.as_view(), name='toggle_abuser'),

    url(r'^make-note/(?P<pk>.+)/$',
        admin.MakeNote.as_view(), name='make_note'),
    url(r'^remove-note/(?P<pk>.+)/$',
        admin.RemoveNote.as_view(), name='remove_note'),
], 'admin')


js_patterns = ([
    url(r'^select/$', js.Select.as_view(), name='select'),
    url(r'^deselect/$', js.Deselect.as_view(), name='deselect'),
    url(r'^selection/$', js.GetSelection.as_view(), name='get_selection'),
    url(r'^clear_selection/$',
        js.ClearSelection.as_view(), name='clear_selection'),
], 'js')


api_patterns = ([
    url(r'^$', api.ShowAPI.as_view(), name='show'),
    url(r'^week/(?P<date>[\d-]+)/$', api.ShowAPI.as_view(), name='show'),
    url(r'^week/$', api.PrevShowAPI.as_view(), name='last_week'),
    url(r'^user/(?P<screen_name>[_0-9a-zA-Z]+)/$',
        api.TwitterUserAPI.as_view(), name='user'),
    url(r'^track/(?P<pk>[0-9A-F]{16})/$',
        api.TrackAPI.as_view(), name='api_track'),
    url(r'^search/$', api.SearchAPI.as_view(), name='search'),
], 'api')


urlpatterns = [
    url(r'^vote-admin/', include(admin_patterns)),
    url(r'^js/', include(js_patterns)),
    url(r'^api/', include(api_patterns)),

    url(r'^$', views.IndexView.as_view(), name='index'),

    url(r'^browse/$', views.Browse.as_view(), name='browse'),

    url(r'^anime/$', views.BrowseAnime.as_view(), name='browse_anime'),
    url(r'^artists/$', views.BrowseArtists.as_view(), name='browse_artists'),
    url(r'^years/$', views.BrowseYears.as_view(), name='browse_years'),
    url(r'^composers/$', views.BrowseComposers.as_view(), name='browse_composers'),
    url(r'^roles/$', views.BrowseRoles.as_view(), name='browse_roles'),

    url(r'^archive/$', views.Archive.as_view(), name='archive'),
    url(r'^archive/(?P<year>\d{4})/$', views.Archive.as_view(),
        name='archive'),

    url(r'^show/(?P<date>[\d-]+)/$', views.ShowDetail.as_view(), name='show'),
    url(r'^show/(?P<date>[\d-]+)/listen/$', views.ListenRedirect.as_view(),
        name='listen-to-show'),
    url(r'^show/$', views.ShowDetail.as_view(), name='show'),

    url(r'^added/(?P<date>[\d-]+)/$', views.Added.as_view(), name='added'),
    url(r'^added/$', views.Added.as_view(), name='added'),

    url(r'^roulette/$', views.Roulette.as_view(), name='roulette'),
    url(r'^roulette/'
        r'(?P<mode>indiscriminate|hipster|almost-100|pro|staple|short|decade)/$',
        views.Roulette.as_view(), name='roulette'),
    url(r'^roulette/(?P<mode>short)/(?P<minutes>\d+)/$',
        views.Roulette.as_view(), name='roulette'),
    url(r'^roulette/(?P<mode>decade)/(?P<decade>\d{4})/$',
        views.Roulette.as_view(), name='roulette'),

    url(r'^search/$', views.Search.as_view(), name='search'),

    url(r'^user/(?P<screen_name>[_0-9a-zA-Z]+)/$',
        views.TwitterUserDetail.as_view(), name='user'),
    url(r'^twitter-avatar/(?P<user_id>\d+)/$', views.TwitterAvatarView.as_view(),
        name='twitter-avatar'),

    url(r'^artist/(?P<artist>.*)/$', views.Artist.as_view(), name='artist'),
    url(r'^anime/(?P<anime>.*)/$', views.Anime.as_view(), name='anime'),
    url(r'^composer/(?P<composer>.*)/$', views.Composer.as_view(), name='composer'),
    url(r'^year/(?P<year>\d*)/$', views.Year.as_view(), name='year'),

    url(r'^stats/$', views.Stats.as_view(), name='stats'),

    url(r'^info/$', views.Info.as_view(), name='info'),
    url(r'^info/privacy/$', views.Privacy.as_view(), name='privacy'),
    url(r'^info/api/$', views.APIDocs.as_view(), name='api_docs'),

    url(r'^request/$',
        views.RequestAddition.as_view(), name='request_addition'),

    url(r'^set-dark-mode/$', views.SetDarkModeView.as_view(),
        name='set-dark-mode'),

    # tracks
    url(r'^(?P<pk>[0-9A-F]{16})/$', views.TrackDetail.as_view(), name='track'),
    url(r'^(?P<slug>[^/]*)/(?P<pk>[0-9A-F]{16})/$',
        views.TrackDetail.as_view(), name='track'),
    url(r'^(?P<pk>[0-9A-F]{16})/report/$',
        views.ReportBadMetadata.as_view(), name='report'),
]
