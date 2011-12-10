# Views for sukiyaki imageboard app
from sukiyaki.imageboard.models import TextPost, ImagePost, Board, Poster, TxtVote, ImgVote, PostForm, TextPostForm, TextReplyForm, ImagePostForm, ImageReplyForm, DeletePostForm, TxtVoteForm, ImgVoteForm
from settings import MEDIA_ROOT

from django.db.models import F
from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponseRedirect, Http404
from django.core.files import File
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core.urlresolvers import reverse
from django.template import Context

import datetime, hashlib, os, stat
from PIL import Image

# Querysets
board_list = Board.objects.order_by('nsfw', 'abbr').all()

# Objects
ImgPostForm = ImagePostForm()
ImgReplyForm = ImageReplyForm()
TxtPostForm = TextPostForm()
TxtReplyForm = TextReplyForm()
DelPostForm = DeletePostForm()

# Constants
SALT = "@8Y<WjKCg3@UV^5Y5>"
MAX_DEPTH = 100
SECONDS_BETWEEN_VOTES = 15


# Helper functions that are NEVER meant to be a view
def _gen_thumbnail(imgpost, uploaded_image):
    """Generate a thumbnail and save it to disk and in the imgpost. Must be the last field modified before save()"""
    if imgpost.image.width <= imgpost.board.max_thumbnail_size and imgpost.image.height <= imgpost.board.max_thumbnail_size:
        imgpost.thumbnail = imgpost.imgurl(uploaded_image.name)
    else:
        uploaded_image.seek(0) # seek to the beginning of the uploaded file
        thumb_name = imgpost.thumburl(uploaded_image.name) # Generate the filename of the thumbnail
        # Force generated thumbnails to be jpg
        thumb_name, oldext = os.path.splitext(thumb_name)
        thumb_name += ".jpg"
        save_to = os.path.join(MEDIA_ROOT, thumb_name) # Generate the path to save the thumbnail
        
        if not os.path.exists(save_to): # if the thumbnail doesn't exist already
            # TODO wrap in try-except for cases where PIL can't figure out what a file is
            uploaded_image.seek(0) # seek to the beginning of the uploaded file
            thmb = Image.open(uploaded_image).convert('RGB') # Create an Image from the uploaded image and convert it to RGB
            thmb_size = (imgpost.board.max_thumbnail_size, imgpost.board.max_thumbnail_size) # Image.thumbnail() requires a tuple of the maximal dimensions
            thmb.thumbnail(thmb_size, Image.NEAREST) # Create the thumbnail using the fastest method
            
            ## WARNING!! This will overwrite any previous thumbnail with the same name. FIX to use the Django save() method ASAP. -- Fixed. disregard
            ## WARNING! This is not compatible with non-disk-based storage. FIX to use Django's save() -- maybe not possible with PIL
            thmb.save(save_to, optimize=True) #Save using the Image.save() method. I would rather use the Django save() method, but this works. 
            imgpost.thumbnail = thumb_name # Finally, save the relative path to the thumbnail in the database.
    #imgpost.thumbnail.save(thumb_name, open(save_to))

def _get_post_form(post_id):
    try:
        p = ImagePost.objects.get(pk=post_id)
        form = ImgReplyForm
    except ImagePost.DoesNotExist:
        try:
            p = TextPost.objects.get(pk=post_id)
            form = TxtReplyForm
        except TextPost.DoesNotExist:
            # try FilePost
            raise Http404
    return (p, form)
        
