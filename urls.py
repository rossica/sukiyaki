# Copyright (C) 2009,2010,2011 Anthony Rossi
# For License information regarding this software, see LICENSE
# If no LICENSE file was included, see http://www.opensource.org/licenses/mit-license.php

from django.conf.urls.defaults import *
from settings import MEDIA_ROOT, DEBUG

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^sukiyaki/', include('sukiyaki.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    (r'^admin/', include(admin.site.urls)),
    #(r'^admin/(.*)', admin.site.root), # old, deprecated
    
    (r'^', include('sukiyaki.imageboard.urls')),
    #(r'^comment/', include('sukiyaki.imageboard.urls')),
)
# Only enabled during development
if DEBUG:
    urlpatterns += patterns('',
        # Disable this for production use. ONLY USE FOR DEVELOPMENT
        (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': MEDIA_ROOT}),
    )