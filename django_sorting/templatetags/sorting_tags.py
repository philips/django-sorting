from django import template
from django.http import Http404
from django.conf import settings
import warnings

register = template.Library()

DEFAULT_SORT_UP = getattr(settings, 'DEFAULT_SORT_UP' , '&uarr;')
DEFAULT_SORT_DOWN = getattr(settings, 'DEFAULT_SORT_DOWN' , '&darr;')
INVALID_FIELD_RAISES_404 = getattr(settings, 
        'SORTING_INVALID_FIELD_RAISES_404' , False)

sort_directions = {
    'asc': {'icon':DEFAULT_SORT_UP, 'inverse': 'desc'}, 
    'desc': {'icon':DEFAULT_SORT_DOWN, 'inverse': 'asc'}, 
    '': {'icon':DEFAULT_SORT_DOWN, 'inverse': 'asc'}, 
}

def sort_anchor(parser, token):
    """
    Parses a tag that's supposed to be in this format: {% sort_anchor "field" "title" %}
    """
    bits = token.split_contents()
    if len(bits) < 2:
        raise TemplateSyntaxError, "anchor tag takes at least 1 argument"
    try:
        title = bits[2]
    except IndexError:
        title = bits[1].capitalize()
    return SortAnchorNode(bits[1].strip(), title.strip())

class SortAnchorNode(template.Node):
    """
    Renders an <a> HTML tag with a link which href attribute 
    includes the field on which we sort and the direction.
    and adds an up or down arrow if the field is the one 
    currently being sorted on.

    Eg.
        {% anchor "name" "Name" %} generates
        <a href="/the/current/path/?sort=name" title="Name">Name</a>

    """
    def __init__(self, field, title):
        self.field = template.Variable(field)
        self.title = template.Variable(title)

    def render(self, context):
        request = context['request']
        getvars = request.GET.copy()
        field = self.field.resolve(context)
        title = self.title.resolve(context)
        return self._render(context, request, getvars, field, title)

    def _render(self, context, request, getvars, field, title):
        if 'sort' in getvars:
            sortby = getvars['sort']
            del getvars['sort']
        else:
            sortby = ''
        if 'dir' in getvars:
            sortdir = getvars['dir']
            del getvars['dir']
        else:
            sortdir = ''
        if sortby == field:
            getvars['dir'] = sort_directions[sortdir]['inverse']
            icon = sort_directions[sortdir]['icon']
        else:
            icon = ''
        if len(getvars.keys()) > 0:
            urlappend = "&%s" % getvars.urlencode()
        else:
            urlappend = ''
        if icon:
            title_with_sort_ordering = "%s %s" % (title, icon)
        else:
            title_with_sort_ordering = title

        url = '%s?sort=%s%s' % (request.path, field, urlappend)
        return '<a href="%s" title="%s">%s</a>' % (url, title, title_with_sort_ordering)

def anchor(parser, token):
    """
    depreciated: will be removed in a later version
    
    Parses a tag that's supposed to be in this format: {% anchor field title %}    
    """
    bits = [b.strip('"\'') for b in token.split_contents()]
    if len(bits) < 2:
        raise TemplateSyntaxError, "anchor tag takes at least 1 argument"
    try:
        title = bits[2]
    except IndexError:
        title = bits[1].capitalize()
    return OldSortAnchorNode(bits[1].strip(), title.strip())
    

class OldSortAnchorNode(SortAnchorNode):
    """
    depreciated: will be removed in a later version
    
    Renders an <a> HTML tag with a link which href attribute 
    includes the field on which we sort and the direction.
    and adds an up or down arrow if the field is the one 
    currently being sorted on.

    Eg.
        {% anchor name Name %} generates
        <a href="/the/current/path/?sort=name" title="Name">Name</a>

    """
    def __init__(self, field, title):
        warnings.warn("django_sorting anchor is deprecated, use sort_anchor instead", DeprecationWarning)

        self.field = field
        self.title = title

    def render(self, context):
        request = context['request']
        getvars = request.GET.copy()
        return self._render(context, request, getvars, self.field, self.title)

def autosort(parser, token):
    bits = [b.strip('"\'') for b in token.split_contents()]
    if len(bits) != 2:
        raise TemplateSyntaxError, "autosort tag takes exactly one argument"
    return SortedDataNode(bits[1])

class SortedDataNode(template.Node):
    """
    Automatically sort a queryset with {% autosort queryset %}
    """
    def __init__(self, queryset_var, context_var=None):
        self.queryset_var = template.Variable(queryset_var)
        self.context_var = context_var

    def render(self, context):
        key = self.queryset_var.var
        value = self.queryset_var.resolve(context)
        order_by = context['request'].field
        if len(order_by) > 1:
            try:
                context[key] = value.order_by(order_by)
            except template.TemplateSyntaxError:
                if INVALID_FIELD_RAISES_404:
                    raise Http404('Invalid field sorting. If DEBUG were set to ' +
                    'False, an HTTP 404 page would have been shown instead.')
                context[key] = value
        else:
            context[key] = value

        return ''

anchor = register.tag(anchor)
sort_anchor = register.tag(sort_anchor)
autosort = register.tag(autosort)

