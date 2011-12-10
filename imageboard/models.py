# Copyright (C) 2009,2010,2011 Anthony Rossi
# For License information regarding this software, see LICENSE
# If no LICENSE file was included, see http://www.opensource.org/licenses/mit-license.php

from django.db import models
from django.forms import ModelForm, Form
from django import forms
from django.core.files.storage import Storage, FileSystemStorage

import datetime, os.path

# Models for sukiyaki imageboard app
# in the future perhaps use abstract classes for more specific models. such as Imagepost and TextPost and FilePost, and ImageBoard and FileBoard

# Because templates wont let us do multiplication (as of Django 1.1)
INDENT_PIXELS = 50

# Record the software version here. 
# All major version changes involve significant changes to the models (e.g. removing or renaming fields, adding new models, reorganizing structure/inheritance, etc.)
# Significantly changing the way the interface or backend works (as opposed to adding new features and leaving everything else as-is) warrants a major version change.
# Minor version numbers involve adding new features in the admin or views, or adding (but not removing or renaming) model fields
# Bug fixes, if they're all lumped together into a single update, also warrent a minor version bump. Otherwise, they're rolled in with other feature updates.
# For example, version 1.0 was the first stable version with all basic features implemented. 1.1 implements image banning.
SUKIYAKI_VERSION = 1.1

class DuplicateFileStorage(FileSystemStorage):
    def save(self, name, content):
        """
        Saves new content to the file specified by name. The content should be a
        proper File object, ready to be read from the beginning.
        """
        from django.utils.encoding import force_unicode
        # Get the proper name for the file, as it will actually be saved.
        if name is None:
            name = content.name

        if self.exists(name): # If the file already exists, don't save it again. 
            return force_unicode(name.replace('\\', '/'))
            
        name = self._save(name, content)

        # Store filenames with forward slashes, even on Windows
        return force_unicode(name.replace('\\', '/'))

    def delete(self, name):
        """
        Deletes a file specified by name. If the file is read-only, 
        it wont be deleted.
        """
        import os, stat
        name = self.path(name)
        # If the file exists, delete it from the filesystem.
        if os.path.exists(name):
			# But don't delete it if it is read-only. That means it is special.
            attrs = os.stat(name)
            if(attrs.st_mode & stat.S_IWRITE): # File is not Read Only
                os.remove(name)
            else: # File is read only. 
                pass # keep this here in case we want to do something later.
##############################################################################################
dfs = DuplicateFileStorage()


class Poster(models.Model):
    ipaddr = models.IPAddressField(unique=True,)
    banned = models.BooleanField()
    ban_start = models.DateTimeField(default=datetime.datetime.now())
    ban_end = models.DateTimeField(default=datetime.datetime.now())
    last_post_time = models.DateTimeField(auto_now=True)
    
    def get_posts(self):
        return Post.objects.filter(poster=self.id)
    
    def __unicode__(self):
        return self.ipaddr

class Board(models.Model):
    abbr = models.CharField(max_length=5, unique=True, verbose_name="Short name")
    name = models.CharField(max_length=50, unique=True)
    
    nsfw = models.BooleanField("Not safe for work?")
    images = models.BooleanField(default=True, help_text="MUST be set if this board will have images.")
    files = models.BooleanField(help_text="MUST be set if this board will have <b>non-image</b> files.")
    
    max_filesize = models.IntegerField(default=2000, help_text="Max file size in kilobytes, no commas. Zero for no limit. Default: 2 MB.")
    max_image_dimension = models.IntegerField(default=10000, help_text="Maximum x and y length of an image in pixels. Default: 10000 pixels.")
    min_image_dimension = models.IntegerField(default=75, help_text="Minimum x and y length of an image in pixels. Default: 75 pixels.")
    max_thumbnail_size = models.IntegerField(default=250, help_text="Size cutoff to thumbnail images, in pixels. Default 250 pixels.")
    
    max_threads = models.IntegerField(default=100, help_text="Maximum number of threads for this board. Zero for no limit. Default: 100 threads.")
    reply_limit_per_thread = models.IntegerField(default=0, help_text="Maximum number of replies in a thread. Zero for no limit. Default: No limit.")
    time_between_posts = models.IntegerField(default=120, help_text="Time in seconds from last post. Zero for no limit. Default: 2 minutes.")
    max_thread_age = models.IntegerField(default=0, help_text="Time in minutes a thread is allowed to live. Zero for no time limit. Default: No limit.")
    threads_per_page = models.IntegerField(default=10, help_text="Number of threads to display per page. Default: 10 threads.")
    
    
    def __unicode__(self):
        return '/' + self.abbr + '/ ' + self.name
        
    def highest_rank(self):
        '''Returns the highest rank per board'''
        if self.files and not self.images:
            high = FilePost.objects.filter(reply=None, board=self.id).aggregate(rank=models.Max('rank'))['rank']
        elif self.images and not self.files:
            high = ImagePost.objects.filter(reply=None, board=self.id).aggregate(rank=models.Max('rank'))['rank']
        else:
            high = TextPost.objects.filter(reply=None, board=self.id).aggregate(rank=models.Max('rank'))['rank']
        if high != None:
            return high
        else:
            return 0 # default rank

    def count_threads(self):
        '''Number of threads per board'''
        if self.images and not self.files:
            return ImagePost.objects.filter(reply=None, board=self.id).count()
        if not self.images and not self.files:
            return TextPost.objects.filter(reply=None, board=self.id).count()
    count_threads.short_description = "Number of Threads"

    def count_posts(self):
        '''Number of posts per board'''
        if self.images and not self.files:
            return ImagePost.objects.filter(board=self.id).count()
        if not self.images and not self.files:
            return TextPost.objects.filter(board=self.id).count()
    count_posts.short_description = "Number of Posts"