def _increment_rank(parent, reply):
    """Update the reference to the root (OP) of the thread and increment ranks."""
    if parent.reply == None: # if the parent is OP
        reply.root = parent
        # Increment rank of the root (OP)
        reply.root.rank = F('rank') + 1
        reply.root.save()
    else: # otherwise
        reply.root = parent.root
        # Increment rank of the parent
        parent.rank = F('rank') + 1
        parent.save()
        # Increment rank of the root (OP)
        reply.root.rank = F('rank') + 1
        reply.root.save()
    ## Try to fix this later, it really is the desired behavior
    #while parent.reply != None: # increment the rank of all ancestors, or climb all the way to the top-most post (root)
    #    parent.rank = F('rank') + 1 # increase the rank of the parent # comment out this and the next line to only increase rank of the top-most post (root)
    #    parent.save() # save the parent # comment out this and the previous line to only increase rank of the top-most post (root)
    #    parent = Post.objects.only('rank','reply').get(id=parent.reply.id) # climb the tree to the next-highest parent
        #parent = parent.reply # climb the tree to the next-highest parent
    #parent.rank = F('rank') + 1 # increase the rank of the top-most post (root)
    #parent.save()

def _imgpost(request, board):
    posts = board.imagepost_set.filter(reply=None).order_by('sticky', 'rank', 'post_time').reverse()
    paginator = Paginator(posts, board.threads_per_page)
    
    form = ImagePostForm(request.POST, request.FILES)
    if form.is_valid():
        # get the IP address of the Poster, and store it if new, or stop if banned
        remote_addr = request.META['REMOTE_ADDR']
        new_poster, poster_created = Poster.objects.get_or_create(ipaddr=remote_addr)
        if not poster_created and new_poster.banned: # if the Poster is not new, and is banned
            if new_poster.ban_end < datetime.datetime.now(): # Need to check if a user's ban has expired. If so, remove their ban, and continue 
                new_poster.banned = False # unban the Poster
            else: # they are still banned
                return render_to_response('imageboard/banned.html', {'board_list':board_list, 'board':board, 'poster':new_poster} ) # Banned poster, do not post
        elif not poster_created and board.time_between_posts > 0 and datetime.datetime.now() - new_poster.last_post_time < datetime.timedelta(seconds=board.time_between_posts): # The Poster is not new, and has posted less than time_between_posts seconds ago
            error_message = "Flood detected! Please wait to post."
            return render_to_response('imageboard/board.html', {'board_list':board_list, 'board':board, 'form':form, 'error_message':error_message, 'posts':paginator.page(1),}) 
            
        #check if the thread limit for this board has been reached, if so, delete the lowest ranked thread, and continue
        if ImagePost.objects.filter(reply=None, board=board.id, sticky=False).count() >= board.max_threads > 0:
            p = ImagePost.objects.filter(reply=None, board=board.id, sticky=False).order_by('rank', 'post_time')[0]
            p.delete()
        
        tempPost = form.save(commit=False) # get the Post object

        tempPost.board = board # set the board this post belongs to
        tempPost.poster = new_poster # set the poster this post belongs to

        tempPost.rank = board.highest_rank() # set the rank of this post to the highest rank
        tempPost.reply = None # Since this is a top-level post, it is a reply to nothing
        tempPost.password = hashlib.sha512(SALT + tempPost.password).hexdigest() # save the password as a hash
        
        # Enforce image size less than the board limit
        if tempPost.image.size > (board.max_filesize * 1000):
            error_message = "File size is " + str(tempPost.image.size - (board.max_filesize *1000)) + " bytes larger than the maximum of " + str(board.max_filesize) + " kilobytes."
            return render_to_response('imageboard/board.html', {'board_list':board_list, 'board':board, 'form':form, 'error_message':error_message, 'posts':paginator.page(1),})
            
        # Enforce image dimensions
        if not board.min_image_dimension < tempPost.image.width < board.max_image_dimension or not board.min_image_dimension < tempPost.image.height < board.max_image_dimension:
            error_message = "Images must be at least " + str(board.min_image_dimension) + "x" + str(board.min_image_dimension) + " pixels and no more than "
            error_message += str(board.max_image_dimension) + "x" + str(board.max_image_dimension) + " pixels"
            return render_to_response('imageboard/board.html', {'board_list':board_list, 'board':board, 'form':form, 'error_message':error_message, 'posts':paginator.page(1),})
        
        # Save the original filename. Maybe later we can make it so that files are downloaded with this name
        tempPost.file_name = form.cleaned_data['image'].name 
        
        # This must come last. Right before the image is saved.
        _gen_thumbnail(tempPost, form.cleaned_data['image'])
        
        new_poster.save() # save the last_post_time for the Poster
        tempPost.save() # save the object to the databse finally
        
        return HttpResponseRedirect(reverse('sukiyaki.imageboard.views.view_post', args=(tempPost.id,)))
    else: # if the form is invalid
        return render_to_response('imageboard/board.html', {'form':form, 'delform':DelPostForm, 'board_list':board_list, 'board':board}) # {'form':form, 'delform':DelPostForm, 'board_list':board_list,}

