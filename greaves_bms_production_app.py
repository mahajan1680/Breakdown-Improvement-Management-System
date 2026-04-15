import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import secrets
from datetime import datetime, time, timedelta
from streamlit_autorefresh import st_autorefresh

# =====================================================
# GREAVES COTTON - BREAKDOWN & IMPROVEMENT MANAGEMENT
# Standard Level Streamlit App
# =====================================================

st.set_page_config(page_title="Greaves Cotton BMS", layout="wide")

DB_FILE = "greaves_bms_standard.db"
AUTO_REFRESH_MS = 30000
SESSION_TIMEOUT_MINUTES = 30
MAX_LOGIN_ATTEMPTS = 3

ROLE_ADMIN = "Admin"
ROLE_PLANT_HEAD = "Plant Head"
ROLE_HOD = "HOD"
ROLE_MANAGER = "Manager"
ROLE_USER = "User"

ENTRY_BREAKDOWN = "Breakdown"
ENTRY_IMPROVEMENT = "Improvement"

SERVICE_MAINT = "Maintenance"
SERVICE_TOOLROOM = "Tool Room"

PRODUCTION = "Production"
SERVICE = "Service"

# -------------------------
# CSS
# -------------------------
def inject_css():
    st.markdown(
        """
        <style>
            .main {
                background: linear-gradient(180deg, #f3f8f4 0%, #edf5ee 100%);
            }
            .block-container {
                padding-top: 1rem;
                padding-bottom: 2rem;
            }
            .top-banner {
                background: linear-gradient(135deg, #0b5d3f 0%, #198754 45%, #2f9b6c 100%);
                border-radius: 18px;
                padding: 18px 22px;
                color: white;
                box-shadow: 0 8px 24px rgba(0,0,0,0.12);
                margin-bottom: 16px;
            }
            .top-title {
                font-size: 30px;
                font-weight: 800;
                margin-bottom: 4px;
            }
            .top-sub {
                font-size: 14px;
                opacity: 0.96;
            }
            .welcome-chip {
                display: inline-block;
                background: rgba(255,255,255,0.16);
                padding: 8px 12px;
                border-radius: 12px;
                font-weight: 700;
                margin-bottom: 10px;
            }
            .metric-box {
                background: white;
                border-radius: 18px;
                padding: 16px;
                box-shadow: 0 6px 18px rgba(0,0,0,0.08);
                border-left: 6px solid #198754;
                min-height: 110px;
            }
            .metric-label {
                color: #62756b;
                font-size: 13px;
                margin-bottom: 6px;
            }
            .metric-value {
                font-size: 30px;
                font-weight: 800;
                color: #163c2d;
            }
            .card-red {
                background: linear-gradient(135deg, #fff5f5 0%, #ffe3e3 100%);
                border-left: 8px solid #dc3545;
                border-radius: 16px;
                padding: 16px;
                margin-bottom: 12px;
                box-shadow: 0 6px 16px rgba(220,53,69,0.16);
                animation: blinkRed 1.2s infinite;
            }
            .card-yellow {
                background: linear-gradient(135deg, #fff9e8 0%, #fff3cd 100%);
                border-left: 8px solid #ffc107;
                border-radius: 16px;
                padding: 16px;
                margin-bottom: 12px;
                box-shadow: 0 6px 16px rgba(255,193,7,0.15);
            }
            .card-green {
                background: linear-gradient(135deg, #f3fff6 0%, #dcfce7 100%);
                border-left: 8px solid #198754;
                border-radius: 16px;
                padding: 16px;
                margin-bottom: 12px;
                box-shadow: 0 6px 16px rgba(25,135,84,0.12);
            }
            .panel {
                background: white;
                border-radius: 18px;
                padding: 16px;
                box-shadow: 0 6px 18px rgba(0,0,0,0.08);
                margin-bottom: 14px;
            }
            .login-box {
                background: white;
                padding: 24px;
                border-radius: 18px;
                box-shadow: 0 10px 24px rgba(0,0,0,0.10);
                border-top: 6px solid #198754;
            }
            @keyframes blinkRed {
                0% { opacity: 1; box-shadow: 0 0 0 rgba(220,53,69,0.10); }
                50% { opacity: 0.90; box-shadow: 0 0 24px rgba(220,53,69,0.35); }
                100% { opacity: 1; box-shadow: 0 0 0 rgba(220,53,69,0.10); }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

# -------------------------
# DB
# -------------------------
def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

conn = get_connection()


def execute_query(query, params=(), fetch=False):
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    if fetch:
        return cur.fetchall()
    return None


def safe_df(query, params=()):
    return pd.read_sql_query(query, conn, params=params)


def table_columns(table_name):
    cols = execute_query(f"PRAGMA table_info({table_name})", fetch=True)
    return [x[1] for x in cols]


def ensure_column(table_name, column_name, column_type):
    if column_name not in table_columns(table_name):
        execute_query(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def init_db():
    execute_query(
        """
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dept_name TEXT UNIQUE NOT NULL,
            dept_type TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT NOT NULL,
            parent_hod TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_name TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL,
            created_by TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_no TEXT UNIQUE NOT NULL,
            line_name TEXT NOT NULL,
            department TEXT NOT NULL,
            created_by TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    execute_query(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_type TEXT NOT NULL,
            source_department TEXT NOT NULL,
            target_department TEXT NOT NULL,
            line_name TEXT NOT NULL,
            machine_no TEXT NOT NULL,
            problem_text TEXT NOT NULL,
            planned_date TEXT,
            priority_label TEXT,
            status_color TEXT NOT NULL,
            status_text TEXT NOT NULL,
            raised_by_name TEXT NOT NULL,
            raised_by_username TEXT NOT NULL,
            raised_by_role TEXT NOT NULL,
            shift_name TEXT NOT NULL,
            raised_time TIMESTAMP NOT NULL,
            photo_name TEXT,
            photo_bytes BLOB,
            action_taken TEXT,
            closed_by_name TEXT,
            closed_by_username TEXT,
            closed_by_role TEXT,
            closed_time TIMESTAMP,
            downtime_mins REAL,
            active_shift_tag TEXT,
            is_shift_hidden INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    ensure_column("tickets", "priority_label", "TEXT")
    ensure_column("tickets", "active_shift_tag", "TEXT")
    ensure_column("tickets", "is_shift_hidden", "INTEGER DEFAULT 0")

    default_departments = [
        ("Machine Shop", PRODUCTION),
        ("Assembly", PRODUCTION),
        ("Testing", PRODUCTION),
        (SERVICE_MAINT, SERVICE),
        (SERVICE_TOOLROOM, SERVICE),
    ]

    for dept_name, dept_type in default_departments:
        existing = execute_query("SELECT id FROM departments WHERE dept_name=?", (dept_name,), fetch=True)
        if not existing:
            execute_query(
                "INSERT INTO departments (dept_name, dept_type) VALUES (?,?)",
                (dept_name, dept_type),
            )

    existing_admin = execute_query("SELECT id FROM users WHERE username='admin'", fetch=True)
    if not existing_admin:
        execute_query(
            "INSERT INTO users (full_name, username, password, role, department, parent_hod) VALUES (?,?,?,?,?,?)",
            (
                "System Admin",
                "admin",
                hash_password("admin123"),
                ROLE_ADMIN,
                "All",
                None,
            ),
        )

# -------------------------
# SECURITY
# -------------------------
def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{digest}:{salt}"


def verify_password(stored_password, provided_password):
    try:
        digest, salt = stored_password.split(":")
        new_digest = hashlib.sha256((provided_password + salt).encode()).hexdigest()
        return new_digest == digest
    except Exception:
        return False

# -------------------------
# SESSION
# -------------------------
def init_state():
    if "user" not in st.session_state:
        st.session_state.user = None
    if "last_activity" not in st.session_state:
        st.session_state.last_activity = datetime.now()
    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = 0


def touch_session():
    st.session_state.last_activity = datetime.now()


def logout():
    st.session_state.user = None
    st.session_state.last_activity = datetime.now()


def session_guard():
    if st.session_state.user:
        if datetime.now() - st.session_state.last_activity > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
            st.warning("Session expired. Please login again.")
            logout()
            st.rerun()

# -------------------------
# HELPERS
# -------------------------
def current_user():
    return st.session_state.user


def get_shift(dt=None):
    dt = dt or datetime.now()
    tm = dt.time()
    if time(6, 30) <= tm < time(15, 0):
        return "First"
    elif time(15, 0) <= tm < time(23, 30):
        return "Second"
    return "Night"


def active_shift_tag():
    now = datetime.now()
    return f"{now.strftime('%Y-%m-%d')}_{get_shift(now)}"


def hide_old_green_items():
    current_tag = active_shift_tag()
    execute_query(
        """
        UPDATE tickets
        SET is_shift_hidden=1
        WHERE status_color='GREEN' AND active_shift_tag IS NOT NULL AND active_shift_tag != ?
        """,
        (current_tag,),
    )


def user_is_admin():
    return current_user()["role"] == ROLE_ADMIN


def user_is_plant_head():
    return current_user()["role"] == ROLE_PLANT_HEAD


def user_is_hod():
    return current_user()["role"] == ROLE_HOD


def user_is_manager():
    return current_user()["role"] == ROLE_MANAGER


def user_is_user():
    return current_user()["role"] == ROLE_USER


def render_header(title, subtitle):
    user = current_user()
    welcome_name = user["full_name"] if user else "Guest"
    st.markdown(
        f"""
        <div class='top-banner'>
            <div class='welcome-chip'>Welcome, {welcome_name}</div>
            <div class='top-title'>🏭 Greaves Cotton Limited</div>
            <div style='font-size:22px;font-weight:700;margin-top:4px;'>{title}</div>
            <div class='top-sub'>{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_box(label, value, note=""):
    st.markdown(
        f"""
        <div class='metric-box'>
            <div class='metric-label'>{label}</div>
            <div class='metric-value'>{value}</div>
            <div class='metric-label'>{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_department_df(prod_only=False, service_only=False):
    query = "SELECT dept_name, dept_type FROM departments WHERE is_active=1"
    params = []
    if prod_only:
        query += " AND dept_type=?"
        params.append(PRODUCTION)
    if service_only:
        query += " AND dept_type=?"
        params.append(SERVICE)
    query += " ORDER BY dept_name"
    return safe_df(query, params)


def get_production_departments():
    return get_department_df(prod_only=True)


def get_service_departments():
    return pd.DataFrame({"dept_name": [SERVICE_MAINT, SERVICE_TOOLROOM]})


def allowed_asset_access_department():
    user = current_user()
    if user["role"] in [ROLE_ADMIN, ROLE_PLANT_HEAD]:
        return None
    return user["department"]


def can_manage_users():
    return current_user()["role"] in [ROLE_ADMIN, ROLE_HOD]


def can_manage_assets_for_department(dept_name):
    user = current_user()
    if user["role"] in [ROLE_ADMIN, ROLE_PLANT_HEAD]:
        dept_df = safe_df("SELECT dept_type FROM departments WHERE dept_name=?", (dept_name,))
        if dept_df.empty:
            return False
        return dept_df.iloc[0]["dept_type"] == PRODUCTION
    if user["role"] in [ROLE_HOD, ROLE_MANAGER]:
        if user["department"] != dept_name:
            return False
        dept_df = safe_df("SELECT dept_type FROM departments WHERE dept_name=?", (dept_name,))
        if dept_df.empty:
            return False
        return dept_df.iloc[0]["dept_type"] == PRODUCTION
    return False


def can_close_ticket(row):
    user = current_user()
    if user["role"] in [ROLE_ADMIN, ROLE_PLANT_HEAD]:
        return True
    if user["department"] == row["target_department"]:
        return user["role"] in [ROLE_HOD, ROLE_MANAGER, ROLE_USER]
    if user["department"] == row["source_department"] and user["role"] == ROLE_MANAGER:
        return True
    return False


def visible_tickets_df(include_hidden=False):
    user = current_user()
    query = "SELECT * FROM tickets WHERE 1=1"
    params = []

    if not include_hidden:
        query += " AND is_shift_hidden=0"

    if user["role"] in [ROLE_ADMIN, ROLE_PLANT_HEAD]:
        pass
    else:
        query += " AND (source_department=? OR target_department=?)"
        params.extend([user["department"], user["department"]])

    query += " ORDER BY raised_time DESC"
    return safe_df(query, params)

# -------------------------
# LOGIN
# -------------------------
def login_screen():
    st.markdown(
        """
        <div class='top-banner'>
            <div class='welcome-chip'>GREAVES</div>
            <div class='top-title'>🏭 Greaves Cotton Limited</div>
            <div style='font-size:22px;font-weight:700;margin-top:4px;'>Breakdown & Improvement Management System</div>
            <div class='top-sub'>Desktop-first • Mobile responsive • Role based secure access</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1, 1.1, 1])
    with c2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.subheader("🔐 Secure Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            if submit:
                if st.session_state.login_attempts >= MAX_LOGIN_ATTEMPTS:
                    st.error("Too many attempts. Contact admin.")
                    st.stop()
                row = execute_query(
                    "SELECT full_name, username, password, role, department, parent_hod FROM users WHERE username=? AND is_active=1",
                    (username.strip(),),
                    fetch=True,
                )
                if row and verify_password(row[0]["password"], password):
                    st.session_state.user = {
                        "full_name": row[0]["full_name"],
                        "username": row[0]["username"],
                        "role": row[0]["role"],
                        "department": row[0]["department"],
                        "parent_hod": row[0]["parent_hod"],
                    }
                    st.session_state.login_attempts = 0
                    touch_session()
                    st.success(f"Welcome {row[0]['full_name']}")
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    st.error("Invalid username or password")
        st.markdown("</div>", unsafe_allow_html=True)
        

# -------------------------
# SIDEBAR
# -------------------------
def sidebar_menu():
    user = current_user()
    st.sidebar.markdown(f"## 👋 {user['full_name']}")
    st.sidebar.info(
        f"Role: {user['role']}\n\nDepartment: {user['department']}\n\nShift: {get_shift()}"
    )

    menu = ["Dashboard", "Raise Breakdown/Improvement", "Reports"]

    if can_manage_assets_for_department(user["department"]) or user["role"] in [ROLE_ADMIN, ROLE_PLANT_HEAD]:
        menu.append("Asset Master")

    if can_manage_users() or user_is_admin():
        menu.append("User Management")

    if user_is_admin():
        menu.append("Department Management")

    if st.sidebar.button("Logout"):
        logout()
        st.rerun()

    return st.sidebar.radio("Navigation", menu)

# -------------------------
# DEPARTMENT MANAGEMENT
# -------------------------
def department_management_page():
    render_header("Department Management", "Admin can add departments and keep the structure ready")
    if not user_is_admin():
        st.error("Only admin can access this page.")
        return

    t1, t2 = st.tabs(["Add Department", "Department List"])

    with t1:
        with st.form("add_dept"):
            dept_name = st.text_input("Department Name")
            dept_type = st.selectbox("Department Type", [PRODUCTION, SERVICE])
            submit = st.form_submit_button("Add Department")
            if submit:
                if not dept_name.strip():
                    st.error("Department name is required.")
                else:
                    try:
                        execute_query(
                            "INSERT INTO departments (dept_name, dept_type) VALUES (?,?)",
                            (dept_name.strip(), dept_type),
                        )
                        st.success("Department added successfully.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Department already exists.")

    with t2:
        df = safe_df("SELECT * FROM departments ORDER BY dept_name")
        st.dataframe(df, use_container_width=True, hide_index=True)

# -------------------------
# USER MANAGEMENT
# -------------------------
def user_management_page():
    render_header("User Management", "Admin creates HOD/Plant Head. HOD creates Manager/User.")
    user = current_user()
    if not can_manage_users() and not user_is_admin():
        st.error("No access.")
        return

    t1, t2 = st.tabs(["Create User", "User List"])

    with t1:
        with st.form("create_user_form"):
            full_name = st.text_input("Full Name")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")

            if user_is_admin():
                role = st.selectbox("Role", [ROLE_PLANT_HEAD, ROLE_HOD])
                dept_df = get_department_df()
                department = st.selectbox("Department", ["All"] + dept_df["dept_name"].tolist())
                if role == ROLE_HOD and department == "All":
                    st.warning("HOD साठी production/service department select करा.")
                parent_hod = None
            else:
                role = st.selectbox("Role", [ROLE_MANAGER, ROLE_USER])
                department = user["department"]
                st.text_input("Department", value=department, disabled=True)
                parent_hod = user["username"]

            submit = st.form_submit_button("Create User")
            if submit:
                if not full_name.strip() or not username.strip() or not password.strip():
                    st.error("All fields are required.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters.")
                elif user_is_admin() and role == ROLE_HOD and department == "All":
                    st.error("HOD साठी valid department select करा.")
                else:
                    try:
                        execute_query(
                            "INSERT INTO users (full_name, username, password, role, department, parent_hod) VALUES (?,?,?,?,?,?)",
                            (
                                full_name.strip(),
                                username.strip(),
                                hash_password(password),
                                role,
                                department,
                                parent_hod,
                            ),
                        )
                        st.success("User created successfully.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Username already exists.")

    with t2:
        if user_is_admin():
            df = safe_df("SELECT id, full_name, username, role, department, parent_hod, is_active, created_at FROM users ORDER BY id DESC")
        else:
            df = safe_df(
                "SELECT id, full_name, username, role, department, parent_hod, is_active, created_at FROM users WHERE department=? ORDER BY id DESC",
                (user["department"],),
            )
        st.dataframe(df, use_container_width=True, hide_index=True)

        if not df.empty:
            selected_id = st.selectbox("Select User ID", df["id"].tolist())
            action = st.selectbox("Action", ["Activate", "Deactivate"])
            if st.button("Apply User Status"):
                val = 1 if action == "Activate" else 0
                execute_query("UPDATE users SET is_active=? WHERE id=?", (val, int(selected_id)))
                st.success("User status updated.")
                st.rerun()

# -------------------------
# ASSET MASTER
# -------------------------
def asset_master_page():
    render_header("Asset Master", "Production departments can manage lines and machines")
    user = current_user()

    allowed_dept = allowed_asset_access_department()

    t1, t2, t3, t4 = st.tabs(["Add Line", "Add Machine", "Edit Line", "Edit Machine"])

    with t1:
        with st.form("add_line_form"):
            if user["role"] in [ROLE_ADMIN, ROLE_PLANT_HEAD]:
                prod_df = get_production_departments()
                dept = st.selectbox("Production Department", prod_df["dept_name"].tolist()) if not prod_df.empty else None
            else:
                dept = user["department"]
                st.text_input("Production Department", value=dept, disabled=True)

            valid_access = dept is not None and can_manage_assets_for_department(dept)
            line_name = st.text_input("Line Name")
            submit = st.form_submit_button("Add Line")
            if submit:
                if not valid_access:
                    st.error("This department cannot manage assets.")
                elif not line_name.strip():
                    st.error("Line name is required.")
                else:
                    try:
                        execute_query(
                            "INSERT INTO lines (line_name, department, created_by) VALUES (?,?,?)",
                            (line_name.strip(), dept, user["username"]),
                        )
                        st.success("Line added successfully.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Line name already exists.")

    with t2:
        if user["role"] in [ROLE_ADMIN, ROLE_PLANT_HEAD]:
            lines_df = safe_df("SELECT id, line_name, department FROM lines WHERE is_active=1 ORDER BY department, line_name")
        else:
            lines_df = safe_df(
                "SELECT id, line_name, department FROM lines WHERE is_active=1 AND department=? ORDER BY line_name",
                (allowed_dept,),
            )
        if lines_df.empty:
            st.warning("Please add a line first.")
        else:
            with st.form("add_machine_form"):
                line_options = [f"{r['line_name']} | {r['department']}" for _, r in lines_df.iterrows()]
                line_combo = st.selectbox("Select Line", line_options)
                line_name, department = [x.strip() for x in line_combo.split("|")]
                machine_no = st.text_input("Machine Number")
                submit = st.form_submit_button("Add Machine")
                if submit:
                    if not can_manage_assets_for_department(department):
                        st.error("This department cannot manage assets.")
                    elif not machine_no.strip():
                        st.error("Machine number is required.")
                    else:
                        try:
                            execute_query(
                                "INSERT INTO machines (machine_no, line_name, department, created_by) VALUES (?,?,?,?)",
                                (machine_no.strip(), line_name, department, user["username"]),
                            )
                            st.success("Machine added successfully.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Machine number already exists.")

    with t3:
        if user["role"] in [ROLE_ADMIN, ROLE_PLANT_HEAD]:
            line_df = safe_df("SELECT id, line_name, department FROM lines WHERE is_active=1 ORDER BY department, line_name")
        else:
            line_df = safe_df(
                "SELECT id, line_name, department FROM lines WHERE is_active=1 AND department=? ORDER BY line_name",
                (allowed_dept,),
            )
        if line_df.empty:
            st.info("No lines available.")
        else:
            selected_id = st.selectbox("Select Line ID", line_df["id"].tolist())
            row = line_df[line_df["id"] == selected_id].iloc[0]
            new_name = st.text_input("New Line Name", value=row["line_name"])
            if st.button("Update Line"):
                if can_manage_assets_for_department(row["department"]):
                    execute_query("UPDATE lines SET line_name=? WHERE id=?", (new_name.strip(), int(selected_id)))
                    execute_query("UPDATE machines SET line_name=? WHERE line_name=?", (new_name.strip(), row["line_name"]))
                    execute_query("UPDATE tickets SET line_name=? WHERE line_name=?", (new_name.strip(), row["line_name"]))
                    st.success("Line updated successfully.")
                    st.rerun()
                else:
                    st.error("No access to edit this line.")

    with t4:
        if user["role"] in [ROLE_ADMIN, ROLE_PLANT_HEAD]:
            machine_df = safe_df("SELECT id, machine_no, line_name, department FROM machines WHERE is_active=1 ORDER BY department, line_name, machine_no")
        else:
            machine_df = safe_df(
                "SELECT id, machine_no, line_name, department FROM machines WHERE is_active=1 AND department=? ORDER BY line_name, machine_no",
                (allowed_dept,),
            )
        if machine_df.empty:
            st.info("No machines available.")
        else:
            selected_mid = st.selectbox("Select Machine ID", machine_df["id"].tolist())
            row = machine_df[machine_df["id"] == selected_mid].iloc[0]
            new_machine = st.text_input("New Machine Number", value=row["machine_no"])
            if st.button("Update Machine"):
                if can_manage_assets_for_department(row["department"]):
                    execute_query("UPDATE machines SET machine_no=? WHERE id=?", (new_machine.strip(), int(selected_mid)))
                    execute_query("UPDATE tickets SET machine_no=? WHERE machine_no=?", (new_machine.strip(), row["machine_no"]))
                    st.success("Machine updated successfully.")
                    st.rerun()
                else:
                    st.error("No access to edit this machine.")

# -------------------------
# RAISE ENTRY
# -------------------------
def raise_entry_page():
    render_header("Raise Breakdown / Improvement", "Line first, then machine selection, then service routing")
    user = current_user()
    src_department = user["department"]

    if src_department == "All":
        st.warning("Please login with a department user to raise entries.")
        return

    dept_check = safe_df("SELECT dept_type FROM departments WHERE dept_name=?", (src_department,))
    if dept_check.empty:
        st.error("Your department is not configured.")
        return

    if dept_check.iloc[0]["dept_type"] != PRODUCTION:
        st.info("Service departments do not raise machine-side breakdown/improvement tickets from this form.")
        return

    line_df = safe_df(
        "SELECT line_name FROM lines WHERE is_active=1 AND department=? ORDER BY line_name",
        (src_department,),
    )
    if line_df.empty:
        st.warning("No lines found. Please ask HOD/Manager to add a line first.")
        return

    with st.form("raise_ticket_form"):
        entry_type = st.selectbox("Entry Type", [ENTRY_BREAKDOWN, ENTRY_IMPROVEMENT])
        selected_line = st.selectbox("Select Line", line_df["line_name"].tolist())

        machine_df = safe_df(
            "SELECT machine_no FROM machines WHERE is_active=1 AND department=? AND line_name=? ORDER BY machine_no",
            (src_department, selected_line),
        )
        if machine_df.empty:
            st.warning("No machines found for this line.")
            st.stop()

        selected_machine = st.selectbox("Select Machine", machine_df["machine_no"].tolist())
        target_department = st.selectbox("Send To", [SERVICE_MAINT, SERVICE_TOOLROOM])
        problem_text = st.text_area("Problem / Improvement Description")
        photo = st.file_uploader("Optional Photo", type=["png", "jpg", "jpeg"])

        planned_date = None
        priority_label = None
        if entry_type == ENTRY_IMPROVEMENT:
            planned_date = st.date_input("Planned Date")
            priority_label = st.selectbox("Plan Label", ["Tomorrow", "Day After Tomorrow", "Planned Date"])

        submit = st.form_submit_button("Submit")
        if submit:
            if not problem_text.strip():
                st.error("Description is required.")
                return

            status_color = "RED" if entry_type == ENTRY_BREAKDOWN else "YELLOW"
            status_text = "Open" if entry_type == ENTRY_BREAKDOWN else "Planned"
            photo_name = photo.name if photo is not None else None
            photo_bytes = photo.getvalue() if photo is not None else None
            raised_at = datetime.now()

            execute_query(
                """
                INSERT INTO tickets (
                    entry_type, source_department, target_department, line_name, machine_no, problem_text,
                    planned_date, priority_label, status_color, status_text,
                    raised_by_name, raised_by_username, raised_by_role,
                    shift_name, raised_time, photo_name, photo_bytes, active_shift_tag
                )
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    entry_type,
                    src_department,
                    target_department,
                    selected_line,
                    selected_machine,
                    problem_text.strip(),
                    planned_date.strftime("%Y-%m-%d") if planned_date else None,
                    priority_label,
                    status_color,
                    status_text,
                    user["full_name"],
                    user["username"],
                    user["role"],
                    get_shift(raised_at),
                    raised_at,
                    photo_name,
                    photo_bytes,
                    active_shift_tag(),
                ),
            )
            st.success("Entry submitted successfully.")
            st.rerun()

# -------------------------
# DASHBOARD
# -------------------------
def dashboard_page():
    hide_old_green_items()
    st_autorefresh(interval=AUTO_REFRESH_MS, key="auto_refresh_dashboard")
    render_header("Central Live Dashboard", "Single dashboard with live status, summaries, charts and scrolling cards")

    user = current_user()
    all_df = visible_tickets_df(include_hidden=False)
    full_report_df = visible_tickets_df(include_hidden=True)

    active_red = all_df[all_df["status_color"] == "RED"] if not all_df.empty else pd.DataFrame()
    active_yellow = all_df[all_df["status_color"] == "YELLOW"] if not all_df.empty else pd.DataFrame()
    green_df = all_df[all_df["status_color"] == "GREEN"] if not all_df.empty else pd.DataFrame()

    today = datetime.now().strftime("%Y-%m-%d")
    today_df = full_report_df.copy()
    if not today_df.empty:
        today_df["raised_time"] = pd.to_datetime(today_df["raised_time"], errors="coerce")
        today_df = today_df[today_df["raised_time"].dt.strftime("%Y-%m-%d") == today]

    maint_count = len(today_df[today_df["target_department"] == SERVICE_MAINT]) if not today_df.empty else 0
    tool_count = len(today_df[today_df["target_department"] == SERVICE_TOOLROOM]) if not today_df.empty else 0
    impro_count = len(today_df[today_df["entry_type"] == ENTRY_IMPROVEMENT]) if not today_df.empty else 0

    if not full_report_df.empty and "downtime_mins" in full_report_df.columns:
        full_report_df["downtime_mins"] = pd.to_numeric(full_report_df["downtime_mins"], errors="coerce").fillna(0)
    total_downtime = 0 if full_report_df.empty else round(full_report_df["downtime_mins"].sum(), 2)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_box("Active Breakdown", len(active_red), "Live RED")
    with c2:
        metric_box("Improvement Pending", len(active_yellow), "Live YELLOW")
    with c3:
        metric_box("Today Maintenance", maint_count, "Assigned to maintenance")
    with c4:
        metric_box("Today Tool Room", tool_count, "Assigned to tool room")
    with c5:
        metric_box("Total Downtime (min)", total_downtime, "Visible report base")

    if user["role"] in [ROLE_ADMIN, ROLE_PLANT_HEAD]:
        st.markdown("### 📊 Plant Summary")
        s1, s2 = st.columns(2)
        with s1:
            if not today_df.empty:
                st.bar_chart(today_df.groupby("target_department").size())
        with s2:
            if not full_report_df.empty:
                top_machines = full_report_df.groupby("machine_no")["downtime_mins"].sum().sort_values(ascending=False).head(10)
                if not top_machines.empty:
                    st.bar_chart(top_machines)

    st.markdown("### 🔴 Live Active Cards")
    live_df = all_df[all_df["status_color"].isin(["RED", "YELLOW"])] if not all_df.empty else pd.DataFrame()
    if live_df.empty:
        st.success("No active breakdown or improvement items.")
    else:
        for _, row in live_df.iterrows():
            box = "card-red" if row["status_color"] == "RED" else "card-yellow"
            st.markdown(f"<div class='{box}'>", unsafe_allow_html=True)
            left, right = st.columns([4, 1.6])
            with left:
                st.markdown(f"### {row['machine_no']} | {row['line_name']}")
                st.write(f"**Type:** {row['entry_type']} | **From:** {row['source_department']} | **To:** {row['target_department']}")
                st.write(f"**Description:** {row['problem_text']}")
                st.write(f"**Shift:** {row['shift_name']} | **Raised By:** {row['raised_by_name']} ({row['raised_by_role']})")
                st.caption(f"Raised Time: {row['raised_time']}")
                if row['planned_date']:
                    st.write(f"**Planned Date:** {row['planned_date']} | **Plan Label:** {row['priority_label']}")
                if row['photo_name']:
                    st.caption(f"Photo attached: {row['photo_name']}")
            with right:
                if can_close_ticket(row):
                    with st.form(f"close_form_{row['id']}"):
                        action_text = st.text_area("Action / Result", key=f"action_{row['id']}")
                        close_button = st.form_submit_button("Close Item")
                        if close_button:
                            if not action_text.strip():
                                st.error("Action / Result is required.")
                            else:
                                raised_time = pd.to_datetime(row["raised_time"])
                                closed_time = datetime.now()
                                downtime = round((closed_time - raised_time).total_seconds() / 60, 2) if row["entry_type"] == ENTRY_BREAKDOWN else 0
                                execute_query(
                                    """
                                    UPDATE tickets
                                    SET action_taken=?, closed_by_name=?, closed_by_username=?, closed_by_role=?,
                                        closed_time=?, downtime_mins=?, status_color='GREEN', status_text='Closed', active_shift_tag=?
                                    WHERE id=?
                                    """,
                                    (
                                        action_text.strip(),
                                        user["full_name"],
                                        user["username"],
                                        user["role"],
                                        closed_time,
                                        downtime,
                                        active_shift_tag(),
                                        int(row["id"]),
                                    ),
                                )
                                st.success("Item closed successfully.")
                                st.rerun()
                else:
                    st.info("View only")
            st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### ✅ Current Shift Green Items")
    if green_df.empty:
        st.info("No green items in current visible shift.")
    else:
        st.dataframe(green_df, use_container_width=True, hide_index=True)

# -------------------------
# REPORTS
# -------------------------
def reports_page():
    render_header("Reports & Analysis", "Historical data, filters and export for standard management review")
    df = visible_tickets_df(include_hidden=True)
    if df.empty:
        st.info("No data available.")
        return

    df["raised_time"] = pd.to_datetime(df["raised_time"], errors="coerce")
    min_date = df["raised_time"].min().date()
    max_date = df["raised_time"].max().date()

    f1, f2, f3, f4 = st.columns(4)
    with f1:
        from_date = st.date_input("From Date", min_date)
    with f2:
        to_date = st.date_input("To Date", max_date)
    with f3:
        status_filter = st.selectbox("Status", ["All", "RED", "YELLOW", "GREEN"])
    with f4:
        type_filter = st.selectbox("Entry Type", ["All", ENTRY_BREAKDOWN, ENTRY_IMPROVEMENT])

    filtered = df[df["raised_time"].dt.date.between(from_date, to_date)]
    if status_filter != "All":
        filtered = filtered[filtered["status_color"] == status_filter]
    if type_filter != "All":
        filtered = filtered[filtered["entry_type"] == type_filter]

    st.dataframe(filtered, use_container_width=True, hide_index=True)

    if not filtered.empty:
        st.markdown("### 📈 Summary Charts")
        c1, c2 = st.columns(2)
        with c1:
            st.bar_chart(filtered.groupby("target_department").size())
        with c2:
            tmp = filtered.copy()
            tmp["downtime_mins"] = pd.to_numeric(tmp["downtime_mins"], errors="coerce").fillna(0)
            top_machine = tmp.groupby("machine_no")["downtime_mins"].sum().sort_values(ascending=False).head(10)
            if not top_machine.empty:
                st.bar_chart(top_machine)

    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV Report", csv, "greaves_bms_report.csv", "text/csv")

# -------------------------
# MAIN
# -------------------------
def main():
    inject_css()
    init_db()
    init_state()

    if not st.session_state.user:
        login_screen()
        return

    session_guard()
    touch_session()

    menu = sidebar_menu()

    if menu == "Dashboard":
        dashboard_page()
    elif menu == "Raise Breakdown/Improvement":
        raise_entry_page()
    elif menu == "Reports":
        reports_page()
    elif menu == "Asset Master":
        asset_master_page()
    elif menu == "User Management":
        user_management_page()
    elif menu == "Department Management":
        department_management_page()

if __name__ == "__main__":
    main()
