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
    Divides the value by the arg.
    
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

@stringfilter
def seewhitespace(value, autoescape=None):
    """Converts space to the proper HTML and tabs to 4 space characters.""" 
    if autoescape:
        value = conditional_escape(value)

    temp = re.sub('\t', '    ', value) # convert tabs to 4 spaces.
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
register.filter('seewhitespace', seewhitespace)
register.filter('escapeexcepttags', escapeexcepttags)