def _imgreply(request, parent):
    form = ImageReplyForm(request.POST, request.FILES)
    if form.is_valid():
        # get the iP address of the poster, store it, or stop if banned
        remote_addr = request.META['REMOTE_ADDR']
        new_poster, poster_created = Poster.objects.get_or_create(ipaddr=remote_addr)
        if not poster_created and new_poster.banned:
            if new_poster.ban_end < datetime.datetime.now(): # Need to check if a user's ban has expired. If so, remove their ban, and continue 
                new_poster.banned = False
            else: # if they are still banned 
                return render_to_response('imageboard/banned.html', {'board_list':board_list,'poster':new_poster})
        elif not poster_created and parent.board.time_between_posts > 0 and datetime.datetime.now() - new_poster.last_post_time < datetime.timedelta(seconds=parent.board.time_between_posts): # The Poster is not new, and has posted less than time_between_posts seconds ago
            return render_to_response('imageboard/post.html', {'post':parent, 'form':form, 'delform':DelPostForm, 'board_list':board_list, 'error_message':"Flood detected! Please wait to reply."})
            
        
        # Test is the board even has a reply limit
        if parent.board.reply_limit_per_thread > 0:
            # Test if the reply limit for the thread has been reached.
            reply_limit = _test_reply_limit(parent, form)
            if reply_limit: # If the reply limit has been reached, return.
                return reply_limit

        reply = form.save(commit=False) # get the reply

        reply.level = parent.level + 1 # one level deeper than the parent
        if reply.level >= MAX_DEPTH: # If the maximum reply depth has been reached, lock the post from replies.
            reply.locked = True
        reply.board = parent.board # same board as parent
        reply.poster = new_poster # set the poster
        reply.reply = parent # set the parent

        
        # update the reference to the root (OP) of the thread and increment ranks
        _increment_rank(parent, reply)
        
        reply.rank = 0
        reply.password = hashlib.sha512(SALT + reply.password).hexdigest() # save the password as a hash
        
        # Test for the existence of an image.
        if form.cleaned_data['image']:
            # Enforce image size less than the board limit
            if reply.image.size > (parent.board.max_filesize * 1000):
                error_message = "File size is " + str(reply.image.size - (parent.board.max_filesize *1000)) + " bytes larger than the maximum of " + str(parent.board.max_filesize) + " kilobytes."
                return render_to_response('imageboard/post.html', {'board_list':board_list, 'form':form, 'delform':DelPostForm, 'error_message':error_message, 'post':parent,})
                
            # Enforce image dimensions
            if not parent.board.min_image_dimension < reply.image.width < parent.board.max_image_dimension or not parent.board.min_image_dimension < reply.image.height < parent.board.max_image_dimension:
                error_message = "Images must be at least " + str(parent.board.min_image_dimension) + "x" + str(parent.board.min_image_dimension) + " pixels and no more than "
                error_message += str(parent.board.max_image_dimension) + "x" + str(parent.board.max_image_dimension) + " pixels"
                return render_to_response('imageboard/post.html', {'board_list':board_list, 'form':form, 'delform':DelPostForm, 'error_message':error_message, 'post':parent,})
        
            # Generate the thumbnail right before saving.
            _gen_thumbnail(reply, form.cleaned_data['image'])
        
            # Save the original filename. Maybe later we can make it so that files are downloaded with this name
            reply.file_name = form.cleaned_data['image'].name 
        
        new_poster.save() # save the last_post_time for the Poster
        reply.save() # save the reply
            
        # where to go after replying: the root, or the post being replied to
        if parent.root:
            return_to = parent.root.id
        else:
            return_to = parent.id
            
        return HttpResponseRedirect(reverse('sukiyaki.imageboard.views.view_post', args=(return_to,))) # go back to the root (OP)
    else: # invalid form
        return render_to_response('imageboard/post.html', {'post':parent, 'form':form, 'delform':DelPostForm, 'board_list':board_list,})

