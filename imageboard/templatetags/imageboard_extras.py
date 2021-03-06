# Copyright (C) 2009,2010,2011 Anthony Rossi
# For License information regarding this software, see LICENSE
# If no LICENSE file was included, see http://www.opensource.org/licenses/mit-license.php

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe


import re

register = template.Library()


def multiply(value, arg):
    """
    Multiplies the value by the arg.
    
    Returns the value if an exception occurs.
    """
    try:
        output = int(value) * int(arg)
    except:
        output = value
    return output
multiply.is_safe = False


def divide(value, arg):
    """
    Divides the value by the arg. Integer division.
    
    Returns 0 if an exception occurs, or if dividing by zero.
    """
    try:
        output = int(value) / int(arg)
    except:
        output = 0
    return output
divide.is_safe = False


def truncatechars(value, arg):
    """
    Truncates a string after a certain number of characters.

    Argument: Number of characters to truncate after.
    """
    from django.utils.encoding import force_unicode
    
    try:
        length = int(arg)
    except ValueError: # Invalid literal for int().
        return value # Fail silently.
    
    words = value
    if len(value) > length: # if the string is longer than the length
        words = value[:length] # truncate
        if not words[-3:].endswith('...'):
            words += '...' # append trailing dots.
    
    return words
truncatechars.is_safe = True
truncatechars = stringfilter(truncatechars)


def forcewrap(value, arg):
    """
    Inserts newline characters every so many characters.
    This filter is dumb and inserts newlines inside words.
    
    Argument: Number of characters to insert a newline
    """
    from django.utils.encoding import force_unicode
    from django.utils.text import wrap
    import textwrap
    
    # Goals and steps to accomplish them:
    #
    # Call the Django wrap() function, then split into a list of lines.
    # then go through the lines and find the ones that are longer than the length, and forcibly insert a newline.
    # finally, join them all back together into a single string.
    
    # Common code to all types
    try:
        length = int(arg) # validate the integer
    except ValueError:
        return value
        
    # Evan's TextWrapper method
    #
    #wrapper = textwrap.TextWrapper()
    #wrapper.width = length
    #wrapper.replace_whitespace = False
    #wrapped_text =  u"\n".join(wrapper.wrap(value))
    #return wrapped_text
    
    
    
    # My TextWrapper method
    #
    #output = textwrap.wrap(value, length)
    #return u'\n'.join(output)

    
    
    # My most successful method
    #
    #lines =  wrap(value, length).splitlines(True)
    #output =[]
    # for li in lines:
        # if len(li) > length + 1:
            # x = 1
            # while x < len(li):
                # if x%length == 0:
                        # li = li[:x] + u'\n' + li[x:]
                # x = x + 1
            # output.append( li )
        # else:
            # output.append(li)
    #return u''.join(output)
    
    # Old broken way. Use for code snippets, but utterly failure code below.
    # for line in lines: # For every line in the input
        # if len(line) > length: # if the line is longer than the arg
            # chars = [] # List of chars
            
            # words = line.split(' ')
            
            # if len(words) == 1: # only one long word in the line
                # pass # insert a newline in the string
                
            # else: # more than 1 word in the line
                # pass
                
            # for i in line: # Put the chars into a list
                # chars.append(i)
                
            # extras = len(chars)/length # compute how many newlines will be inserted into the string
            
            # for i in range(0, len(chars)+extras, length): # Insert newlines
                # chars.insert(i, '\n')
            
            # for i in chars: # append the output to the final result
                # output += i
        # else: # If the line is not too long, then append it to the final result
            # output += line    

    return value # if nothing is uncommented above, do this by default, that is to say, do nothing.
forcewrap.is_safe = True
forcewrap = stringfilter(forcewrap)
    

@stringfilter
def seewhitespace(value, autoescape=None):
    """Converts space to the proper HTML and tabs to 4 space characters.""" 
    if autoescape:
        value = conditional_escape(value)

    #temp = re.sub('\t', '    ', value) # convert tabs to 4 spaces.
    temp = value.expandtabs(4) # convert tabs to 4 spaces.
    temp = re.sub(r'   ', "&nbsp; &nbsp;", temp) # convert 3 spaces to 2 non-breaking spaces and a space.
    return mark_safe(re.sub(r'  ', "&nbsp; ", temp)) # convert 2 spaces to a non-breaking space and a space.
seewhitespace.is_safe = True
seewhitespace.needs_autoescape = True

@stringfilter
def escapeexcepttags(value, tags, autoescape=None):
    """Escapes all [X]HTML tags from the output except those in a space separated list."""
    
    if autoescape:
        value = conditional_escape(value)


    # This in here is what needs to change. 
    tags = [re.escape(tag) for tag in tags.split()]
    tags_re = u'(%s)' % u'|'.join(tags)
    starttag_re = re.compile(ur'<%s(/?>|(\s+[^>]*>))' % tags_re, re.U)
    endtag_re = re.compile(u'</%s>' % tags_re)
    value = starttag_re.sub(u'', value)
    value = endtag_re.sub(u'', value)
    # end of what needs to change
    
    
    return marksafe(value)
escapeexcepttags.needs_autoescape = True
escapeexcepttags.is_safe = True


register.filter('multiply', multiply)
register.filter('divide', divide)
register.filter('truncatechars', truncatechars)
register.filter('forcewrap', forcewrap)
register.filter('seewhitespace', seewhitespace)
register.filter('escapeexcepttags', escapeexcepttags)