# Posts
class Post(models.Model):
    class Meta:
        abstract = True

    board = models.ForeignKey(Board)
    poster = models.ForeignKey(Poster)
    
    level = models.IntegerField(default=0) # depth in the tree
    rank = models.IntegerField(default=0) # to determine rank within threads
    sticky = models.BooleanField("Stickied", default=False) # to determine rank within boards
    locked = models.BooleanField("Locked from replies", default=False) # whether to allow replies
    
    user_name = models.CharField("User name", max_length=40, default="Anonymous")
    email = models.EmailField("Email", max_length=256, blank=True)
    post_time = models.DateTimeField("Time", auto_now_add=True)
    subject = models.CharField("Subject", max_length=40, blank=True)
    comment = models.TextField("Comment")
    password = models.CharField("Password", max_length=128, blank=True)
    
    def get_replies(self):
        return self.replies.order_by('-rank', '-post_time')
        
    def get_tree(self):
        queue = [] # linear representation of the thread tree of replies
        idx = 0 # where to insert children into the queue
        level = 0 # how far to indent children (replies) in the queue

        # initialize the queue with immediate children
        for c in Post.objects.filter(reply=self).select_related('reply').order_by('-rank','-post_time').iterator():
            queue.append((c, idx*INDENT_PIXELS))

        # Populate the queue with descendants
        for i in queue:
            current = i[0] # fetch the current child (reply)
            idx += 1 # increment the index

            if Post.objects.filter(reply=current).count() == 0: # if the loop is not going to execute (current has no children)
                if level > 0:
                    level -= 1 # decrement the level of indentation

            else: # if the loop will execute (current has children)
                level += 1 # increment the level of indentation
                for j in Post.objects.filter(reply=current).select_related('reply').order_by('-rank','-post_time').reverse().iterator(): # sense of the order has to be reversed because the loop inserts in reverse order
                    queue.insert(idx, (j, level*INDENT_PIXELS))

        return queue
        
    def count_replies(self):
        total = Post.objects.filter(reply=self.id).count()
        for item in Post.objects.filter(reply=self.id).iterator():
            if item.replies.count():
                total += item.count_replies()
        return total

    def __unicode__(self):
        return str(self.id) + ' ' + self.subject


    #def get_absolute_url(self):
    #    return "/post/%i/" % self.id

class TextPost(Post):
    reply = models.ForeignKey('self', related_name='replies', default=None, null=True, blank=True) # limit_choices_to={'board':self.board}
    root = models.ForeignKey('self', default=None, null=True, blank=True) # Original Post
    text = models.BooleanField(default=True, editable=False)
    
    def __get_tree(self, base, queue):
        for post in TextPost.objects.order_by('-rank','-post_time').filter(reply=self.id).iterator():
            queue.append((post, (post.level-base)*INDENT_PIXELS))
            post.__get_tree(base, queue)
        return queue
            
    def get_tree(self):
        return self.__get_tree(self.level, [])
        
    def count_replies(self):
        total = TextPost.objects.filter(reply=self.id).count()
        for item in TextPost.objects.filter(reply=self.id).iterator():
            if item.replies.count():
                total += item.count_replies()
        return total

    def get_highest_ranked_children(self, n=2):
        return TextPost.objects.filter(reply=self.id).order_by('-rank', '-post_time')[:n]

