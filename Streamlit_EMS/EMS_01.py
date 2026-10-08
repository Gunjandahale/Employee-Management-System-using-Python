import csv
import hmac
import os
import re
import tempfile
import threading
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st


GENDERS = ["Male", "Female", "Other"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

st.set_page_config(page_title="Employee Management System", page_icon="👥", layout="wide")


# ---------------- STORAGE ----------------


DATA_DIR = Path(os.environ.get("DATA_DIR") or Path(__file__).resolve().parent)
EMPLOYEE_FILE = DATA_DIR / "employees.txt"
ATTENDANCE_FILE = DATA_DIR / "attendance.txt"

EMP_COLUMNS = [
    "Employee ID", "Name", "Age", "Gender", "Department",
    "Designation", "Salary", "Phone", "Email",
]
ATT_COLUMNS = ["Date", "Employee ID", "Status"]

DATE_FORMAT = "%d-%m-%Y"

@st.cache_resource
def get_lock():
    """One lock shared by all sessions (survives Streamlit reruns)."""
    return threading.RLock()


def clean(value):
    """Trim whitespace and remove line breaks (commas are fine: csv quotes them)."""
    return " ".join(str(value).split())


def same_id(a, b):
    return a.strip().lower() == b.strip().lower()


def _read(path, width):
    rows = []
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) == width:
                    rows.append([c.strip() for c in row])
    return rows


