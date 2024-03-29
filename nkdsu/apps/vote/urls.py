from django.urls import include, path, re_path as url

from nkdsu.apps.vote import views
from nkdsu.apps.vote.views import admin, api, elf, js, profiles


app_name = 'vote'

admin_patterns = [
    url(r'^upload/$', admin.LibraryUploadView.as_view(), name='upload_library'),
    url(
        r'^upload/confirm/$',
        admin.LibraryUploadConfirmView.as_view(),
        name='confirm_upload',
    ),
    url(
        r'^upload-myriad/$',
        admin.MyriadExportUploadView.as_view(),
        name='upload_myriad_export',
    ),
    url(r'^play/(?P<pk>.+)/$', admin.Play.as_view(), name='play'),
    url(
        r'^post-about-play/(?P<pk>.+)/$',
        admin.PostAboutPlay.as_view(),
        name='post_about_play',
    ),
    url(
        r'^add-manual-vote/(?P<pk>.+)/$',
        admin.ManualVote.as_view(),
        name='manual_vote',
    ),
    url(
        r'^block/(?P<pk>[^/]+)/reason$',
        admin.MakeBlockWithReason.as_view(),
        name='block_with_reason',
    ),
    url(r'^block/(?P<pk>[^/]+)/$', admin.MakeBlock.as_view(), name='block'),
    url(r'^unblock/(?P<pk>[^/]+)/$', admin.Unblock.as_view(), name='unblock'),
    url(r'^hidden/$', admin.HiddenTracks.as_view(), name='hidden'),
    url(r'^archived/$', admin.ArchivedTracks.as_view(), name='archived'),
    url(r'^no-media-id/$', admin.TracksWithNoMediaId.as_view(), name='no_media_id'),
    url(r'^hide/(?P<pk>.+)/$', admin.Hide.as_view(), name='hide'),
    url(r'^unhide/(?P<pk>.+)/$', admin.Unhide.as_view(), name='unhide'),
    url(r'^archive/(?P<pk>.+)/$', admin.Archive.as_view(), name='archive'),
    url(r'^unarchive/(?P<pk>.+)/$', admin.Unarchive.as_view(), name='unarchive'),
    url(r'^lm/(?P<pk>.+)/$', admin.LockMetadata.as_view(), name='lock_metadata'),
    url(r'^ulm/(?P<pk>.+)/$', admin.UnlockMetadata.as_view(), name='unlock_metadata'),
    url(r'^hide-selection/$', admin.HideSelection.as_view(), name='hide_selection'),
    url(
        r'^unhide-selection/$', admin.UnhideSelection.as_view(), name='unhide_selection'
    ),
    url(
        r'^archive-selection/$',
        admin.ArchiveSelection.as_view(),
        name='archive_selection',
    ),
    url(
        r'^unarchive-selection/$',
        admin.UnarchiveSelection.as_view(),
        name='unarchive_selection',
    ),
    url(r'^inudesu/$', admin.InuDesuTracks.as_view(), name='inudesu'),
    url(r'^artless/$', admin.ArtlessTracks.as_view(), name='artless'),
    url(r'^shortlist/(?P<pk>.+)/$', admin.MakeShortlist.as_view(), name='shortlist'),
    url(
        r'^shortlist-order/$',
        admin.OrderShortlist.as_view(),
        name='shortlist_order',
    ),
    url(r'^discard/(?P<pk>.+)/$', admin.MakeDiscard.as_view(), name='discard'),
    url(
        r'^reset/(?P<pk>.+)/$',
        admin.ResetShortlistAndDiscard.as_view(),
        name='reset',
    ),
    url(
        r'^shortlist-selection/$',
        admin.ShortlistSelection.as_view(),
        name='shortlist_selection',
    ),
    url(
        r'^discard-selection/$',
        admin.DiscardSelection.as_view(),
        name='discard_selection',
    ),
    url(
        r'^reset-shortlist-discard-selection/$',
        admin.ResetShortlistAndDiscardSelection.as_view(),
        name='reset_shortlist_discard_selection',
    ),
    url(
        r'^tw-abuse/(?P<user_id>.+)/$',
        admin.ToggleTwitterAbuser.as_view(),
        name='toggle_twitter_abuser',
    ),
    url(
        r'^local-abuse/(?P<user_id>.+)/$',
        admin.ToggleLocalAbuser.as_view(),
        name='toggle_local_abuser',
    ),
    url(r'^make-note/(?P<pk>.+)/$', admin.MakeNote.as_view(), name='make_note'),
    url(r'^remove-note/(?P<pk>.+)/$', admin.RemoveNote.as_view(), name='remove_note'),
    url(
        r'^migrate-away-from/(?P<pk>.+)/$',
        admin.MigrateAwayFrom.as_view(),
        name='migrate_away_from',
    ),
    url(r'^throw-500/$', admin.Throw500.as_view(), name='throw_500'),
]


elf_patterns = [
    url(r'^requests/$', elf.RequestList.as_view(), name='requests'),
    url(
        r'^requests/fill/(?P<pk>[^/]+)/$',
        elf.FillRequest.as_view(),
        name='fill_request',
    ),
    url(
        r'^requests/claim/(?P<pk>[^/]+)/$',
        elf.ClaimRequest.as_view(),
        name='claim_request',
    ),
    url(
        r'^requests/shelf/(?P<pk>[^/]+)/$',
        elf.ShelfRequest.as_view(),
        name='shelf_request',
    ),
    url(r'^check-metadata/$', elf.CheckMetadata.as_view(), name='check_metadata'),
    url(
        r'^unmatched-anime/$',
        elf.UnmatchedAnimeTitles.as_view(),
        name='unmatched_anime_titles',
    ),
]