class ImagePost(Post):
    def imgurl(self, filename):
        import hashlib, os.path
        extension = os.path.splitext(filename)
        self.image.seek(0)
        # TODO - Fix this to work with file.chunks() -- potentially uses too much memory
        return "images/%s%s" % (hashlib.sha256(self.image.read(self.image.size)).hexdigest(), extension[1])
        
    def thumburl(self, filename):
        import hashlib, os.path
        extension = os.path.splitext(filename)
        self.image.seek(0)
        # TODO - Fix this to work with file.chunks() -- potentially uses too much memory
        return "thumbs/%s%s" % (hashlib.sha256(self.image.read(self.image.size)).hexdigest(), extension[1])
    
    reply = models.ForeignKey('self', related_name='replies', default=None, null=True, blank=True) # limit_choices_to={'board':self.board}
    root = models.ForeignKey('self', default=None, null=True, blank=True) # Original Post
    image = models.ImageField(upload_to=imgurl, storage=dfs, blank=True)
    thumbnail = models.ImageField(upload_to=thumburl, storage=dfs, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    
    def __unicode__(self):
        return str(self.id) + ' ' + (self.subject or self.file_name)
        
    def count_replies(self):
        total = ImagePost.objects.filter(reply=self.id).count()
        for item in ImagePost.objects.filter(reply=self.id).iterator():
            if item.replies.count():
                total += item.count_replies()
        return total
    
    def __get_tree(self, base, queue):
        for post in ImagePost.objects.order_by('-rank','-post_time').filter(reply=self.id).iterator():
            queue.append((post, (post.level - base)*INDENT_PIXELS))
            post.__get_tree(base, queue)
        return queue
            
    def get_tree(self):
        return self.__get_tree(self.level, [])
        
    def get_highest_ranked_children(self, n=2):
        return ImagePost.objects.filter(reply=self.id).order_by('-rank', '-post_time')[:n]
        
    #def count_image_replies(self):
    #    """Returns the number of descendants with images"""
    #    total = self.replies.extra(where=["image IS NOT ''"]).count()
    #    
    #    for post in self.replies.extra(where=["image IS NOT ''"]).iterator():
    #        total += post.count_image_replies()
    #            
    #    return total


class FilePost(Post):
    reply = models.ForeignKey('self', related_name='replies', default=None, null=True, blank=True) # limit_choices_to={'board':self.board}
    root = models.ForeignKey('self', default=None, null=True, blank=True) # Original Post
    file = models.FileField(upload_to='files')
    thumbnail = models.ImageField(upload_to='fileicons')


# Votes
class Vote(models.Model): 
    class Meta:
        abstract = True
    voter = models.IPAddressField()
    time = models.DateTimeField(auto_now_add=True)
    # If it becomes necesary in the future, possibly store the actual content of the vote here too
    
    def __unicode__(self):
        return self.voter + '->' + self.post.__unicode__()

class ImgVote(Vote):
    post = models.ForeignKey(ImagePost)

class TxtVote(Vote):
    post = models.ForeignKey(TextPost)
    
# Forms
class PostForm(ModelForm):
    password = forms.CharField(label='Password', required=False)
    class Meta:
        model = Post
        exclude = ('board', 'poster', 'reply', 'root', 'rank', 'level', 'sticky', 'locked',)

class TextPostForm(ModelForm):
    subject = forms.CharField(max_length=40, required=True)
    comment = forms.CharField(widget=forms.Textarea, max_length=1000000, required=True)
    password = forms.CharField(label='Password', max_length=1000, required=False, widget=forms.PasswordInput)
    class Meta:
        model = TextPost
        exclude = ('board', 'poster', 'reply', 'root', 'rank', 'level', 'sticky', 'locked',)

class TextReplyForm(ModelForm):
    comment = forms.CharField(widget=forms.Textarea, max_length=1000000, required=True)
    password = forms.CharField(label='Password', max_length=1000, required=False, widget=forms.PasswordInput)
    class Meta:
        model = TextPost
        exclude = ('board', 'poster', 'reply', 'root', 'rank', 'level', 'sticky', 'locked',)

class ImagePostForm(ModelForm):
    comment = forms.CharField(widget=forms.Textarea, max_length=1000000, required=False)
    image = forms.ImageField()
    password = forms.CharField(label='Password', max_length=1000, required=False, widget=forms.PasswordInput)
    class Meta:
        model = ImagePost
        exclude = ('board', 'poster', 'reply', 'root', 'rank', 'level', 'sticky', 'locked', 'thumbnail', 'file_name',)
        
class ImageReplyForm(ModelForm):
    comment = forms.CharField(widget=forms.Textarea, max_length=1000000, required=False)
    image = forms.ImageField(required=False)
    password = forms.CharField(label='Password', max_length=1000, required=False, widget=forms.PasswordInput)
    
    def clean(self):
        cleaned_data = self.cleaned_data
        subject = cleaned_data.get("subject")
        comment = cleaned_data.get("comment")
        image = cleaned_data.get("image")
        
        if not comment and not image:
            raise forms.ValidationError("You must either write a comment or upload a picture.")

        return cleaned_data
    
    class Meta:
        model = ImagePost
        exclude = ('board', 'poster', 'reply', 'root', 'rank', 'level', 'sticky', 'locked', 'thumbnail', 'file_name',)

class DeletePostForm(Form):
    password = forms.CharField(label='Password', max_length=1000, widget=forms.PasswordInput) # , max_length=64
    
class ImgVoteForm(ModelForm):
    class Meta:
        model = ImgVote

class TxtVoteForm(ModelForm):
    class Meta:
        model = TxtVote