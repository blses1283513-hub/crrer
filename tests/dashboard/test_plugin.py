"""管理看板外掛（inventree-app/plugins/mgmt_dashboard）的伺服器端測試。

不需要 InvenTree：以最小的替身模組取代 plugin / plugin.mixins，驗證外掛回傳給
InvenTree 1.5.6 的儀表板小工具清單格式（key、title、source、options、context）。
"""

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parents[2] / 'inventree-app' / 'plugins' / 'mgmt_dashboard'


def load_plugin_module():
    """以替身 plugin 套件載入外掛（與 InvenTree 1.5.6 的匯入路徑相同）。"""
    class InvenTreePlugin:
        NAME = ''

    class SettingsMixin:
        def get_setting(self, key):
            return self._settings.get(key, self.SETTINGS[key]['default'])

    class UserInterfaceMixin:
        pass

    plugin = types.ModuleType('plugin')
    plugin.InvenTreePlugin = InvenTreePlugin
    mixins = types.ModuleType('plugin.mixins')
    mixins.SettingsMixin = SettingsMixin
    mixins.UserInterfaceMixin = UserInterfaceMixin
    saved = {k: sys.modules.get(k) for k in ('plugin', 'plugin.mixins')}
    sys.modules['plugin'] = plugin
    sys.modules['plugin.mixins'] = mixins
    try:
        spec = importlib.util.spec_from_file_location('mgmt_dashboard_under_test', PLUGIN_DIR / '__init__.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


M = load_plugin_module()


class User:
    def __init__(self, auth=True):
        self.is_authenticated = auth


class Request:
    def __init__(self, auth=True):
        self.user = User(auth)


def make_plugin(settings=None):
    p = M.MgmtDashboardPlugin()
    p._settings = settings or {}
    p.plugin_static_file = lambda name: f'/static/plugins/mgmt-dashboard/{name}'
    return p


class TestPluginMeta(unittest.TestCase):
    def test_identity(self):
        self.assertEqual(M.MgmtDashboardPlugin.SLUG, 'mgmt-dashboard')
        self.assertTrue(M.MgmtDashboardPlugin.NAME)
        self.assertEqual(M.MgmtDashboardPlugin.VERSION, M.PLUGIN_VERSION)

    def test_static_file_exists_with_all_entrypoints(self):
        js = (PLUGIN_DIR / 'static' / 'mgmt_dashboard.js').read_text(encoding='utf-8')
        for _key, fn, *_rest in M.WIDGETS:
            self.assertIn(f'export function {fn}(target, ctx)', js)

    def test_settings_have_chinese_names_and_int_validators(self):
        for key in ('STAGNANT_DAYS', 'ALERT_HOURS'):
            s = M.MgmtDashboardPlugin.SETTINGS[key]
            self.assertIs(s['validator'], int)
            self.assertRegex(s['name'], r'[一-鿿]')


class TestDashboardItems(unittest.TestCase):
    def test_four_widgets_with_required_fields(self):
        items = make_plugin().get_ui_dashboard_items(Request(), {})
        self.assertEqual([i['key'] for i in items], ['company-overview', 'cross-company', 'today-activity', 'stagnant-stock'])
        for i in items:
            for field in ('key', 'title', 'description', 'source', 'options', 'context'):
                self.assertIn(field, i)
            self.assertRegex(i['title'], r'[一-鿿]', '標題要是中文')
            self.assertRegex(i['source'], r'^/static/plugins/mgmt-dashboard/mgmt_dashboard\.js:render\w+$')
            self.assertGreaterEqual(i['options']['width'], 2)
            self.assertGreaterEqual(i['options']['height'], 2)
            json.dumps(i)   # 必須能轉成 JSON（API 回應）

    def test_context_defaults(self):
        ctx = make_plugin().get_ui_dashboard_items(Request(), {})[0]['context']
        self.assertEqual(ctx['stagnant_days'], 60)
        self.assertEqual(ctx['alert_hours'], 24)
        self.assertEqual(ctx['notify_url'], '/notify/api/feed')
        self.assertEqual([c['code'] for c in ctx['companies']], ['A', 'B', 'C'])

    def test_settings_flow_into_context_and_bad_values_fall_back(self):
        ctx = make_plugin({'STAGNANT_DAYS': 90, 'ALERT_HOURS': '48'}).get_ui_dashboard_items(Request(), {})[0]['context']
        self.assertEqual((ctx['stagnant_days'], ctx['alert_hours']), (90, 48))
        ctx = make_plugin({'STAGNANT_DAYS': 0, 'ALERT_HOURS': 'x'}).get_ui_dashboard_items(Request(), {})[0]['context']
        self.assertEqual((ctx['stagnant_days'], ctx['alert_hours']), (60, 24))

    def test_context_not_shared_between_items(self):
        items = make_plugin().get_ui_dashboard_items(Request(), {})
        items[0]['context']['stagnant_days'] = 1
        self.assertEqual(items[1]['context']['stagnant_days'], 60)

    def test_anonymous_gets_nothing(self):
        self.assertEqual(make_plugin().get_ui_dashboard_items(Request(auth=False), {}), [])
        self.assertEqual(make_plugin().get_ui_dashboard_items(types.SimpleNamespace(), {}), [])


class TestCompanies(unittest.TestCase):
    def write(self, text, encoding='utf-8'):
        d = tempfile.mkdtemp()
        p = Path(d) / 'companies.json'
        p.write_bytes(text.encode(encoding))
        return p

    def test_reads_list_or_object_and_bom(self):
        data = [{'name': '甲公司', 'code': 'X'}, {'name': '乙公司', 'code': 'Y', 'owner_group': 'g'}]
        self.assertEqual(M.load_companies(self.write(json.dumps(data))), [{'name': '甲公司', 'code': 'X'}, {'name': '乙公司', 'code': 'Y'}])
        self.assertEqual(M.load_companies(self.write(json.dumps({'companies': data}), 'utf-8-sig'))[0]['name'], '甲公司')

    def test_missing_or_broken_file_uses_defaults(self):
        self.assertEqual(M.load_companies(Path(tempfile.mkdtemp()) / 'none.json'), M.DEFAULT_COMPANIES)
        self.assertEqual(M.load_companies(self.write('{oops')), M.DEFAULT_COMPANIES)
        self.assertEqual(M.load_companies(self.write('[]')), M.DEFAULT_COMPANIES)
        self.assertEqual(M.load_companies(self.write('[{"code": "A"}]')), M.DEFAULT_COMPANIES)


if __name__ == '__main__':
    unittest.main()
