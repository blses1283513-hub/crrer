"""5 個層級的權限表。純邏輯，不需要 ERPNext，可單獨測試。

兩層保護：
1. 妮菈的頁面與功能：依 CAPS（能力表）檢查；門市層級只能操作自己的門市。
2. ERPNext 原本的畫面（訂單、調撥單、盤點單、商品…）：每個層級帶一組 ERPNext 標準角色（BUNDLES），
   再加上 EXTRA_PERMS；成本欄位只有 COST_ROLES 看得到（其他層級在畫面與 API 都看不到）。
"""

ADMIN, MANAGER, HQ_STAFF, STORE_LEAD, STORE_STAFF = "妮菈管理員", "妮菈營運主管", "妮菈總公司作業", "妮菈門市店長", "妮菈門市店員"
LEVELS = [ADMIN, MANAGER, HQ_STAFF, STORE_LEAD, STORE_STAFF]
LEVEL_LABELS = {ADMIN: "1 管理員", MANAGER: "2 營運主管", HQ_STAFF: "3 總公司作業", STORE_LEAD: "4 門市店長", STORE_STAFF: "5 門市店員"}
STORE_LEVELS = {STORE_LEAD, STORE_STAFF}  # 只能看、只能操作自己的門市

ALL = set(LEVELS)
TOP = {ADMIN, MANAGER}
HQ = {ADMIN, MANAGER, HQ_STAFF}
CAPS = {
    # 門市與會員
    "store_sale": ALL,                         # 門市銷售
    "store_return": TOP | {STORE_LEAD},        # 退貨、退款
    "price_override": TOP | {STORE_LEAD},      # 單筆改價、打折
    "member": ALL,                             # 會員查詢、新增
    "member_merge": TOP,                       # 合併會員
    "sales_report": TOP | {STORE_LEAD},        # 消費報表
    "barcode": HQ | {STORE_LEAD},              # 條碼
    # 庫存、補貨、調度
    "stock_view": ALL,                         # 庫存表（門市層級只看自己的門市）
    "stock_history": ALL,                      # 庫存異動明細（只有數量）
    "replenish_view": HQ,                      # 補貨建議
    "replenish_manage": TOP,                   # 建立補貨單、叫貨
    "transfer_create": HQ,                     # 建立調撥單
    "transfer_receive": HQ | {STORE_LEAD},     # 到貨入庫（門市店長只能收自己門市的貨）
    "dispatch": HQ,                            # 訂單畫面的調度面板
    # 商品、成本、抽獎、帳號
    "item_manage": TOP,                        # 新增款式、匯入匯出、改售價
    "cost_view": TOP,                          # 看成本與進價
    "lottery": TOP,                            # 抽獎活動
    "accounts": {ADMIN},                       # 帳號管理
}

# 每個層級帶的 ERPNext 標準角色（讓 ERPNext 原本的畫面能用；成本另外用欄位權限擋）
BUNDLES = {
    ADMIN: ["System Manager", "Stock Manager", "Item Manager", "Sales Manager", "Purchase Manager", "Accounts Manager",
            "Stock User", "Sales User", "Purchase User", "Accounts User"],
    MANAGER: ["Stock Manager", "Item Manager", "Sales Manager", "Purchase Manager", "Stock User", "Sales User",
              "Purchase User", "Accounts User"],
    HQ_STAFF: ["Stock User", "Sales User"],
    STORE_LEAD: ["Stock User"],
    STORE_STAFF: [],
}
STANDARD_ROLES = sorted({r for rs in BUNDLES.values() for r in rs})

# ERPNext 原本沒有給、但層級需要的單據權限：(單據, 角色, [權限])
EXTRA_PERMS = [
    ("Stock Reconciliation", HQ_STAFF, ["read", "write", "create", "submit"]),   # 盤點
    ("Stock Reconciliation", STORE_LEAD, ["read", "write", "create", "submit"]),
    ("Sales Invoice", STORE_LEAD, ["read"]),                                       # 看自己門市的銷售單
]

