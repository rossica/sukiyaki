# Copyright (C) 2009,2010,2011 Anthony Rossi
# For License information regarding this software, see LICENSE
# If no LICENSE file was included, see http://www.opensource.org/licenses/mit-license.php

from django.conf.urls.defaults import *
from sukiyaki.imageboard.models import ImagePost, Board
from sukiyaki.imageboard.views import board_index, view_board, post, view_post, view_text_post, reply, text_reply, delete, delete_text, sage, sage_text

urlpatterns = patterns('sukiyaki.imageboard.views',
    # Example:
    # (r'^sukiyaki/', include('sukiyaki.foo.urls')),
    
    (r'^$', board_index),
    (r'board/(?P<board_abbr>[A-Za-z]{1,5})/$', view_board),
    (r'board/(?P<board_abbr>[A-Za-z]{1,5})/post/$', post),
    (r'post/(?P<post_id>\d+)/$', view_post),
    (r'post/(?P<reply_to>\d+)/reply/$', reply),
    (r'post/(?P<post_id>\d+)/delete/$', delete),
    (r'post/(?P<post_id>\d+)/(?P<sage>[s]?)age/$', sage),
    (r'text/(?P<text_id>\d+)/$', view_text_post),
    (r'text/(?P<reply_to>\d+)/reply/$', text_reply),
    (r'text/(?P<text_id>\d+)/delete/$', delete_text),
    (r'text/(?P<text_id>\d+)/(?P<sage>[s]?)age/$', sage_text),
)
