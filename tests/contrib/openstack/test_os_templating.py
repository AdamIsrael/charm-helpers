import jinja2
import os
import unittest
from mock import patch

import charmhelpers.contrib.openstack.templating as templating


class FakeContextGenerator(object):
    interfaces = None

    def set(self, interfaces, context):
        self.interfaces = interfaces
        self.context = context

    def __call__(self):
        return self.context


class FakeLoader(object):
    def set(self, template):
        self.template = template

    def get(self, name):
        return self.template


class TemplatingTests(unittest.TestCase):
    def setUp(self):
        path = os.path.dirname(__file__)
        self.renderer = templating.OSConfigRenderer(templates_dir=path,
                                                    openstack_release='folsom')
        self.loader = FakeLoader()
        self.context = FakeContextGenerator()

    def test_create_renderer_invalid_templates_dir(self):
        '''Ensure OSConfigRenderer checks templates_dir'''
        self.assertRaises(templating.OSConfigException,
                          templating.OSConfigRenderer,
                          templates_dir='/tmp/foooo0',
                          openstack_release='grizzly')

    def test_render_unregistered_config(self):
        '''Ensure cannot render an unregistered config file'''
        self.assertRaises(templating.OSConfigException,
                          self.renderer.render,
                          config_file='/tmp/foo')

    def test_write_unregistered_config(self):
        '''Ensure cannot write an unregistered config file'''
        self.assertRaises(templating.OSConfigException,
                          self.renderer.write,
                          config_file='/tmp/foo')

    @patch.object(templating, 'get_loader')
    def test_render_complete_context(self, loader):
        '''It renders a template when provided a complete context'''
        self.loader.set('{{ foo }}')
        self.context.set(interfaces=['fooservice'], context={'foo': 'bar'})
        loader.return_value = jinja2.FunctionLoader(self.loader.get)
        self.renderer.register('/tmp/foo', [self.context])
        result = self.renderer.render('/tmp/foo')
        self.assertEquals(result, 'bar')
        self.assertIn('fooservice', self.renderer.complete_contexts())

    @patch.object(templating, 'get_loader')
    def test_render_incomplete_context_with_template(self, loader):
        '''It renders a template when provided an incomplete context'''
        _tmp = '''
        {% if foo is defined %}
        {{ foo }}
        {% else %}
        Foo is not defined
        {% endif %}
        '''
        self.loader.set(_tmp)
        self.context.set(interfaces=['fooservice'], context={})
        loader.return_value = jinja2.FunctionLoader(self.loader.get)
        self.renderer.register('/tmp/foo', [self.context])
        result = self.renderer.render('/tmp/foo')
        self.assertTrue('Foo is not defined' in result)
        self.assertNotIn('fooservice', self.renderer.complete_contexts())

    @patch.object(templating, 'get_loader')
    def test_reset_template_loader_for_new_os_release(self, loader):
        self.loader.set('')
        self.context.set(interfaces=['fooservice'], context={})
        loader.return_value = jinja2.FunctionLoader(self.loader.get)
        self.renderer.register('/tmp/foo', [self.context])
        self.renderer.render('/tmp/foo')
        loader.assert_called_with(os.path.dirname(__file__), 'folsom')
        self.renderer.set_release(openstack_release='grizzly')
        self.renderer.render('/tmp/foo')
        loader.assert_called_with(os.path.dirname(__file__), 'grizzly')

    @patch.object(templating, 'get_loader')
    def test_incomplete_context_not_reported_complete(self, loader):
        '''It does not recognize an incomplete context as a complete context'''
        self.context.set(interfaces=['fooservice'], context={})
        loader.return_value = jinja2.FunctionLoader(self.loader.get)
        self.renderer.register('/tmp/foo', [self.context])
        self.assertNotIn('fooservice', self.renderer.complete_contexts())

    @patch.object(templating, 'get_loader')
    def test_complete_context_reported_complete(self, loader):
        '''It recognizes a complete context as a complete context'''
        self.context.set(interfaces=['fooservice'], context={'foo': 'bar'})
        self.renderer.register('/tmp/foo', [self.context])
        self.assertIn('fooservice', self.renderer.complete_contexts())

    @patch('os.path.isdir')
    def test_get_loader_no_templates_dir(self, isdir):
        '''Ensure getting loader fails with no template dir'''
        isdir.return_value = False
        self.assertRaises(templating.OSConfigException,
                          templating.get_loader,
                          templates_dir='/tmp/foo', os_release='foo')

    @patch('os.path.isdir')
    def test_get_loader_all_search_paths(self, isdir):
        '''Ensure loader reverse searches of all release template dirs'''
        isdir.return_value = True
        choice_loader = templating.get_loader('/tmp/foo',
                                              os_release='icehouse')
        dirs = [l.searchpath for l in choice_loader.loaders]

        common_tmplts = os.path.join(os.path.dirname(templating.__file__),
                                     'templates')
        expected = [['/tmp/foo/icehouse'],
                    ['/tmp/foo/havana'],
                    ['/tmp/foo/grizzly'],
                    ['/tmp/foo/folsom'],
                    ['/tmp/foo/essex'],
                    ['/tmp/foo'],
                    [common_tmplts]]
        self.assertEquals(dirs, expected)

    @patch('os.path.isdir')
    def test_get_loader_some_search_paths(self, isdir):
        '''Ensure loader reverse searches of some release template dirs'''
        isdir.return_value = True
        choice_loader = templating.get_loader('/tmp/foo', os_release='grizzly')
        dirs = [l.searchpath for l in choice_loader.loaders]

        common_tmplts = os.path.join(os.path.dirname(templating.__file__),
                                     'templates')

        expected = [['/tmp/foo/grizzly'],
                    ['/tmp/foo/folsom'],
                    ['/tmp/foo/essex'],
                    ['/tmp/foo'],
                    [common_tmplts]]
        self.assertEquals(dirs, expected)

    def test_register_template_with_list_of_contexts(self):
        '''Ensure registering a template with a list of context generators'''
        def _c1():
            pass

        def _c2():
            pass
        tmpl = templating.OSConfigTemplate(config_file='/tmp/foo',
                                           contexts=[_c1, _c2])
        self.assertEquals(tmpl.contexts, [_c1, _c2])

    def test_register_template_with_single_context(self):
        '''Ensure registering a template with a single non-list context'''
        def _c1():
            pass
        tmpl = templating.OSConfigTemplate(config_file='/tmp/foo',
                                           contexts=_c1)
        self.assertEquals(tmpl.contexts, [_c1])