def _write(path, rows):
    """Atomic write: a crash mid-save can never leave a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            csv.writer(f, lineterminator="\n").writerows(rows)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# ---------------- employees ----------------

def load_employees():
    with get_lock():
        return _read(EMPLOYEE_FILE, len(EMP_COLUMNS))


def db_add_employee(row):
    with get_lock():
        records = _read(EMPLOYEE_FILE, len(EMP_COLUMNS))
        if any(same_id(r[0], row[0]) for r in records):
            raise ValueError("Employee ID already exists!")
        records.append(row)
        _write(EMPLOYEE_FILE, records)


def db_update_employee(row):
    with get_lock():
        records = _read(EMPLOYEE_FILE, len(EMP_COLUMNS))
        for i, r in enumerate(records):
            if same_id(r[0], row[0]):
                records[i] = row
                _write(EMPLOYEE_FILE, records)
                return
        raise ValueError("Employee no longer exists.")


def db_delete_employee(emp_id):
    """Delete the employee and their attendance records."""
    with get_lock():
        records = _read(EMPLOYEE_FILE, len(EMP_COLUMNS))
        kept = [r for r in records if not same_id(r[0], emp_id)]
        if len(kept) == len(records):
            raise ValueError("Employee no longer exists.")
        _write(EMPLOYEE_FILE, kept)

        att = _read(ATTENDANCE_FILE, len(ATT_COLUMNS))
        att_kept = [a for a in att if not same_id(a[1], emp_id)]
        if len(att_kept) != len(att):
            _write(ATTENDANCE_FILE, att_kept)


# ---------------- attendance ----------------

def load_attendance():
    with get_lock():
        return _read(ATTENDANCE_FILE, len(ATT_COLUMNS))


def db_mark_attendance(date_str, emp_id, status):
    """Insert or overwrite the record for (date, employee). True if overwritten."""
    with get_lock():
        att = _read(ATTENDANCE_FILE, len(ATT_COLUMNS))
        for a in att:
            if a[0] == date_str and same_id(a[1], emp_id):
                a[2] = status
                _write(ATTENDANCE_FILE, att)
                return True
        att.append([date_str, emp_id, status])
        _write(ATTENDANCE_FILE, att)
        return False


# ---------------- HELPERS ----------------

def to_number(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def fmt_num(value):
    """50000.0 -> '50000', 50000.5 -> '50000.5'"""
    value = float(value)
    return str(int(value)) if value.is_integer() else str(value)


def emp_label(r):
    return f"{r[0]} - {r[1]}"


def employees_df(records):
    df = pd.DataFrame(records, columns=EMP_COLUMNS)
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    df["Salary"] = pd.to_numeric(df["Salary"], errors="coerce")
    return df


def validate_contact(phone, email):
    """Return an error message, or None if fine. Both fields are optional."""
    if phone and not 7 <= len(re.sub(r"\D", "", phone)) <= 15:
        return "Phone number must have 7 to 15 digits."
    if phone and not re.fullmatch(r"[0-9+\-() ]+", phone):
        return "Phone number may only contain digits, spaces, + - ( )."
    if email and not EMAIL_RE.match(email):
        return "Email address looks invalid."
    return None


def flash(message, kind="success"):
    st.session_state["flash"] = (kind, message)


def show_flash():
    if "flash" in st.session_state:
        kind, message = st.session_state.pop("flash")
        getattr(st, kind)(message)


def csv_download(df, filename):
    st.download_button(
        "⬇️ Download CSV", df.to_csv(index=False).encode("utf-8"),
        file_name=filename, mime="text/csv",
    )


# ---------------- LOGIN ----------------

def get_password():
    try:
        pw = st.secrets.get("APP_PASSWORD")
    except Exception:  # no secrets file configured
        pw = None
    return pw or os.environ.get("APP_PASSWORD")


def check_login():
    """Password gate. Set APP_PASSWORD (Streamlit secret or env var) before hosting."""
    pw = get_password()
    if not pw:
        st.sidebar.warning(
            "No APP_PASSWORD is set: anyone with the link can view and edit all data."
        )
        return True

    if st.session_state.get("auth"):
        if st.sidebar.button("Log out"):
            st.session_state["auth"] = False
            st.rerun()
        return True

    st.subheader("🔒 Login")
    with st.form("login_form"):
        entered = st.text_input("Password", type="password")
        ok = st.form_submit_button("Log in", type="primary")
    if ok:
        if hmac.compare_digest(entered.encode(), str(pw).encode()):
            st.session_state["auth"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


# ---------------- ADD EMPLOYEE ----------------

def add_employee():
    st.subheader("➕ Add Employee")

    # Bumping the nonce gives the form fresh widgets (cleared) after a successful add,
    # while a failed validation keeps everything the user typed.
    n = st.session_state.setdefault("add_nonce", 0)

    with st.form(f"add_form_{n}"):
        c1, c2 = st.columns(2)
        emp_id = c1.text_input("Employee ID", key=f"add_id_{n}")
        name = c2.text_input("Name", key=f"add_name_{n}")
        age = c1.number_input("Age", min_value=16, max_value=100, value=25, step=1, key=f"add_age_{n}")
        gender = c2.selectbox("Gender", GENDERS, key=f"add_gender_{n}")
        department = c1.text_input("Department", key=f"add_dept_{n}")
        designation = c2.text_input("Designation", key=f"add_desig_{n}")
        salary = c1.number_input("Salary", min_value=0, value=0, step=1000, key=f"add_sal_{n}")
        phone = c2.text_input("Phone", key=f"add_phone_{n}")
        email = st.text_input("Email", key=f"add_email_{n}")
        submitted = st.form_submit_button("Add Employee", type="primary")

    if not submitted:
        return

    emp_id, name, phone, email = clean(emp_id), clean(name), clean(phone), clean(email)
    if not emp_id or not name:
        st.error("Employee ID and Name are required.")
        return
    problem = validate_contact(phone, email)
    if problem:
        st.error(problem)
        return

    row = [emp_id, name, str(int(age)), gender, clean(department),
           clean(designation), str(int(salary)), phone, email]
    try:
        db_add_employee(row)
    except ValueError as e:
        st.error(str(e))
        return
    st.session_state["add_nonce"] = n + 1
    flash("Employee Added Successfully")
    st.rerun()


# ---------------- VIEW EMPLOYEES ----------------

def view_employees():
    st.subheader("📋 All Employees")
    records = load_employees()
    if not records:
        st.info("No employee records found.")
        return
    df = employees_df(records)
    st.dataframe(df, width="stretch", hide_index=True)
    st.caption(f"Total employees: {len(records)}")
    csv_download(df, "employees.csv")


# ---------------- SEARCH ----------------

def search_employee():
    st.subheader("🔍 Search Employee")
    with st.form("search_form"):  # form so pressing Enter works
        emp_id = st.text_input("Enter Employee ID")
        submitted = st.form_submit_button("Search", type="primary")

    if submitted:
        for r in load_employees():
            if same_id(r[0], emp_id):
                st.success("Employee Found")
                c1, c2 = st.columns(2)
                for i, col in enumerate(EMP_COLUMNS):
                    (c1 if i % 2 == 0 else c2).markdown(f"**{col}:** {r[i]}")
                return
        st.error("Employee Not Found")


# ---------------- UPDATE ----------------

def update_employee():
    st.subheader("✏️ Update Employee")
    records = load_employees()
    if not records:
        st.info("No employee records found.")
        return

    by_id = {r[0]: r for r in records}
    emp_id = st.selectbox("Select Employee", list(by_id), format_func=lambda i: emp_label(by_id[i]))
    d = by_id[emp_id]

    gender_options = GENDERS if d[3] in GENDERS else GENDERS + [d[3]]
    age_now = int(min(100, max(16, to_number(d[2]) or 25)))

    with st.form(f"update_form_{emp_id}"):
        st.caption("Edit the fields you want to change.")
        c1, c2 = st.columns(2)
        name = c1.text_input("Name", d[1], key=f"upd_name_{emp_id}")
        age = c2.number_input("Age", min_value=16, max_value=100, value=age_now, step=1, key=f"upd_age_{emp_id}")
        gender = c1.selectbox("Gender", gender_options, index=gender_options.index(d[3]), key=f"upd_gender_{emp_id}")
        department = c2.text_input("Department", d[4], key=f"upd_dept_{emp_id}")
        designation = c1.text_input("Designation", d[5], key=f"upd_desig_{emp_id}")
        salary = c2.number_input("Salary", min_value=0.0, value=max(0.0, to_number(d[6])),
                                 step=1000.0, format="%.0f", key=f"upd_sal_{emp_id}")
        phone = c1.text_input("Phone", d[7], key=f"upd_phone_{emp_id}")
        email = c2.text_input("Email", d[8], key=f"upd_email_{emp_id}")
        submitted = st.form_submit_button("Update Employee", type="primary")

    if not submitted:
        return

    name, phone, email = clean(name), clean(phone), clean(email)
    if not name:
        st.error("Name cannot be empty.")
        return
    problem = validate_contact(phone, email)
    if problem:
        st.error(problem)
        return

    new = [d[0], name, str(int(age)), gender, clean(department),
           clean(designation), fmt_num(salary), phone, email]
    try:
        db_update_employee(new)
    except ValueError as e:
        st.error(str(e))
        return
    flash("Employee Updated")
    st.rerun()


# ---------------- DELETE ----------------

def delete_employee():
    st.subheader("🗑️ Delete Employee")
    records = load_employees()
    if not records:
        st.info("No employee records found.")
        return

    by_id = {r[0]: r for r in records}
    emp_id = st.selectbox("Select Employee", list(by_id), format_func=lambda i: emp_label(by_id[i]))
    st.caption("This also removes the employee's attendance records.")

    confirm = st.checkbox("I confirm I want to delete this employee", key=f"del_confirm_{emp_id}")
    if st.button("Delete Employee", type="primary", disabled=not confirm):
        try:
            db_delete_employee(emp_id)
        except ValueError as e:
            st.error(str(e))
            return
        flash("Employee Deleted")
        st.rerun()


# ---------------- DEPARTMENT LIST ----------------

def department_list():
    st.subheader("🏢 Department Wise List")
    records = load_employees()
    if not records:
        st.info("No employee records found.")
        return

    # Group case-insensitively ("HR" and "hr" are one department); blank -> "(none)"
    depts = {}
    for r in records:
        depts.setdefault(r[4].lower(), r[4] or "(none)")
    keys = sorted(depts, key=lambda k: depts[k].lower())
    key = st.selectbox("Select Department", keys, format_func=lambda k: depts[k])

    matches = [r for r in records if r[4].lower() == key]
    df = pd.DataFrame(
        [[r[0], r[1], r[5], to_number(r[6])] for r in matches],
        columns=["Employee ID", "Name", "Designation", "Salary"],
    )
    st.dataframe(df, width="stretch", hide_index=True)
    st.caption(f"{len(matches)} employee(s) in {depts[key]}")


# ---------------- MARK ATTENDANCE ----------------

def mark_attendance():
    st.subheader("✅ Mark Attendance")
    records = load_employees()
    if not records:
        st.info("Add employees first before marking attendance.")
        return

    by_id = {r[0]: r for r in records}

    with st.form("attendance_form"):
        att_date = st.date_input("Date", value=date.today(), max_value=date.today(), format="DD/MM/YYYY")
        emp_id = st.selectbox("Employee", list(by_id), format_func=lambda i: emp_label(by_id[i]))
        status = st.radio("Status", ["Present", "Absent"], horizontal=True)
        submitted = st.form_submit_button("Mark Attendance", type="primary")

    if submitted:
        replaced = db_mark_attendance(att_date.strftime(DATE_FORMAT), emp_id, status)
        st.success("Attendance Updated (replaced the earlier entry for that day)" if replaced
                   else "Attendance Marked")


# ---------------- VIEW ATTENDANCE ----------------

def view_attendance():
    st.subheader("📅 Attendance Records")
    att = load_attendance()
    if not att:
        st.info("No Attendance Found")
        return

    names = {r[0].lower(): r[1] for r in load_employees()}
    df = pd.DataFrame(att, columns=ATT_COLUMNS)
    df.insert(2, "Name", df["Employee ID"].str.lower().map(names).fillna("(deleted)"))

    # Sort by real date, newest first (dd-mm-yyyy strings don't sort correctly)
    df["_d"] = pd.to_datetime(df["Date"], format=DATE_FORMAT, errors="coerce")
    df = df.sort_values("_d", ascending=False, kind="stable").drop(columns="_d")

    c1, c2 = st.columns(2)
    emp_filter = c1.selectbox("Filter by Employee ID", ["All"] + sorted(df["Employee ID"].unique()))
    status_filter = c2.selectbox("Filter by Status", ["All", "Present", "Absent"])

    if emp_filter != "All":
        df = df[df["Employee ID"] == emp_filter]
    if status_filter != "All":
        df = df[df["Status"] == status_filter]

    st.dataframe(df, width="stretch", hide_index=True)
    st.caption(f"{len(df)} record(s)")
    csv_download(df, "attendance.csv")


# ---------------- SALARY REPORT ----------------

def salary_report():
    st.subheader("💰 Salary Report")
    records = load_employees()
    if not records:
        st.info("No Records")
        return

    salaries = [to_number(r[6]) for r in records]
    hi = max(range(len(records)), key=lambda i: salaries[i])
    lo = min(range(len(records)), key=lambda i: salaries[i])

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Salary", f"{sum(salaries):,.0f}")
    c2.metric("Highest Salary", f"{salaries[hi]:,.0f}")
    c2.caption(records[hi][1])
    c3.metric("Lowest Salary", f"{salaries[lo]:,.0f}")
    c3.caption(records[lo][1])

    st.markdown("#### Salary by Employee")
    chart_df = pd.DataFrame(
        {"Employee": [emp_label(r) for r in records], "Salary": salaries}
    ).set_index("Employee")
    st.bar_chart(chart_df)


# ---------------- MAIN / NAVIGATION ----------------

PAGES = {
    "Add Employee": add_employee,
    "View Employees": view_employees,
    "Search Employee": search_employee,
    "Update Employee": update_employee,
    "Delete Employee": delete_employee,
    "Department Wise List": department_list,
    "Mark Attendance": mark_attendance,
    "View Attendance": view_attendance,
    "Salary Report": salary_report,
}


def main():
    st.title("👥 Employee Management System")
    if not check_login():
        return
    st.sidebar.title("Menu")
    page = st.sidebar.radio("Go to", list(PAGES.keys()), label_visibility="collapsed")
    show_flash()
    PAGES[page]()


if __name__ == "__main__":
    main()