'''
Created on 23-Jun-2014

@author: rjoyce
'''

from lxml import etree

from jnpr.space import util
from jnpr.space import rest

class Collection(object):
    """Encapsulates a collection of Space Resources"""

    def __init__(self, parent, name, meta_object):
        self._parent = parent
        self._rest_end_point = parent._rest_end_point
        self._name = name
        self.meta_object = meta_object
        self._methods = {}

    def get_href(self):
        if self.meta_object.url:
            return self.meta_object.url
        else:
            return self._parent.get_href() + "/" + util.make_xml_name(self._name)

    def __getattr__(self, attr):
        if attr in self.meta_object.named_members:
            r = self._create_named_resource(attr,
                            self.meta_object.named_members[attr], None)
            r.id = attr
            return r

        if attr in self._methods:
            return self._methods[attr]

        method = self.meta_object.create_method(self, attr)
        if method is not None:
            self._methods[attr] = method
            return method

    def get(self, filter_=None, paging=None, sortby=None):
        url = self._form_get_url(filter_, paging, sortby)

        resource_list = []
        response = self._rest_end_point.get(url)
        if response.status_code != 200:
            if response.status_code == 204:
                return []
            raise rest.RestException("GET failed on %s" % url, response)

        # Fixing issue #17
        #r = response.text
        # Skip the <?xml> line to avoid encoding errors in lxml
        #start = r.index('?><') + 2
        #root = etree.fromstring(r[start:])

        root = etree.fromstring(response.content)

        if self.meta_object.single_object_collection:
            resource_list.append(self._create_resource(root))
        elif self.meta_object.named_members:
            for key, value in self.meta_object.named_members.iteritems():
                r = self._create_named_resource(key, value,root)
                r.id = key
                resource_list.append(r)
        else:
            for child in root:
                try:
                    r = self._create_resource(child)
                    resource_list.append(r)
                except Exception as e:
                    if e.ignore:
                        pass
                    else:
                        raise e

        return resource_list

    def _create_named_resource(self, key, meta_object, xml_root):
        type_name = meta_object['resource_type']
        xml_data = xml_root.find(meta_object['xml_name']) \
            if xml_root is not None else None
        from jnpr.space.resource import Resource
        return Resource(type_name=type_name,
                        rest_end_point=self._rest_end_point,
                        xml_data=xml_data,
                        parent=self)

    def _create_resource(self, xml_data):
        if self.meta_object.resource_type:
            from jnpr.space import resource
            return resource.Resource(type_name=self.meta_object.resource_type,
                                 rest_end_point=self._rest_end_point,
                                 xml_data=xml_data, parent=self)
        else:
            from jnpr.space import xmlutil
            s = etree.tostring(xml_data)
            return xmlutil.xml2obj(s)

    def post(self, new_obj, xml_name=None, content_type=None, accept=None):
        if content_type:
            media_type = content_type
        elif isinstance(new_obj, list):
            media_type = self.meta_object.media_type
        else:
            media_type = new_obj.get_meta_object().media_type

        headers = {'content-type': media_type}
        if accept:
            headers['accept'] = accept

        x = None
        if isinstance(new_obj, list):
            x = etree.Element(self._name)
            for o in new_obj:
                x.append(o.form_xml())
        else:
            x = new_obj.form_xml()

        saved_root_tag = x.tag

        if xml_name:
            x.tag = xml_name

        response = self._rest_end_point.post(self.get_href(),
                                             headers,
                                             etree.tostring(x))

        if response.status_code == 204: # Special case of post with null response
            return new_obj

        if response.status_code not in [200, 202]:
            raise rest.RestException("POST failed on %s" % self.get_href(),
                                     response)

        if not isinstance(new_obj, list):
            # Fixing issue #17
            #r = response.text
            # Skip the <?xml> line to avoid encoding errors in lxml
            #start = r.index('?><') + 2
            #root = etree.fromstring(r[start:])
            root = etree.fromstring(response.content)
            #new_obj._xml_data = root
            #new_obj._rest_end_point = self._rest_end_point
            root.tag = saved_root_tag
            new_obj = self._create_resource(root)

        return new_obj

    def _form_get_url(self, filter_, paging, sortby):
        url = self.get_href()

        f, p, s = None, None, None
        if filter_ is not None:
            f = self._stringify_filter(filter_)
        if paging is not None:
            p = self._stringify_paging(paging)
        if sortby is not None:
            s = self._stringify_sortby(sortby)

        if f is not None:
            url = '?'.join([url, f])
            if p is not None:
                url = '&'.join([url, p])
            if s is not None:
                url = '&'.join([url, s])
        elif p is not None:
            url = '?'.join([url, p])
            if s is not None:
                url = '&'.join([url, s])
        elif s is not None:
                url = '?'.join([url, s])

        return url

    def _stringify_filter(self, filter_):
        if isinstance(filter_, basestring):
            return ''.join(['filter=(', filter_, ')'])

        if isinstance(filter_, dict):
            filter_list = ['filter=(']
            index = 1
            for key, value in filter_.iteritems():
                if (index < len(filter_)):
                    filter_list.extend(["(", key, " eq '", str(value), "') and "])
                else:
                    filter_list.extend(["(", key, " eq '", str(value), "')"])
                index += 1
            filter_list.append(')')
            return ''.join(filter_list)

    def _stringify_paging(self, paging):
        start, limit = None, None
        if 'start' in paging:
            start = 'start eq %d' % paging['start']
        if 'limit' in paging:
            limit = 'limit eq %d' % paging['limit']

        if start and limit:
            pg_str = 'paging=(%s, %s)' % (start,limit)
        elif start:
            pg_str = 'paging=(%s)' % (start)
        elif limit:
            pg_str = 'paging=(%s)' % (limit)

        return pg_str

    def _stringify_sortby(self, field_list):
        return 'sortby=(%s)' % ','.join(field_list)

class MetaCollection(object):
    def __init__(self, key, values):
        self.key = key
        self.name = values['name'] \
            if ('name' in values) else None
        self.single_object_collection = values['single_object_collection'] \
            if ('single_object_collection' in values) else False
        self.xml_name = values['xml_name'] \
            if ('xml_name' in values) else None
        self.media_type = values['media_type'] \
            if ('media_type' in values) else None
        self.resource_type = values['resource_type'] \
            if ('resource_type' in values) else None
        self.url = values['url'] \
            if ('url' in values) else None
        self.named_members = values['named_members'] \
            if ('named_members' in values) else {}
        self.methods = values['methods'] \
            if ('methods' in values) else {}

    def create_method(self, service, name):
        if name in self.methods:
            from jnpr.space import method
            mObj = method.get_meta_object(service._name, name, self.methods[name])
            return method.Method(service, name, mObj)


_meta_collections = {}

def get_meta_object(coll_name, values):
    if coll_name in _meta_collections:
        return _meta_collections[coll_name]

    c = MetaCollection(coll_name, values)
    _meta_collections[coll_name] = c
    return c