def _test_reply_limit(parent, form):
    """Check if the reply_limit has been reached for this thread, if so, lock the thread."""
    if parent.root:
        count = parent.root.count_replies()
        if count + 1 == parent.board.reply_limit_per_thread > 0:
            parent.locked = True
            parent.root.locked = True
        elif count > parent.board.reply_limit_per_thread > 0:
            return render_to_response('imageboard/post.html', {'post':parent.root, 'form':form, 'delform':DelPostForm, 'board_list':board_list, 'error_message':"Thread full."})
    else:
        count = parent.count_replies()
        if count + 1 == parent.board.reply_limit_per_thread > 0:
            parent.locked = True
        elif count > parent.board.reply_limit_per_thread > 0:
            return render_to_response('imageboard/post.html', {'post':parent, 'form':form, 'delform':DelPostForm, 'board_list':board_list, 'error_message':"Thread full."})

def _txtpost(request, board):
    form = TextPostForm(request.POST)
    if form.is_valid():
        # get the IP address of the Poster, and store it if new, or stop if banned
        remote_addr = request.META['REMOTE_ADDR']
        new_poster, poster_created = Poster.objects.get_or_create(ipaddr=remote_addr)
        if not poster_created and new_poster.banned: # if the Poster is not new, and is banned
            if new_poster.ban_end < datetime.datetime.now(): # Need to check if a user's ban has expired. If so, remove their ban, and continue 
                new_poster.banned = False # unban the Poster
            else: # they are still banned
                return render_to_response('imageboard/banned.html', {'board_list':board_list, 'board':board, 'poster':new_poster} ) # Banned poster, do not post
        elif not poster_created and board.time_between_posts > 0 and datetime.datetime.now() - new_poster.last_post_time < datetime.timedelta(seconds=board.time_between_posts): # The Poster is not new, and has posted less than time_between_posts seconds ago
            error_message = "Flood detected! Please wait to post."
            posts = board.textpost_set.filter(reply=None).order_by('sticky', 'rank', 'post_time')
            return render_to_response('imageboard/board.html', {'board_list':board_list, 'board':board, 'form':form, 'error_message':error_message, 'posts':posts,}) 
            
        #check if the thread limit for this board has been reached, if so, delete the lowest ranked thread, and continue
        if TextPost.objects.filter(reply=None, board=board.id, sticky=False).count() >= board.max_threads > 0:
            p = TextPost.objects.filter(reply=None, board=board.id, sticky=False).order_by('rank', 'post_time')[0]
            p.delete()
        
        tempPost = form.save(commit=False) # get the Post object

        tempPost.board = board # set the board this post belongs to
        tempPost.poster = new_poster # set the poster this post belongs to

        tempPost.rank = board.highest_rank() # set the rank of this post to the highest rank
        tempPost.reply = None # Since this is a top-level post, it is a reply to nothing
        tempPost.password = hashlib.sha512(SALT + tempPost.password).hexdigest() # save the password as a hash
        
        new_poster.save() # save the last_post_time for the Poster
        tempPost.save() # save the object to the databse finally
        
        return HttpResponseRedirect(reverse('sukiyaki.imageboard.views.view_text_post', args=(tempPost.id,)))
    else: # if the form is invalid
        return render_to_response('imageboard/board.html', {'form':form, 'delform':DelPostForm, 'board_list':board_list, 'board':board}) # {'form':form, 'delform':DelPostForm, 'board_list':board_list,}

