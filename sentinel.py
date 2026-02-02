import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime

DB_FILE = "attendance.db"


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def log_visit(scanner_code):
    """Insert a visit record for the scanned ID and return the student name if found."""
    now = datetime.now()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Look up the student
    cursor.execute("SELECT full_name FROM students WHERE scanner_code = ?", (scanner_code,))
    row = cursor.fetchone()
    student_name = row["full_name"] if row else None

    # Log the visit regardless of whether the student is registered
    cursor.execute(
        """
        INSERT INTO visits (scanner_code, check_in_time, day_of_week, week_number, month_str)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            scanner_code,
            now.strftime("%Y-%m-%d %H:%M:%S"),
            now.strftime("%A"),
            int(now.strftime("%W")),
            now.strftime("%Y-%m"),
        ),
    )
    conn.commit()
    conn.close()
    return student_name


def register_student(scanner_code, school_id, full_name, major, grade_level):
    """Insert a new student into the database. Returns True on success."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO students (scanner_code, school_id, full_name, major, grade_level)
            VALUES (?, ?, ?, ?, ?)
            """,
            (scanner_code, school_id, full_name, major, grade_level or None),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


class RegistrationWindow(tk.Toplevel):
    """Dialog window for registering a new student."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Register Student")
        self.resizable(False, False)
        self.grab_set()

        # Prevent scan input from reaching the main window while registering
        self.parent_app = parent

        padding = {"padx": 10, "pady": 5}

        # --- Name ---
        tk.Label(self, text="Name *", anchor="w").grid(row=0, column=0, sticky="w", **padding)
        self.name_entry = tk.Entry(self, width=30)
        self.name_entry.grid(row=0, column=1, **padding)

        # --- CSU ID ---
        tk.Label(self, text="CSU ID *", anchor="w").grid(row=1, column=0, sticky="w", **padding)
        self.csu_id_entry = tk.Entry(self, width=30)
        self.csu_id_entry.grid(row=1, column=1, **padding)

        # --- Scan ID ---
        tk.Label(self, text="Scan ID *", anchor="w").grid(row=2, column=0, sticky="w", **padding)
        self.scan_id_entry = tk.Entry(self, width=30)
        self.scan_id_entry.grid(row=2, column=1, **padding)

        # --- Major ---
        tk.Label(self, text="Major *", anchor="w").grid(row=3, column=0, sticky="w", **padding)
        self.major_entry = tk.Entry(self, width=30)
        self.major_entry.grid(row=3, column=1, **padding)

        # --- Year (optional) ---
        tk.Label(self, text="Year", anchor="w").grid(row=4, column=0, sticky="w", **padding)
        self.year_combo = ttk.Combobox(
            self,
            width=27,
            values=["", "Freshman", "Sophomore", "Junior", "Senior", "Graduate"],
            state="readonly",
        )
        self.year_combo.grid(row=4, column=1, **padding)
        self.year_combo.current(0)

        # --- Buttons ---
        btn_frame = tk.Frame(self)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        tk.Button(btn_frame, text="Register", width=12, command=self.on_register).pack(
            side="left", padx=5
        )
        tk.Button(btn_frame, text="Cancel", width=12, command=self.destroy).pack(
            side="left", padx=5
        )

        self.name_entry.focus_set()

    def on_register(self):
        name = self.name_entry.get().strip()
        csu_id = self.csu_id_entry.get().strip()
        scan_id = self.scan_id_entry.get().strip()
        major = self.major_entry.get().strip()
        year = self.year_combo.get().strip()

        # Validate required fields
        if not name:
            messagebox.showwarning("Missing Field", "Name is required.", parent=self)
            self.name_entry.focus_set()
            return
        if not csu_id:
            messagebox.showwarning("Missing Field", "CSU ID is required.", parent=self)
            self.csu_id_entry.focus_set()
            return
        if not scan_id:
            messagebox.showwarning("Missing Field", "Scan ID is required.", parent=self)
            self.scan_id_entry.focus_set()
            return
        if not major:
            messagebox.showwarning("Missing Field", "Major is required.", parent=self)
            self.major_entry.focus_set()
            return

        success = register_student(scan_id, csu_id, name, major, year)
        if success:
            messagebox.showinfo("Success", f"Student '{name}' registered.", parent=self)
            self.destroy()
        else:
            messagebox.showerror(
                "Error",
                "A student with that Scan ID already exists.",
                parent=self,
            )
            self.scan_id_entry.focus_set()


class SentinelApp(tk.Tk):
    """Main application window that listens for barcode scans and logs attendance."""

    def __init__(self):
        super().__init__()
        self.title("Esports Attendance")
        self.geometry("500x400")

        # --- Top frame: scan input ---
        top_frame = tk.Frame(self)
        top_frame.pack(fill="x", padx=10, pady=(10, 0))

        tk.Label(top_frame, text="Scan ID:", font=("Arial", 12)).pack(side="left")
        self.scan_entry = tk.Entry(top_frame, font=("Arial", 12))
        self.scan_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.scan_entry.bind("<Return>", self.on_scan)

        # --- Register button ---
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)

        tk.Button(btn_frame, text="Register Student", command=self.open_registration).pack(
            side="right"
        )

        # --- Log area ---
        tk.Label(self, text="Scan Log", font=("Arial", 10, "bold"), anchor="w").pack(
            fill="x", padx=10
        )
        log_frame = tk.Frame(self)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log_text = tk.Text(log_frame, state="disabled", wrap="word", font=("Courier", 10))
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

        # Keep focus on the scan entry
        self.scan_entry.focus_set()
        self.bind("<FocusIn>", self._refocus_scan_entry)

    def _refocus_scan_entry(self, event):
        """Keep the cursor in the scan entry unless a child window is open."""
        if not self._has_toplevel():
            self.scan_entry.focus_set()

    def _has_toplevel(self):
        """Return True if a Toplevel (like the registration dialog) is open."""
        for widget in self.winfo_children():
            if isinstance(widget, tk.Toplevel) and widget.winfo_exists():
                return True
        return False

    def on_scan(self, event=None):
        """Handle a completed scan (Enter key pressed)."""
        scanned_id = self.scan_entry.get().strip()
        self.scan_entry.delete(0, "end")

        if not scanned_id:
            return

        student_name = log_visit(scanned_id)
        now_str = datetime.now().strftime("%H:%M:%S")

        if student_name:
            msg = f"[{now_str}]  {student_name} (ID: {scanned_id})\n"
        else:
            msg = f"[{now_str}]  Unknown ID: {scanned_id}  (not registered)\n"

        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def open_registration(self):
        RegistrationWindow(self)


if __name__ == "__main__":
    app = SentinelApp()
    app.mainloop()
