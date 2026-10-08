import os

EMPLOYEE_FILE = "employees.txt"
ATTENDANCE_FILE = "attendance.txt"

# ---------------- ADD EMPLOYEE ----------------

def add_employee():
    emp_id = input("Employee ID: ")

    if os.path.exists(EMPLOYEE_FILE):
        with open(EMPLOYEE_FILE, "r") as file:
            for line in file:
                if line.strip():
                    data = line.strip().split(",")
                    if data[0] == emp_id:
                        print("Employee ID already exists!")
                        return

    name = input("Name: ")
    age = input("Age: ")
    gender = input("Gender: ")
    department = input("Department: ")
    designation = input("Designation: ")
    salary = input("Salary: ")
    phone = input("Phone: ")
    email = input("Email: ")

    with open(EMPLOYEE_FILE, "a") as file:
        file.write(f"{emp_id},{name},{age},{gender},{department},{designation},{salary},{phone},{email}\n")

    print("Employee Added Successfully")


# ---------------- VIEW EMPLOYEES ----------------

def view_employees():

    if not os.path.exists(EMPLOYEE_FILE):
        print("No employee records found.")
        return

    with open(EMPLOYEE_FILE, "r") as file:

        found = False

        for line in file:

            if line.strip() == "":
                continue

            data = line.strip().split(",")

            if len(data) != 9:
                continue

            found = True

            print("-" * 40)
            print("Employee ID :", data[0])
            print("Name        :", data[1])
            print("Age         :", data[2])
            print("Gender      :", data[3])
            print("Department  :", data[4])
            print("Designation :", data[5])
            print("Salary      :", data[6])
            print("Phone       :", data[7])
            print("Email       :", data[8])
            print("-" * 40)

        if not found:
            print("No employee records found.")

# ---------------- SEARCH ----------------

def search_employee():

    emp_id = input("Enter Employee ID: ")

    found = False

    if os.path.exists(EMPLOYEE_FILE):

        with open(EMPLOYEE_FILE,"r") as file:

            for line in file:

                d = line.strip().split(",")

                if d[0] == emp_id:

                    found = True

                    print("\nEmployee Found\n")

                    print("Employee ID :", d[0])
                    print("Name :", d[1])
                    print("Age :", d[2])
                    print("Gender :", d[3])
                    print("Department :", d[4])
                    print("Designation :", d[5])
                    print("Salary :", d[6])
                    print("Phone :", d[7])
                    print("Email :", d[8])

    if not found:
        print("Employee Not Found")


# ---------------- UPDATE ----------------

def update_employee():

    emp_id = input("Enter Employee ID: ")

    records = []

    found = False

    if os.path.exists(EMPLOYEE_FILE):

        with open(EMPLOYEE_FILE,"r") as file:

            for line in file:

                d = line.strip().split(",")

                if d[0] == emp_id:

                    found = True

                    print("Leave blank to keep old value")

                    d[1] = input(f"Name ({d[1]}): ") or d[1]
                    d[2] = input(f"Age ({d[2]}): ") or d[2]
                    d[3] = input(f"Gender ({d[3]}): ") or d[3]
                    d[4] = input(f"Department ({d[4]}): ") or d[4]
                    d[5] = input(f"Designation ({d[5]}): ") or d[5]
                    d[6] = input(f"Salary ({d[6]}): ") or d[6]
                    d[7] = input(f"Phone ({d[7]}): ") or d[7]
                    d[8] = input(f"Email ({d[8]}): ") or d[8]

                records.append(",".join(d))

        with open(EMPLOYEE_FILE,"w") as file:
            for r in records:
                file.write(r+"\n")

        if found:
            print("Employee Updated")
        else:
            print("Employee Not Found")


# ---------------- DELETE ----------------

def delete_employee():

    emp_id = input("Enter Employee ID: ")

    records = []

    found = False

    if os.path.exists(EMPLOYEE_FILE):

        with open(EMPLOYEE_FILE,"r") as file:

            for line in file:

                d = line.strip().split(",")

                if d[0] != emp_id:
                    records.append(",".join(d))
                else:
                    found = True

        with open(EMPLOYEE_FILE,"w") as file:
            for r in records:
                file.write(r+"\n")

    if found:
        print("Employee Deleted")
    else:
        print("Employee Not Found")


# ---------------- DEPARTMENT LIST ----------------

def department_list():

    dept = input("Enter Department: ")

    found = False

    if os.path.exists(EMPLOYEE_FILE):

        with open(EMPLOYEE_FILE,"r") as file:

            for line in file:

                d = line.strip().split(",")

                if d[4].lower() == dept.lower():

                    found = True

                    print(d[0], d[1], d[5], d[6])

    if not found:
        print("No Employees Found")


# ---------------- MARK ATTENDANCE ----------------

def mark_attendance():

    date = input("Date (DD-MM-YYYY): ")
    emp_id = input("Employee ID: ")
    status = input("Present/Absent: ")

    with open(ATTENDANCE_FILE,"a") as file:
        file.write(f"{date},{emp_id},{status}\n")

    print("Attendance Marked")


# ---------------- VIEW ATTENDANCE ----------------

def view_attendance():

    if not os.path.exists(ATTENDANCE_FILE):
        print("No Attendance Found")
        return

    with open(ATTENDANCE_FILE,"r") as file:

        for line in file:

            d = line.strip().split(",")

            print("-----------------------------")
            print("Date :", d[0])
            print("Employee ID :", d[1])
            print("Status :", d[2])


# ---------------- SALARY REPORT ----------------

def salary_report():

    if not os.path.exists(EMPLOYEE_FILE):
        print("No Records")
        return

    total = 0
    highest = 0
    lowest = None
    high_name = ""
    low_name = ""

    with open(EMPLOYEE_FILE,"r") as file:

        for line in file:

            d = line.strip().split(",")

            salary = int(d[6])

            total += salary

            if salary > highest:
                highest = salary
                high_name = d[1]

            if lowest is None or salary < lowest:
                lowest = salary
                low_name = d[1]

    print("\nSalary Report")
    print("Total Salary :", total)
    print("Highest Salary :", highest, "-", high_name)
    print("Lowest Salary :", lowest, "-", low_name)


# ---------------- MENU ----------------

while True:

    print("\n===== EMPLOYEE MANAGEMENT SYSTEM =====")
    print("1. Add Employee")
    print("2. View Employees")
    print("3. Search Employee")
    print("4. Update Employee")
    print("5. Delete Employee")
    print("6. Department Wise List")
    print("7. Mark Attendance")
    print("8. View Attendance")
    print("9. Salary Report")
    print("10. Exit")

    choice = input("Enter Choice: ")

    if choice == "1":
        add_employee()

    elif choice == "2":
        view_employees()

    elif choice == "3":
        search_employee()

    elif choice == "4":
        update_employee()

    elif choice == "5":
        delete_employee()

    elif choice == "6":
        department_list()

    elif choice == "7":
        mark_attendance()

    elif choice == "8":
        view_attendance()

    elif choice == "9":
        salary_report()

    elif choice == "10":
        break

    else:
        print("Invalid Choice")