def _txtreply(request, parent):
    form = TextReplyForm(request.POST)
    if form.is_valid():
        # get the iP address of the poster, store it, or stop if banned
        remote_addr = request.META['REMOTE_ADDR']
        new_poster, poster_created = Poster.objects.get_or_create(ipaddr=remote_addr)
        if not poster_created and new_poster.banned:
            if new_poster.ban_end < datetime.datetime.now(): # Need to check if a user's ban has expired. If so, remove their ban, and continue 
                new_poster.banned = False
            else: # if they are still banned 
                return render_to_response('imageboard/banned.html', {'board_list':board_list,'poster':new_poster})
        elif not poster_created and parent.board.time_between_posts > 0 and datetime.datetime.now() - new_poster.last_post_time < datetime.timedelta(seconds=parent.board.time_between_posts): # The Poster is not new, and has posted less than time_between_posts seconds ago
            return render_to_response('imageboard/post.html', {'post':parent, 'form':form, 'delform':DelPostForm, 'board_list':board_list, 'error_message':"Flood detected! Please wait to reply."})
            
        
        # Test if the reply limit for the thread has been reached.
        reply_limit = _test_reply_limit(parent, form)
        if reply_limit: # If the reply limit has been reached, return.
            return reply_limit

        reply = form.save(commit=False) # get the reply

        reply.level = parent.level + 1 # one level deeper than the parent
        if reply.level >= MAX_DEPTH: # If the maximum reply depth has been reached, lock the post from replies.
            reply.locked = True
        reply.board = parent.board # same board as parent
        reply.poster = new_poster # set the poster
        reply.reply = parent # set the parent

        
        # update the reference to the root (OP) of the thread and increment ranks
        _increment_rank(parent, reply)
        
        reply.rank = 0
        reply.password = hashlib.sha512(SALT + reply.password).hexdigest() # save the password as a hash
        
        new_poster.save() # save the last_post_time for the Poster
        reply.save() # save the reply
            
        # where to go after replying: the root, or the post being replied to
        if parent.root:
            return_to = parent.root.id
        else:
            return_to = parent.id
            
        return HttpResponseRedirect(reverse('sukiyaki.imageboard.views.view_text_post', args=(return_to,))) # go back to the root (OP)
    else: # invalid form
        return render_to_response('imageboard/post.html', {'post':parent, 'form':form, 'delform':DelPostForm, 'board_list':board_list,})

# View functions
def board_index(request):
    return render_to_response('imageboard/index.html', {'board_list':board_list,})