# 成本、進價欄位：只有這些角色看得到（欄位權限層級 1）
COST_ROLES = ["System Manager", "Stock Manager", "Item Manager", "Purchase Manager", "Accounts Manager", "Accounts User",
              ADMIN, MANAGER]
COST_FIELDS = {
    "Item": [("Item", "valuation_rate"), ("Item", "last_purchase_rate"), ("Item", "nila_cost")],
    "Stock Entry": [("Stock Entry", "total_incoming_value"), ("Stock Entry", "total_outgoing_value"),
                    ("Stock Entry", "value_difference"), ("Stock Entry", "total_additional_costs"),
                    ("Stock Entry Detail", "basic_rate"), ("Stock Entry Detail", "basic_amount"),
                    ("Stock Entry Detail", "valuation_rate"), ("Stock Entry Detail", "amount"),
                    ("Stock Entry Detail", "additional_cost")],
    "Stock Reconciliation": [("Stock Reconciliation", "difference_amount"),
                             ("Stock Reconciliation Item", "valuation_rate"), ("Stock Reconciliation Item", "amount"),
                             ("Stock Reconciliation Item", "current_valuation_rate"), ("Stock Reconciliation Item", "current_amount"),
                             ("Stock Reconciliation Item", "amount_difference")],
    "Sales Order": [("Sales Order Item", "valuation_rate"), ("Sales Order Item", "gross_profit")],
    "Delivery Note": [("Delivery Note Item", "incoming_rate")],
    "Sales Invoice": [("Sales Invoice Item", "incoming_rate")],
}
# ERPNext 庫存報表大多顯示金額（成本）：只有能看成本的層級可以開；數量用「庫存表」與「異動明細」
OPEN_STOCK_REPORTS = {"Stock Projected Qty"}


def has_cap(cap, roles, user=None):
    """roles：使用者的角色。Administrator 與 System Manager（系統最高權限）一律可以。"""
    roles = set(roles or ())
    if user == "Administrator" or "System Manager" in roles:
        return True
    return bool(CAPS[cap] & roles)


def store_scoped(roles, user=None):
    """只有門市層級（店長、店員）、又沒有更高層級的帳號，才限定在自己的門市。"""
    roles = set(roles or ())
    if user == "Administrator" or "System Manager" in roles or roles & HQ:
        return False
    return bool(roles & STORE_LEVELS)


def level_of(roles):
    """帳號目前的層級（有多個時取最高）；沒有妮菈層級回傳 None。"""
    roles = set(roles or ())
    return next((lv for lv in LEVELS if lv in roles), None)


def plan_roles(level, current):
    """改成某個層級時，要加上與要移除的角色。只動妮菈層級與 BUNDLES 裡的標準角色，其他角色保留。"""
    want = {level, *BUNDLES[level]}
    managed = set(LEVELS) | set(STANDARD_ROLES)
    current = set(current or ())
    return sorted(want - current), sorted((current & managed) - want)


def check_account(data, stores, existing_usernames=()):
    """檢查帳號資料：姓名、帳號（英數字，開頭英文）、層級、門市（門市層級至少一間）。回傳錯誤清單。"""
    import re

    errors = []
    if not str(data.get("full_name") or "").strip():
        errors.append("姓名必填")
    username = str(data.get("username") or "").strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9._-]{2,29}", username):
        errors.append("帳號必須是 3–30 個英文小寫、數字或 . _ -，第一個字是英文")
    elif username in existing_usernames:
        errors.append(f"帳號 {username} 已經有人使用")
    level = data.get("level")
    if level not in LEVELS:
        errors.append("請選擇層級")
    chosen = list(data.get("stores") or [])
    bad = [s for s in chosen if s not in stores]
    if bad:
        errors.append("沒有這些門市：" + "、".join(bad))
    if level in STORE_LEVELS and not chosen:
        errors.append("門市店長、店員至少要選一間門市")
    return errors
