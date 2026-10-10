"""管理看板：在 InvenTree 儀表板的「新增小工具」抽屜加入四個管理用小工具。

- 各公司庫存總覽：A/B/C 公司並排比較庫存總量、品項數、低庫存與缺貨
- 跨公司調動與異常：近 N 小時別家公司或管理者調進／調出自家庫位、大量、歸零（取自通知服務）
- 今日異動摘要：今天各公司的入庫、出庫、調入、盤點筆數與操作人
- 呆滯庫存：超過 N 天沒有異動的庫存

資料都由瀏覽器以「使用者自己的權限」讀取 InvenTree API，外掛本身不修改任何資料。
公司清單讀取同資料夾的 companies.json（由 setup-server.ps1／enable-dashboard.ps1 依匯入設定產生）。
適用 InvenTree 1.5.6（UserInterfaceMixin 的 dashboard 功能）。
"""

import json
from pathlib import Path

from plugin import InvenTreePlugin
from plugin.mixins import SettingsMixin, UserInterfaceMixin

PLUGIN_VERSION = '1.0.0'

DEFAULT_COMPANIES = [
    {'name': 'A 公司', 'code': 'A'},
    {'name': 'B 公司', 'code': 'B'},
    {'name': 'C 公司', 'code': 'C'},
]

# key, 函式名稱, 標題, 說明, 圖示, 寬, 高
WIDGETS = [
    ('company-overview', 'renderCompanyOverview', '各公司庫存總覽',
     'A/B/C 公司並排：庫存總量、品項數、低庫存與缺貨數', 'ti:building-warehouse:outline', 6, 3),
    ('cross-company', 'renderCrossCompany', '跨公司調動與異常',
     '近期別家公司或管理者調進／調出自家庫位、大量與歸零操作（依你所屬公司）', 'ti:arrows-exchange:outline', 6, 4),
    ('today-activity', 'renderTodayActivity', '今日異動摘要',
     '今天各公司的入庫、出庫、調入、盤點筆數與操作人', 'ti:calendar-stats:outline', 6, 4),
    ('stagnant-stock', 'renderStagnantStock', '呆滯庫存',
     '超過設定天數沒有任何異動的庫存，方便出清或調撥', 'ti:hourglass:outline', 6, 4),
]


def load_companies(path=None):
    """讀取公司清單；檔案不存在或格式錯誤時使用預設的 A/B/C 公司。"""
    path = Path(path) if path else Path(__file__).with_name('companies.json')
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        items = data.get('companies', data) if isinstance(data, dict) else data
        out = [{'name': str(c['name']), 'code': str(c.get('code') or '')} for c in items if c.get('name')]
        return out or DEFAULT_COMPANIES
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return DEFAULT_COMPANIES


def build_items(static_file, companies, stagnant_days, alert_hours, notify_url='/notify/api/feed'):
    """組出儀表板小工具清單（與 InvenTree 無關的純函式，方便測試）。"""
    context = {
        'companies': companies,
        'stagnant_days': stagnant_days,
        'alert_hours': alert_hours,
        'notify_url': notify_url,
        'version': PLUGIN_VERSION,
    }
    return [
        {
            'key': key,
            'title': title,
            'description': desc,
            'icon': icon,
            'source': static_file(f'mgmt_dashboard.js:{fn}'),
            'context': dict(context),
            'options': {'width': w, 'height': h},
        }
        for key, fn, title, desc, icon, w, h in WIDGETS
    ]


def _positive_int(value, default):
    try:
        v = int(value)
        return v if v > 0 else default
    except (TypeError, ValueError):
        return default


class MgmtDashboardPlugin(SettingsMixin, UserInterfaceMixin, InvenTreePlugin):
    """管理看板儀表板小工具。"""

    NAME = 'MgmtDashboard'
    SLUG = 'mgmt-dashboard'
    TITLE = '管理看板'
    DESCRIPTION = '各公司庫存總覽、跨公司調動與異常、今日異動摘要、呆滯庫存'
    VERSION = PLUGIN_VERSION
    AUTHOR = 'crrer'

    SETTINGS = {
        'STAGNANT_DAYS': {
            'name': '呆滯天數',
            'description': '超過幾天沒有異動就列入「呆滯庫存」',
            'default': 60,
            'validator': int,
        },
        'ALERT_HOURS': {
            'name': '異常顯示時間（小時）',
            'description': '「跨公司調動與異常」顯示最近幾小時內的紀錄',
            'default': 24,
            'validator': int,
        },
    }

    def get_ui_dashboard_items(self, request, context, **kwargs):
        """回傳儀表板小工具；未登入時不提供。"""
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return []
        return build_items(
            self.plugin_static_file,
            load_companies(),
            _positive_int(self.get_setting('STAGNANT_DAYS'), 60),
            _positive_int(self.get_setting('ALERT_HOURS'), 24),
        )