def view_board(request, board_abbr):
    b = get_object_or_404(Board, abbr=board_abbr)
    # If time limits are placed on threads, either delete them here, or put some kind of warning of impending deletion
    # We're going to delete them with no warning.
    if b.max_thread_age > 0:
        # cover cases for each type of post, depending on board.
        if b.files and not b.images: # Files
            cutoff = datetime.datetime.now() - datetime.timedelta(seconds=(b.max_thread_age*60))
            #posts = b.filepost_set.filter(reply=None)
        elif b.images and not b.files: # Images
            cutoff = datetime.datetime.now() - datetime.timedelta(seconds=(b.max_thread_age*60))
            b.imagepost_set.filter(reply=None, sticky=False, post_time__lte=cutoff).delete()
        elif not b.images and not b.files: #Text
            cutoff = datetime.datetime.now() - datetime.timedelta(seconds=(b.max_thread_age*60))
    
    # Which kind of form and posts do we display?
    # Later on, we can also decide which template to show depending on the board type
    if b.files and not b.images:
        posts = b.filepost_set.filter(reply=None).order_by('sticky', 'rank', 'post_time').reverse()
        # form = filepostform
    elif b.images and not b.files:
        posts = b.imagepost_set.filter(reply=None).order_by('sticky', 'rank', 'post_time').reverse()
        form = ImgPostForm
    elif not b.images and not b.files:
        posts = b.textpost_set.filter(reply=None).order_by('sticky', 'rank', 'post_time').reverse()
        form = TxtPostForm
        
    paginator = Paginator(posts, b.threads_per_page)
    
    # Ensure that the page GET is an int. Otherwise, default to page 1.
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    # If page request (9999) is out of range, deliver last page of results.
    try:
        posts_page = paginator.page(page)
    except (EmptyPage, InvalidPage):
        posts_page = paginator.page(paginator.num_pages)
    
    # for now, we just use the same template, because it's sort of generic.
    return render_to_response('imageboard/board.html', {'board':b, 'posts':posts_page, 'board_list':board_list, 'form':form,})

def view_post(request, post_id):
    p = get_object_or_404(ImagePost, pk=post_id)
    form = ImgReplyForm
    
    return render_to_response('imageboard/post.html', {'post':p, 'board_list':board_list, 'form':form, 'delform':DelPostForm})
    
def view_text_post(request, text_id):
    p = get_object_or_404(TextPost, pk=text_id)
    form = TxtReplyForm
    
    return render_to_response('imageboard/post.html', {'post':p, 'board_list':board_list, 'form':form, 'delform':DelPostForm})
    
def post(request, board_abbr):
    board = get_object_or_404(Board, abbr=board_abbr)
    
    if request.method == 'POST':
    
        # Test board type here and jump to appropriate validation
        if board.images and not board.files: # ImagePost
            return _imgpost(request, board)
        elif not board.images and not board.files: # TextPost
            return _txtpost(request, board)
        
    else: # not POST
        if board.images and not board.files:
            form = ImgPostForm
        elif not board.images and not board.files:
            form = TxtPostForm
        return render_to_response('imageboard/board.html', {'form':form, 'delform':DelPostForm, 'board_list':board_list,})

def reply(request, reply_to):
    parent = get_object_or_404(ImagePost, pk=reply_to)
    form = ImgReplyForm
    
    # Detect locked threads/posts
    if parent.root:
        if parent.root.locked: # if  thread is locked
            return render_to_response('imageboard/post.html', {'post':parent, 'form':form, 'delform':DelPostForm, 'board_list':board_list,'error_message':"Post is locked: No replies allowed"}) # Fix the dictionary
    else:
        if parent.locked: # if replies aren't allowed on the parent
            return render_to_response('imageboard/post.html', {'post':parent, 'form':form, 'delform':DelPostForm, 'board_list':board_list,'error_message':"Post is locked: No replies allowed"}) # Fix the dictionary
    
    # If this is a POST request
    if request.method == 'POST':
    
        return _imgreply(request, parent)

    else: # not POST
        return render_to_response('imageboard/post.html', {'post':parent, 'form':ImgPostForm, 'delform':DelPostForm, 'board_list':board_list,})
    ''' three ways to handle the reply problem:
        1) display a reply_to field that the user populates (WRONG)
        2) when browsing the board, there is no "reply" link for each post, only a "view" link, which then takes the user to a page where they can see the post and all replies
            there, they can click a "reply" link that will:
                a) open a posting form right below the parent post (requires JavaScript)
                b) open a new page with the reply_to post as the parent (a subtree, if you will) and the post form at the top
    '''

