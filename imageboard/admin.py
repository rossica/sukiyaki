# Copyright (C) 2009,2010,2011 Anthony Rossi
# For License information regarding this software, see LICENSE
# If no LICENSE file was included, see http://www.opensource.org/licenses/mit-license.php

# admin.py for Sukiyaki ImageBoard
from django.contrib import admin
from sukiyaki.imageboard.models import  Poster, Board, Post, TextPost, ImagePost, ImgVote, TxtVote
from settings import MEDIA_ROOT
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
    actions = ['ban_poster', 'ban_image', 'unban_image']
    
    def ban_poster(self, request, queryset):
        for post in queryset:
            user = post.poster
            user.banned = True # make the user banned
            user.ban_start = datetime.datetime.now() # the ban starts now
            user.ban_end = datetime.datetime.now() + datetime.timedelta(days=1) # ends a day from now
            user.save()
        queryset.update(comment=comment + "\n\n\nTHIS USER IS B&")
    ban_poster.short_description = "Ban poster(s) of selected posts"
    
    def ban_image(self, request, queryset):
        import Image, ImageDraw, ImageFont, os, stat
        replacement = Image.new("RGB", (128,128), "white")
        draw = ImageDraw.Draw(replacement)
        
        # generate a banned image
        try: 
            font = ImageFont.truetype("comicbd.ttf", 100)
            draw.text((0,0), "B&", font=font, fill="red")
        except: # in case the desired font is unavailable
            font = ImageFont.load_default()
            banned = "B&B&B&B&B&B&B&B&B&B&B&"
            draw.text((0,0), banned, font=font, fill="red")
            draw.text((0,10), banned, font=font, fill="red")
            draw.text((0,20), banned, font=font, fill="red")
            draw.text((0,30), banned, font=font, fill="red")
            draw.text((0,40), banned, font=font, fill="red")
            draw.text((0,50), banned, font=font, fill="red")
            draw.text((0,60), banned, font=font, fill="red")
            draw.text((0,70), banned, font=font, fill="red")
            draw.text((0,80), banned, font=font, fill="red")
            draw.text((0,90), banned, font=font, fill="red")
            draw.text((0,100), banned, font=font, fill="red")
            draw.text((0,110), banned, font=font, fill="red")
            draw.text((0,120), banned, font=font, fill="red")

        for post in queryset:
            img_path = os.path.join(MEDIA_ROOT, post.image.name)
            thumb_path = os.path.join(MEDIA_ROOT, post.thumbnail.name)
            path, filename = os.path.split(img_path)
            name, ext = os.path.splitext(filename)
            
            if img_path == thumb_path: # If the thumbnail and image are the same file, don't write twice (or assume the thumb is JPG)
                # Overwrite the offensive image with the banned image
                if os.stat(img_path).st_mode & stat.S_IWRITE: # file is writeable
                    replacement.save(img_path)
                    os.chmod(img_path, stat.S_IREAD) # Make read-only
            
            else: # The thumbnail and image are not the same file (safe to assume the thumbnail is JPG)
                # Overwrite the offensive image with the banned image
                if os.stat(img_path).st_mode & stat.S_IWRITE: # file is writeable
                    replacement.save(img_path)
                    os.chmod(img_path, stat.S_IREAD) # Make read-only
                    
                # Overwrite the offensive thumbnail with the banned image
                if os.stat(thumb_path).st_mode & stat.S_IWRITE: # thumb is writeable
                    replacement.save(thumb_path, optimize=True)
                    os.chmod(thumb_path, stat.S_IREAD) # make read-only
    ban_image.short_description = "Ban selected images"
    
    def unban_image(self, request, queryset):
        import os, stat
        for post in queryset:
            img_path = os.path.join(MEDIA_ROOT, post.image.name)
            thumb_path = os.path.join(MEDIA_ROOT, post.thumbnail.name)
            
            if img_path == thumb_path:
                os.chmod(img_path, stat.S_IWRITE)
            else:
                os.chmod(img_path, stat.S_IWRITE)
                os.chmod(thumb_path, stat.S_IWRITE)
    unban_image.short_description = "Unban selected images (make them writeable)"

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