js_patterns = (
    [
        url(r'^select/$', js.Select.as_view(), name='select'),
        url(r'^deselect/$', js.Deselect.as_view(), name='deselect'),
        url(r'^selection/$', js.GetSelection.as_view(), name='get_selection'),
        url(r'^clear_selection/$', js.ClearSelection.as_view(), name='clear_selection'),
    ],
    'js',
)


api_patterns = (
    [
        url(r'^$', api.ShowAPI.as_view(), name='show'),
        url(r'^week/(?P<date>[\d-]+)/$', api.ShowAPI.as_view(), name='show'),
        url(r'^week/$', api.PrevShowAPI.as_view(), name='last_week'),
        url(
            r'^user/(?P<screen_name>[_0-9a-zA-Z]+)/$',
            api.TwitterUserAPI.as_view(),
            name='user',
        ),
        url(r'^track/(?P<pk>[0-9A-F]{16})/$', api.TrackAPI.as_view(), name='api_track'),
        url(r'^search/$', api.SearchAPI.as_view(), name='search'),
    ],
    'api',
)

profile_patterns = (
    [
        path('@<str:username>/', profiles.ProfileView.as_view(), name='profile'),
        path('profile/', profiles.UpdateProfileView.as_view(), name='edit-profile'),
    ],
    'profiles',
)


urlpatterns = [
    url(r'^vote-admin/', include((admin_patterns + elf_patterns, 'admin'))),
    url(r'^js/', include(js_patterns)),
    url(r'^api/', include(api_patterns)),
    url(r'^', include(profile_patterns)),
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^browse/$', views.Browse.as_view(), name='browse'),
    url(r'^anime/$', views.BrowseAnime.as_view(), name='browse_anime'),
    url(r'^artists/$', views.BrowseArtists.as_view(), name='browse_artists'),
    url(r'^years/$', views.BrowseYears.as_view(), name='browse_years'),
    url(r'^composers/$', views.BrowseComposers.as_view(), name='browse_composers'),
    url(r'^roles/$', views.BrowseRoles.as_view(), name='browse_roles'),
    url(r'^archive/$', views.Archive.as_view(), name='archive'),
    url(r'^archive/(?P<year>\d{4})/$', views.Archive.as_view(), name='archive'),
    url(r'^show/(?P<date>[\d-]+)/$', views.ShowDetail.as_view(), name='show'),
    url(
        r'^show/(?P<date>[\d-]+)/listen/$',
        views.ListenRedirect.as_view(),
        name='listen-to-show',
    ),
    url(r'^show/$', views.ShowDetail.as_view(), name='show'),
    url(r'^added/(?P<date>[\d-]+)/$', views.Added.as_view(), name='added'),
    url(r'^added/$', views.Added.as_view(), name='added'),
    url(r'^roulette/$', views.Roulette.as_view(), name='roulette'),
    url(
        r'^roulette/'
        r'(?P<mode>indiscriminate|hipster|almost-100|pro|staple|short|decade)/$',
        views.Roulette.as_view(),
        name='roulette',
    ),
    url(
        r'^roulette/(?P<mode>short)/(?P<minutes>\d+)/$',
        views.Roulette.as_view(),
        name='roulette',
    ),
    url(
        r'^roulette/(?P<mode>decade)/(?P<decade>\d{4})/$',
        views.Roulette.as_view(),
        name='roulette',
    ),
    url(r'^search/$', views.Search.as_view(), name='search'),
    url(
        r'^user/(?P<screen_name>[_0-9a-zA-Z]+)/$',
        views.TwitterUserDetail.as_view(),
        name='user',
    ),
    url(r'^artist/(?P<artist>.*)/$', views.Artist.as_view(), name='artist'),
    url(r'^anime/(?P<anime>.*)/$', views.Anime.as_view(), name='anime'),
    url(
        r'^anime-picture/(?P<anime>.*)/$',
        views.AnimePicture.as_view(),
        name='anime-picture',
    ),
    url(r'^composer/(?P<composer>.*)/$', views.Composer.as_view(), name='composer'),
    url(r'^year/(?P<year>\d*)/$', views.Year.as_view(), name='year'),
    url(r'^stats/$', views.Stats.as_view(), name='stats'),
    url(r'^info/$', views.Info.as_view(), name='info'),
    url(r'^info/privacy/$', views.Privacy.as_view(), name='privacy'),
    url(r'^info/tos/$', views.TermsOfService.as_view(), name='tos'),
    url(r'^info/api/$', views.APIDocs.as_view(), name='api_docs'),
    url(
        r'^request-addition/$', views.RequestAddition.as_view(), name='request_addition'
    ),
    url(r'^request/$', views.VoteView.as_view(), name='vote'),
    path('update-request/<int:pk>/', views.UpdateVoteView.as_view(), name='edit-vote'),
    url(r'^set-dark-mode/$', views.SetDarkModeView.as_view(), name='set-dark-mode'),
    # tracks
    url(r'^(?P<pk>[0-9A-F]{16})/$', views.TrackDetail.as_view(), name='track'),
    url(
        r'^(?P<slug>[^/]*)/(?P<pk>[0-9A-F]{16})/$',
        views.TrackDetail.as_view(),
        name='track',
    ),
    url(
        r'^(?P<pk>[0-9A-F]{16})/report/$',
        views.ReportBadMetadata.as_view(),
        name='report',
    ),
]