def text_reply(request, reply_to):
    parent = get_object_or_404(TextPost, pk=reply_to)
    form = TxtReplyForm
    
    if parent.root:
        if parent.root.locked: # if  thread is locked
            return render_to_response('imageboard/post.html', {'post':parent, 'form':form, 'delform':DelPostForm, 'board_list':board_list,'error_message':"Post is locked: No replies allowed"}) # Fix the dictionary
    else:
        if parent.locked: # if replies aren't allowed on the parent
            return render_to_response('imageboard/post.html', {'post':parent, 'form':form, 'delform':DelPostForm, 'board_list':board_list,'error_message':"Post is locked: No replies allowed"}) # Fix the dictionary
    
    # If this is a POST request
    if request.method == 'POST':
    
        return _txtreply(request, parent)

    else: # not POST
        return render_to_response('imageboard/post.html', {'post':parent, 'form':TxtPostForm, 'delform':DelPostForm, 'board_list':board_list,})

def delete(request, post_id):
    dead_post = get_object_or_404(ImagePost, pk=post_id)
    
    if dead_post.password == hashlib.sha512(SALT + '').hexdigest(): # can't delete empty passwords
        return render_to_response('imageboard/post.html', {'post':dead_post, 'pw_error':"Empty password, can't delete", 'delform':DelPostForm, 'board_list':board_list, 'form':form})
    
    if request.method == 'POST': # if the form is submitted through a POST
        delform = DeletePostForm(request.POST) # create a form based on submitted data
        
        if delform.is_valid(): # if the form is valid 
            
            if dead_post.password == hashlib.sha512(SALT + delform.cleaned_data['password']).hexdigest(): # if the passwords match
                dead_post.delete() # delete the post
                
                # Need to do something special with banned users. Can they delete their own posts?
                return HttpResponseRedirect(reverse('sukiyaki.imageboard.views.view_board', args=(dead_post.board.abbr)))
            
            else: # the passwords don't match
                return render_to_response('imageboard/post.html', {'post':dead_post, 'delform': DelPostForm, 'pw_error':"Wrong Password",})
                
        else: # inavlid form
            return render_to_response('imageboard/post.html', {'post':dead_post, 'delform':DelPostForm, })
            
    else: # not POST
        return render_to_response('imageboard/post.html', {'post':dead_post, 'delform':DelPostForm, })

def delete_text(request, text_id):
    dead_post = get_object_or_404(TextPost, pk=text_id)
    
    if dead_post.password == hashlib.sha512(SALT + '').hexdigest(): # can't delete empty passwords
        return render_to_response('imageboard/post.html', {'post':dead_post, 'pw_error':"Empty password, can't delete", 'delform':DelPostForm, 'board_list':board_list, 'form':form})
    
    if request.method == 'POST': # if the form is submitted through a POST
        delform = DeletePostForm(request.POST) # create a form based on submitted data
        
        if delform.is_valid(): # if the form is valid 
            
            if dead_post.password == hashlib.sha512(SALT + delform.cleaned_data['password']).hexdigest(): # if the passwords match
                dead_post.delete() # delete the post
                
                # Need to do something special with banned users. Can they delete their own posts?
                return HttpResponseRedirect(reverse('sukiyaki.imageboard.views.view_board', args=(dead_post.board.abbr)))
            
            else: # the passwords don't match
                return render_to_response('imageboard/post.html', {'post':dead_post, 'delform': DelPostForm, 'pw_error':"Wrong Password",})
                
        else: # inavlid form
            return render_to_response('imageboard/post.html', {'post':dead_post, 'delform':DelPostForm, })
            
    else: # not POST
        return render_to_response('imageboard/post.html', {'post':dead_post, 'delform':DelPostForm, })    

