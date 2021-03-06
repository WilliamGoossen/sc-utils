from django.template import Library, Node
from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.db import models
from django.shortcuts import get_object_or_404
from django.http import Http404

register = Library()

@register.filter
def split(value, sep=','):
    return [v.strip() for v in value.split(sep)]

@register.filter
def date_tz(value, arg=settings.DATE_FORMAT, tz=settings.TIME_ZONE):
    """ Takes UTC datetime value and formats as string in required timezone
            Requires pytz package - http://pytz.sourceforge.net/
    """
    from datetime import datetime, timedelta
    from pytz import timezone
    
    utc = timezone('UTC')
    loc_tz = timezone(tz)
    utc_dt = value.replace(tzinfo=utc)
    loc_dt = utc_dt.astimezone(loc_tz)
    return loc_dt.strftime(arg)

@register.filter
def flatpage(value, arg=None):
    """ usage {{ "path"|flatpage }}   would fetch flatpage /path/
        usage {{ "path/%s"|flatpage:"more" }}   would fetch flatpage /path/more/
        example {{ "tags/%s"|flatpage:object.name|textile }}
        slashes are appended if missing
    
    """
    if arg and value.find('%s') > -1:
        value = value % arg
    if not value.startswith('/'):
        value = "/" + value
    if not value.endswith('/'):
        value = value + "/"
    result = ''
    try:
        f = get_object_or_404(FlatPage, url__exact=value, sites__id__exact=settings.SITE_ID)
        result = f.content
    except Http404:
        pass
    
    return result

@register.filter
def nologout(value):
    """ Usage: use to stop passing logout url as 'next' to login param
        which immediately logs out user as they log in
    """
    if value.endswith('/accounts/logout/'):
        return '/'
    else:
        return value

@register.filter
def crumbs_no_home(url, title):
    return crumbs(url, title, False)
    
@register.filter
def crumbs(url, title, show_home=True):
    "Return breadcrumb trail leading to URL for this page"
    t = title
    s = '&nbsp;&nbsp;&gt;&nbsp;&nbsp;'
    if show_home: c = '<a href="/">Home</a>' + s
    else: c = ''
    l = url.split('/')
    for index, item in enumerate(l):
        if item == '':
            del l[index]
    n = len(l)
    if n > 1:
        l[0] = '/' + l[0] + '/'
        for i in range(1, n-1):
            l[i] = l[i-1] + l[i] + '/'
        for index2, item2 in enumerate(l):
            q = FlatPage.objects.filter(url=l[index2])
            if q:
                qa = '<a href="%s">%s</a>' % (q[0].url, q[0].title)
                if c == '':
                    c = qa
                else:
                    c = c + s + qa
    if c == '':
        c = t
    else:
        c = c + s + t
    return c

def flatpage_tree(root='wiki'):
    # Create an ordered tree of all flatpages
    def _add_page(_page):
        indent = len(_page.url.split('/')[2:-1])
        return '<p>%s-&nbsp;&nbsp;<a href="%s" title="%s">%s</a></p>' % ('&nbsp;&nbsp;&nbsp;' * indent, _page.url, _page.title, _page.title)
        
    pages = FlatPage.objects.all().order_by('url')
    from django.utils.datastructures import SortedDict
    tree = SortedDict()
    for page in pages:
        segs = page.url.split('/')[2:-1]
        # removes /wiki/ and empty last string
        if len(segs) > 0:
            tree[page.url] = [page, {}]
    menu = '<p><a href="/">Home</a></p>'
    for p in tree.keys():
        menu += _add_page(tree[p][0])
        #menu += '<li><a href="%s" title="%s">%s</a></li>' % (tree[p][0].url, tree[p][0].title, tree[p][0].url)
    #menu += '</ul>'
    return menu 

register.simple_tag(flatpage_tree)

def flatpage_menu():
    # Create an unordered list of all flatpages
    pages = FlatPage.objects.all()
    menu = '<ul>'
    for i in range(len(pages)):
        menu += '<li>'+'<a href="'+pages[i].url+'" title="'+pages[i].title+'">'+pages[i].title+'</a></li>'
    menu += '</ul>'
    return menu 

register.simple_tag(flatpage_menu)

import calendar
@register.filter
def weekdayabbr(value):
    try:
        return calendar.day_abbr[int(value)-1]
    except:
        return '-'

@register.filter
def weekday(value):
    try:
        return calendar.day_name[int(value)-1]
    except:
        return '-'

@register.filter
def get_object_url(value, arg):
    model = models.get_model(*value.split(".", 1))
    target = model._default_manager.get(pk=arg)
    return target.get_absolute_url()

@register.filter
def first_name(user):
    return user.first_name or user.username


"""
from James Bennet blog: http://www.b-list.org/weblog/2006/jun/07/django-tips-write-better-template-tags/

{% get_latest weblog.Link 5 as recent_links %}
{% get_latest weblog.Entry 10 as latest_entries %}
{% get_latest comments.Comment 5 as recent_comments %}
"""
from django.db.models import get_model


class LatestContentNode(Node):
    def __init__(self, model, num, varname):
        self.num, self.varname = num, varname
        self.model = get_model(*model.split('.'))

    def render(self, context):
        context[self.varname] = self.model._default_manager.all()[:self.num]
        return ''

def get_latest(parser, token):
    bits = token.contents.split()
    if len(bits) != 5:
        raise TemplateSyntaxError, "get_latest tag takes exactly four arguments"
    if bits[3] != 'as':
        raise TemplateSyntaxError, "third argument to get_latest tag must be 'as'"
    return LatestContentNode(bits[1], bits[2], bits[4])

get_latest = register.tag(get_latest)

