# admin.py for Sukiyaki TextBoard
from django.contrib import admin
from sukiyaki.imageboard.models import  Poster, Board, Post, TextPost, ImagePost, ImgVote, TxtVote
import datetime

class ImagePostInline(admin.TabularInline):
    model = ImagePost
    fields = ('user_name', 'email', 'subject', 'sticky', 'locked', 'file_name')
    exclude = ('comment',)
    extra = 0

class PosterAdmin(admin.ModelAdmin):
    fieldsets = [
        ('IP Address', {'fields':['ipaddr'], 'classes':['collapse',], }),
        ('Ban?', {'fields':['banned','ban_start','ban_end',]}),
        #('Posts', {'fields':['get_posts',], 'classes':['collapse']}),
    ]
    inlines = [ImagePostInline]
    list_filter = ('banned',)
    actions = ['ban_1_day']
    
    def ban_1_day(self, request, queryset):
        """Ban poster for 1 day, do not update all posts by poster with 'User was B&'"""
        queryset.update(banned=True, ban_start=datetime.datetime.now(), ban_end = datetime.datetime.now()+datetime.timedelta(days=1))
    ban_1_day.short_description = "Ban selected posters 1 day"

class PostAdmin(admin.ModelAdmin):
    fieldsets = [
        ('User Info', {'fields': ('poster', 'user_name', 'email', 'password',), 'classes':('collapse',)}),
        ('Post Info', {'fields':('board', 'reply', 'sticky', 'locked', 'subject', 'comment',)}),
        ('Back-end', {'fields':('rank', 'root'), 'classes':('collapse',),}),
        #('Password', {'fields':['password'], 'classes':['collapse']}),
    ]
    list_filter = ['post_time']
    date_hierarchy = 'post_time'
    list_display = ('board', 'id', 'user_name', 'email', 'subject', 'poster',)
    list_filter = ('sticky', 'post_time', 'board', 'poster',) # 'rank'
    actions = ['ban_poster']
    
    def ban_poster(self, request, queryset):
        for post in queryset:
            user = post.poster
            user.banned = True # make the user banned
            user.ban_start = datetime.datetime.now() # the ban starts now
            user.ban_end = datetime.datetime.now() + datetime.timedelta(days=1) # ends a day from now
            user.save()
        queryset.update(comment=comment + "\n\n\nTHIS USER IS B&")
    ban_poster.short_description = "Ban poster(s) of selected posts"
   
class TextPostAdmin(admin.ModelAdmin):
    fieldsets = [
        ('User Info', {'fields': ('poster', 'user_name', 'email', 'password',), 'classes':('collapse',)}),
        ('Post Info', {'fields':('board', 'reply', 'sticky', 'locked', 'subject', 'comment',)}),
        ('Back-end', {'fields':('rank', 'level', 'root'), 'classes':('collapse',),}),
        #('Password', {'fields':['password'], 'classes':['collapse']}),
    ]
    date_hierarchy = 'post_time'
    list_filter = ('sticky', 'post_time', 'board', 'poster',)
    list_display = ('board', 'id', 'poster', 'user_name', 'email', 'subject',)
   
class ImagePostAdmin(admin.ModelAdmin):
    fieldsets = [
        ('User Info', {'fields': ('poster', 'user_name', 'email', 'password',), 'classes':('collapse',)}),
        ('Post Info', {'fields':('board', 'reply', 'sticky', 'locked', 'subject', 'comment',)}),
        ('Back-end', {'fields':('rank', 'level', 'root'), 'classes':('collapse',),}),
        #('Password', {'fields':['password'], 'classes':['collapse']}),
    ]
    date_hierarchy = 'post_time'
    list_display = ('board', 'id', 'user_name', 'email', 'subject', 'poster',)
    list_filter = ('sticky', 'post_time', 'board', 'poster',) # 'rank'
    actions = ['ban_poster']
    
    def ban_poster(self, request, queryset):
        for post in queryset:
            user = post.poster
            user.banned = True # make the user banned
            user.ban_start = datetime.datetime.now() # the ban starts now
            user.ban_end = datetime.datetime.now() + datetime.timedelta(days=1) # ends a day from now
            user.save()
        queryset.update(comment=comment + "\n\n\nTHIS USER IS B&")
    ban_poster.short_description = "Ban poster(s) of selected posts"

class BoardAdmin(admin.ModelAdmin):
    fieldsets = [
        ('General Settings', {'fields':('abbr', 'name', 'nsfw', 'images', 'files'),}),
        ('Image/File Settings', {'fields':('max_filesize', 'max_image_dimension', 'min_image_dimension', 'max_thumbnail_size'), 'classes':('collapse',),}),
        ('Thread Settings', {'fields':('max_threads', 'max_thread_age', 'reply_limit_per_thread', 'threads_per_page', 'time_between_posts'), 'classes':('collapse',),}),
    ]
    inlines = [ImagePostInline]
    list_display = ('name', 'abbr', 'count_threads', 'count_posts')
    
class ImgVoteAdmin(admin.ModelAdmin):
    list_display = ('voter', 'post',)
    list_filter = ('voter', 'post', 'time')

class TxtVoteAdmin(admin.ModelAdmin):
    list_display = ('voter', 'post',)
    list_filter = ('voter', 'post', 'time')

admin.site.register(Poster, PosterAdmin)
admin.site.register(Board, BoardAdmin)
#admin.site.register(Post, PostAdmin)
admin.site.register(TextPost, TextPostAdmin)
admin.site.register(ImagePost, ImagePostAdmin)
admin.site.register(ImgVote, ImgVoteAdmin)
admin.site.register(TxtVote, TxtVoteAdmin)