def sage(request, post_id, sage):
    vote_me = get_object_or_404(ImagePost, pk=post_id)
    
    if request.method == 'POST': # make sure this is a POST, not a GET

        form = ImgVoteForm({'voter':request.META['REMOTE_ADDR'], 'post':post_id}) # create a form from the IPAddress of the voter
        
        if form.is_valid(): # if the data is valid
        
            # where to go afterwards: 
            if vote_me.root:
                return_to = vote_me.root.id
            else:
                return_to = post_id

            

            # If the user has already voted for this topic
            if ImgVote.objects.filter(voter=form.cleaned_data['voter'], post=form.cleaned_data['post']).count():
                error = 'You have already voted on this post. You only get one.'
                return render_to_response('imageboard/sage.html', {'error':error, 'return':return_to,})
            # If the user has voted ever...
            if ImgVote.objects.filter(voter=form.cleaned_data['voter']).count():
                if datetime.datetime.now() - ImgVote.objects.filter(voter=form.cleaned_data['voter']).order_by('-time')[0].time < datetime.timedelta(seconds=SECONDS_BETWEEN_VOTES):
                    error = 'Flood detected. Please wait at least '+ str(SECONDS_BETWEEN_VOTES) + ' seconds to vote again.'
                    return render_to_response('imageboard/sage.html', {'error':error, 'return':return_to,})
            
            form.save() # Save the vote in the database

            if sage == 's':
                vote_me.rank = F('rank') - 1 #decrement the rank
                vote_me.save() # save
                message = 'Sage recorded successfully. Thank you for making this a better place.'
            else:
                vote_me.rank = F('rank') + 1 #increment the rank
                vote_me.save() # save
                message = 'Age recorded successfully. Thank you for making this a better place.'

            return render_to_response('imageboard/sage.html', {'message':message, 'return':return_to})
        else: # form data was invalid
            return HttpResponseRedirect(reverse('sukiyaki.imageboard.views.view_post', args=(post_id,)))
    else: #not a POST
        return HttpResponseRedirect(reverse('sukiyaki.imageboard.views.view_post', args=(post_id,)))

def sage_text(request, text_id, sage):
    vote_me = get_object_or_404(TextPost, pk=text_id)
    
    if request.method == 'POST': # make sure this is a POST, not a GET

        form = TxtVoteForm({'voter':request.META['REMOTE_ADDR'], 'post':text_id}) # create a form from the IPAddress of the voter
        
        if form.is_valid(): # if the data is valid
        
            # where to go afterwards: 
            if vote_me.root:
                return_to = vote_me.root.id
            else:
                return_to = text_id
                
            # If the user has already voted for this topic
            if TxtVote.objects.filter(voter=form.cleaned_data['voter'], post=form.cleaned_data['post']).count():
                error = 'You have already voted on this post. You only get one.'
                return render_to_response('imageboard/sage.html', {'error':error, 'type':'t', 'return':return_to,})
            # If the user has voted ever...
            if TxtVote.objects.filter(voter=form.cleaned_data['voter']).count():
                if datetime.datetime.now() - TxtVote.objects.filter(voter=form.cleaned_data['voter']).order_by('-time')[0].time < datetime.timedelta(seconds=SECONDS_BETWEEN_VOTES):
                    error = 'Flood detected. Please wait at least '+ str(SECONDS_BETWEEN_VOTES) + ' seconds to vote again.'
                    return render_to_response('imageboard/sage.html', {'error':error, 'return':return_to,})
            
            form.save() # Save the vote in the database
            
            if sage == 's':
                vote_me.rank = F('rank') - 1 #decrement the rank
                vote_me.save() # save
                message = 'Sage recorded successfully. Thank you for making this a better place.'
            else:
                vote_me.rank = F('rank') + 1 #increment the rank
                vote_me.save() # save
                message = 'Age recorded successfully. Thank you for making this a better place.'

            return render_to_response('imageboard/sage.html', {'type':'t', 'message':message, 'return':return_to})
        else: # form data was invalid
            return HttpResponseRedirect(reverse('sukiyaki.imageboard.views.view_post', args=(text_id,)))
    else: #not a POST
        return HttpResponseRedirect(reverse('sukiyaki.imageboard.views.view_post', args=(text_id,)))