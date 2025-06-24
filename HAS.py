import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import heapq
from datetime import datetime, date
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json
import os
import random
import re
import sys
import numpy as np
import pandas as pd

# Ensure matplotlib backend is set correctly
plt.switch_backend('TkAgg')

# Custom style configuration
class CustomStyle:
    def __init__(self):
        self.primary_color = "#2c3e50"
        self.secondary_color = "#3498db"
        self.accent_color = "#e74c3c"
        self.bg_color = "#ecf0f1"
        self.text_color = "#2c3e50"
        self.success_color = "#27ae60"
        self.warning_color = "#f39c12"
        self.error_color = "#e74c3c"
        
        # Configure ttk styles
        style = ttk.Style()
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=("Segoe UI", 10))
        style.configure("TButton", 
                       background=self.secondary_color,
                       foreground="Black",
                       font=("Segoe UI", 10, "bold"),
                       padding=5)
        style.map("TButton",
                 background=[("active", self.primary_color)],
                 foreground=[("active", "white")])
        style.configure("Header.TLabel", 
                       font=("Segoe UI", 24, "bold"),
                       foreground=self.primary_color)
        style.configure("Subheader.TLabel",
                       font=("Segoe UI", 16),
                       foreground=self.secondary_color)
        style.configure("Success.TButton",
                       background=self.success_color)
        style.configure("Warning.TButton",
                       background=self.warning_color)
        style.configure("Error.TButton",
                       background=self.error_color)
        style.configure("TEntry",
                       fieldbackground="white",
                       padding=5)
        style.configure("TCombobox",
                       fieldbackground="white",
                       padding=5)
        style.configure("Treeview",
                       background="white",
                       fieldbackground="white",
                       foreground=self.text_color)
        style.configure("Treeview.Heading",
                       background=self.primary_color,
                       foreground="black",
                       font=("Segoe UI", 10, "bold"))
        style.map("Treeview",
                 background=[("selected", self.secondary_color)],
                 foreground=[("selected", "white")])

# ---------------------------
# Core Scheduling Logic
# ---------------------------
class HospitalScheduler:
    def __init__(self):
        self.pq = []  # Priority Queue (Min-Heap) for waiting patients
        self.counter = 0  # Used for tie-breaking
        self.served_patients = []  # List to store served patient records
        self.appointment_file = 'appointments_today.json'
        self.load_appointments()

    def load_appointments(self):
        today_str = date.today().isoformat()
        try:
            with open(self.appointment_file, 'r') as f:
                data = json.load(f)
                if data.get('date') == today_str:
                    self.pq = [tuple(item) for item in data.get('waiting', [])]
                    self.counter = data.get('counter', 0)
                    self.served_patients = [(n, s, d, datetime.strptime(t, '%Y-%m-%d %H:%M:%S')) for n, s, d, t in data.get('served', [])]
                    return
        except Exception:
            pass
        # If not today or file missing/corrupt, reset
        self.pq = []
        self.counter = 0
        self.served_patients = []
        self.save_appointments()

    def save_appointments(self):
        today_str = date.today().isoformat()
        try:
            with open(self.appointment_file, 'w') as f:
                json.dump({
                    'date': today_str,
                    'waiting': self.pq,
                    'counter': self.counter,
                    'served': [(n, s, d, t.strftime('%Y-%m-%d %H:%M:%S')) for n, s, d, t in self.served_patients]
                }, f)
        except Exception:
            pass

    def add_patient(self, name, severity, department):
        heapq.heappush(self.pq, (severity, self.counter, name, department))
        self.counter += 1
        self.save_appointments()

    def serve_patient(self):
        if self.pq:
            severity, _, name, department = heapq.heappop(self.pq)
            timestamp = datetime.now()
            self.served_patients.append((name, severity, department, timestamp))
            # Decrement analytics severity count
            if hasattr(self, 'analytics') and self.analytics:
                self.analytics.serve_patient_severity(severity)
            self.save_appointments()
            return f"Serving: {name} (Severity: {severity}, Department: {department})"
        return "No patients in queue."

    def get_waiting_list(self):
        return sorted(self.pq)

    def get_served_list(self):
        return self.served_patients

# ---------------------------
# Patient Management Using a Text File (JSON)
# ---------------------------

class PatientDatabase:
    def __init__(self):
        self.file = "patients.txt"
        self.patients = []
        self.load_patients()

    def load_patients(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, "r") as f:
                    self.patients = json.load(f)
            except Exception as e:
                messagebox.showerror("Load Error", f"Error loading patient data: {e}")
                self.patients = []
        else:
            self.patients = []

    def save_patients(self):
        try:
            with open(self.file, "w") as f:
                json.dump(self.patients, f, indent=4)
        except Exception as e:
            messagebox.showerror("Save Error", f"Error saving patient data: {e}")

    def validate_patient(self, patient):
        """ Validates gender and contact number before adding. """
        if patient["Gender"] not in ["Male", "Female","male","female","MALE","FEMALE"]:
            messagebox.showerror("Validation Error", "Gender must be 'Male' or 'Female'.")
            return False

        if not re.fullmatch(r"[679]\d{9}", patient["Contact"]):
            messagebox.showerror("Validation Error", "Contact must be 10 digits & start with 6 or 9.")
            return False
        if patient["Blood Type"] not in ["A+", "A-","B+","B-","AB+","AB-","O+","O-","a+","a-","b+","b-","ab+","ab-","o+","o-"]:
            messagebox.showerror("Validation Error", "Blood Group must be 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'.")
            return False

        return True

    def add_patient(self, patient):
        """ Adds a patient after validation. Returns True if added, False if not. """
        if self.validate_patient(patient):
            # Check for duplicate by Name and Contact
            for p in self.patients:
                if p.get('Name') == patient.get('Name') and  p.get('Age')==patient.get('Age') and p.get('Contact') == patient.get('Contact'):
                    messagebox.showerror("Duplicate Error", "A patient with the same name and contact already exists.")
                    return False
            self.patients.append(patient)
            self.save_patients()
            return True
        return False

    def delete_patient(self, patient_name):
        """ Deletes a patient by name. """
        self.patients = [p for p in self.patients if p["Name"] != patient_name]
        self.save_patients()

    def get_all_patients(self):
        """ Returns all stored patients. """
        return self.patients


class Department:
    def __init__(self, name, capacity):
        self.name = name
        self.capacity = capacity
        self.current_patients = 0
        self.staff = []

class DepartmentManager:
    def __init__(self):
        self.departments = {
            "Emergency": Department("Emergency", 50),
            "Cardiology": Department("Cardiology", 30),
            "Pediatrics": Department("Pediatrics", 25),
            "Surgery": Department("Surgery", 20),
            "General Medicine": Department("General Medicine", 40),
            "Addiction control":Department("Addiction control",100)
        }
        self.load_departments()

    def load_departments(self):
        """Load departments from file if exists"""
        if os.path.exists('departments.json'):
            try:
                with open('departments.json', 'r') as f:
                    dept_data = json.load(f)
                    self.departments = {
                        name: Department(name, data['capacity'])
                        for name, data in dept_data.items()
                    }
                    # Restore current patients
                    for name, data in dept_data.items():
                        self.departments[name].current_patients = data['current_patients']
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load departments: {e}")

    def save_departments(self):
        """Save departments to file"""
        try:
            dept_data = {
                name: {
                    'capacity': dept.capacity,
                    'current_patients': dept.current_patients
                }
                for name, dept in self.departments.items()
            }
            with open('departments.json', 'w') as f:
                json.dump(dept_data, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save departments: {e}")

    def add_department(self, name, capacity):
        """Add a new department"""
        if name in self.departments:
            raise ValueError("Department already exists")
        self.departments[name] = Department(name, capacity)
        self.save_departments()

    def delete_department(self, name):
        """Delete a department"""
        if name not in self.departments:
            raise ValueError("Department does not exist")
        if self.departments[name].current_patients > 0:
            raise ValueError("Cannot delete department with active patients")
        del self.departments[name]
        self.save_departments()

    def update_department(self, name, capacity=None):
        """Update department details"""
        if name not in self.departments:
            raise ValueError("Department does not exist")
        if capacity is not None:
            if capacity < self.departments[name].current_patients:
                raise ValueError("New capacity cannot be less than current patients")
            self.departments[name].capacity = capacity
        self.save_departments()

    def admit_patient(self, department_name):
        """Admit a patient to a department"""
        if department_name not in self.departments:
            raise ValueError("Department does not exist")
        dept = self.departments[department_name]
        if dept.current_patients >= dept.capacity:
            raise ValueError("Department is at full capacity")
        dept.current_patients += 1
        self.save_departments()

    def discharge_patient(self, department_name):
        """Discharge a patient from a department"""
        if department_name not in self.departments:
            raise ValueError("Department does not exist")
        dept = self.departments[department_name]
        if dept.current_patients <= 0:
            raise ValueError("No patients to discharge")
        dept.current_patients -= 1
        self.save_departments()

    def get_department_status(self):
        """Get current status of all departments"""
        return {
            name: {
                'current_patients': dept.current_patients,
                'capacity': dept.capacity,
                'occupancy_rate': (dept.current_patients / dept.capacity * 100) if dept.capacity > 0 else 0
            }
            for name, dept in self.departments.items()
        }

    def get_available_capacity(self, department_name):
        """Get available capacity in a department"""
        if department_name not in self.departments:
            raise ValueError("Department does not exist")
        dept = self.departments[department_name]
        return dept.capacity - dept.current_patients

    def is_department_full(self, department_name):
        """Check if a department is at full capacity"""
        if department_name not in self.departments:
            raise ValueError("Department does not exist")
        dept = self.departments[department_name]
        return dept.current_patients >= dept.capacity

# ---------------------------
# Emergency Alert System with Dynamic Configuration
# ---------------------------
class EmergencyAlert:
    def __init__(self):
        self.active_alerts = []
        self.alert_history_file = 'alert_history.json'
        self.alert_history = self.load_alert_history()
        # Restore last active alerts from history (if any were not cleared)
        self.restore_active_alerts_from_history()
        # Use a dynamic configuration dictionary.
        # Each key is an alert code and its value is a dict with "description" and "color".
        self.alert_config = {
            "Code Blue": {"description": "Cardiac Arrest", "color": "lightblue"},
            "Code Red": {"description": "Fire", "color": "lightcoral"},
            "Code Black": {"description": "Bomb Threat", "color": "gray"},
            "Code Grey": {"description": "Violent Patient", "color": "lightgray"},
            "Code Orange": {"description": "Mass Casualty", "color": "orange"}
        }

    def load_alert_history(self):
        try:
            if os.path.exists(self.alert_history_file):
                with open(self.alert_history_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    def restore_active_alerts_from_history(self):
        # Optionally, restore all alerts from history as active (or filter by a flag if you want only uncleared)
        # Here, we restore the last N alerts as active (or all, if you want)
        # You can add a 'cleared' flag to alert_history for more advanced logic
        self.active_alerts = []
        for alert in self.alert_history:
            # Convert timestamp back to datetime for display if needed
            if isinstance(alert.get('timestamp'), str):
                try:
                    alert['timestamp'] = datetime.strptime(alert['timestamp'], '%Y-%m-%d %H:%M:%S')
                except Exception:
                    pass
            self.active_alerts.append(alert)

    def raise_alert(self, code, location):
        # Look up description from alert_config if available
        description = self.alert_config.get(code, {}).get("description", "Unknown Alert")
        timestamp = datetime.now()
        alert = {
            "code": code,
            "description": description,
            "location": location,
            "timestamp": timestamp
        }
        self.active_alerts.append(alert)
        self.save_alert_history(alert)

    def save_alert_history(self, alert):
        # Save alert to alert_history.json (append mode) and to self.alert_history
        try:
            # Convert timestamp to string for JSON
            alert_to_save = alert.copy()
            if isinstance(alert_to_save["timestamp"], datetime):
                alert_to_save["timestamp"] = alert_to_save["timestamp"].strftime('%Y-%m-%d %H:%M:%S')
            self.alert_history.append(alert_to_save)
            # Load existing history
            if os.path.exists(self.alert_history_file):
                with open(self.alert_history_file, 'r') as f:
                    history = json.load(f)
            else:
                history = []
            history.append(alert_to_save)
            with open(self.alert_history_file, 'w') as f:
                json.dump(history, f, indent=4)
        except Exception as e:
            pass  # Optionally log error

    def clear_alert(self, index):
        if 0 <= index < len(self.active_alerts):
            self.active_alerts.pop(index)

# ---------------------------
# Analytics System
# ---------------------------
class AnalyticsSystem:
    def __init__(self):
        self.analytics_file = 'analytics_data.json'
        self.severity_counts = self.load_analytics()

    def load_analytics(self):
        try:
            with open(self.analytics_file, 'r') as f:
                data = json.load(f)
                # Ensure all severities 1-10 are present
                return {int(k): int(v) for k, v in data.items()}
        except Exception:
            return {i: 0 for i in range(1, 11)}

    def save_analytics(self):
        try:
            with open(self.analytics_file, 'w') as f:
                json.dump(self.severity_counts, f)
        except Exception:
            pass

    def add_patient_visit(self, department, severity):
        if 1 <= severity <= 10:
            self.severity_counts[severity] = self.severity_counts.get(severity, 0) + 1
            self.save_analytics()

    def serve_patient_severity(self, severity):
        if 1 <= severity <= 10 and self.severity_counts.get(severity, 0) > 0:
            self.severity_counts[severity] -= 1
            self.save_analytics()

    def generate_department_report(self):
        dept_counts = {}
        for visit in self.patient_data:
            dept = visit["department"]
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
        return dept_counts

    def generate_severity_report(self):
        return self.severity_counts.copy()

# ---------------------------
# Main Application with Page Navigation
# ---------------------------
class HospitalManagementApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Advanced Hospital Management System")
        self.state('zoomed')  # Maximize window

        # Initialize custom styles
        self.style = CustomStyle()
        self.configure(background=self.style.bg_color)
        
        # Create a main container
        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Create a header frame
        self.header_frame = ttk.Frame(self.main_container)
        self.header_frame.pack(fill='x', pady=(0, 20))
        
        # Add header label
        header_label = ttk.Label(self.header_frame, 
                               text="Hospital Management System",
                               style="Header.TLabel")
        header_label.pack(side=tk.LEFT)
        
        # Add current time label
        self.time_label = ttk.Label(self.header_frame,
                                  text="",
                                  style="Subheader.TLabel")
        self.time_label.pack(side=tk.RIGHT)
        self.update_time()
        
        # Create navigation frame
        self.nav_frame = ttk.Frame(self.main_container)
        self.nav_frame.pack(fill='x', pady=(0, 20))
        
        # Navigation buttons
        nav_buttons = [
            ("Home", HomePage),
            ("Appointments", AppointmentPage),
            ("Patient Management", PatientManagementPage),
            ("Emergency Alerts", EmergencyAlertsPage),
            ("Analytics", AnalyticsPage),
            ("Alert Config", AlertConfigPage),
            ("Departments", DepartmentManagementPage)
        ]
        
        for text, page in nav_buttons:
            btn = ttk.Button(self.nav_frame,
                           text=text,
                           command=lambda p=page: self.show_frame(p),
                           style="TButton")
            btn.pack(side=tk.LEFT, padx=5, ipadx=10, ipady=5)
        
        # Initialize system components
        self.scheduler = HospitalScheduler()
        self.patient_db = PatientDatabase()
        self.department_mgr = DepartmentManager()
        self.emergency = EmergencyAlert()
        self.analytics = AnalyticsSystem()
        # Link analytics to scheduler for decrement on serve
        self.scheduler.analytics = self.analytics

        # Container to hold all pages
        self.container = ttk.Frame(self.main_container)
        self.container.pack(fill='both', expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Dictionary to hold pages
        self.frames = {}
        for F in (HomePage, AppointmentPage, PatientManagementPage,
                 EmergencyAlertsPage, AnalyticsPage, AlertConfigPage,
                 DepartmentManagementPage):
            frame = F(parent=self.container, controller=self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(HomePage)
        
        # Start updating time
        self.after(1000, self.update_time)

    def update_time(self):
        current_time = datetime.now().strftime("%I:%M %p, %B %d, %Y")
        self.time_label.config(text=current_time)
        self.after(1000, self.update_time)

    def show_frame(self, page):
        frame = self.frames[page]
        frame.tkraise()
        # If showing AnalyticsPage, update analytics automatically
        if page == AnalyticsPage:
            frame.update_analytics()
        # If showing HomePage, refresh stats
        if page == HomePage:
            frame.refresh_stats()

# ---------------------------
# Home Page
# ---------------------------
class HomePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.queue_file = 'queue_demo.json'
        # Modern dashboard background
        self.configure(background='#f7fafd')

        # Main card frame (shadow effect)
        self.card = tk.Frame(self, bg='white', bd=0, highlightthickness=0)
        self.card.place(relx=0.5, rely=0.5, anchor='center', width=900, height=600)
        self.card.update()
        self.card_shadow = tk.Canvas(self, width=920, height=620, bg='#f7fafd', highlightthickness=0, bd=0)
        self.card_shadow.place(relx=0.5, rely=0.5, anchor='center')
        self.card_shadow.create_oval(10, 10, 910, 610, fill='#e3e8ee', outline='')
        self.card.lift()

        # Header with icon
        header_frame = tk.Frame(self.card, bg='white')
        header_frame.pack(fill='x', pady=(30, 10), padx=40)
        header_icon = tk.Label(header_frame, text='🏥', font=('Segoe UI Emoji', 32), bg='white')
        header_icon.pack(side='left', padx=(0, 10))
        header_label = tk.Label(header_frame, text='Hospital Management System', font=('Segoe UI', 28, 'bold'), fg='#2c3e50', bg='white')
        header_label.pack(side='left')

        # Stats cards
        stats_frame = tk.Frame(self.card, bg='white')
        stats_frame.pack(fill='x', pady=(10, 30), padx=40)
        self.stats_labels = {}
        stats = [
            ("👤 Total Patients", "total_patients", '#4f8cff'),
            ("🚨 Active Alerts", "active_alerts", '#e74c3c'),
            ("🏢 Departments", "departments", '#27ae60'),
            ("📅 Today's Appointments", "appointments", '#f39c12')
        ]
        for i, (label, key, color) in enumerate(stats):
            stat_card = tk.Frame(stats_frame, bg='white', bd=0, highlightbackground='#e3e8ee', highlightthickness=2)
            stat_card.grid(row=0, column=i, padx=15, ipadx=10, ipady=10, sticky='nsew')
            stat_icon = tk.Label(stat_card, text=label.split()[0], font=('Segoe UI Emoji', 18), bg='white')
            stat_icon.pack(pady=(5, 0))
            stat_label = tk.Label(stat_card, text=' '.join(label.split()[1:]), font=('Segoe UI', 10, 'bold'), fg='#7b8a97', bg='white')
            stat_label.pack()
            value_label = tk.Label(stat_card, text='0', font=('Segoe UI', 26, 'bold'), fg=color, bg='white')
            value_label.pack(pady=(0, 5))
            self.stats_labels[key] = value_label
        stats_frame.grid_columnconfigure((0,1,2,3), weight=1)

        # Queue Visualization Card
        queue_card = tk.Frame(self.card, bg='white', bd=0, highlightbackground='#e3e8ee', highlightthickness=2)
        queue_card.pack(fill='both', expand=True, padx=40, pady=(0, 30))
        queue_card.grid_propagate(False)
        queue_card.grid_rowconfigure(1, weight=1)
        queue_card.grid_columnconfigure(0, weight=1)

        # Queue Title
        queue_title = tk.Label(queue_card, text='Priority Queue Visualization', font=('Segoe UI', 14, 'bold'), fg='#2c3e50', bg='white')
        queue_title.grid(row=0, column=0, sticky='w', padx=20, pady=(15, 5))

        # Input Frame
        input_frame = tk.Frame(queue_card, bg='white')
        input_frame.grid(row=1, column=0, sticky='ew', padx=20, pady=(0, 10))
        tk.Label(input_frame, text="Patient Name:", font=('Segoe UI', 10), bg='white').pack(side=tk.LEFT, padx=5)
        self.name_entry = ttk.Entry(input_frame, font=('Segoe UI', 10))
        self.name_entry.pack(side=tk.LEFT, padx=5)
        tk.Label(input_frame, text="Priority (1-10):", font=('Segoe UI', 10), bg='white').pack(side=tk.LEFT, padx=5)
        self.priority_entry = ttk.Entry(input_frame, width=5, font=('Segoe UI', 10))
        self.priority_entry.pack(side=tk.LEFT, padx=5)
        style = ttk.Style()
        style.configure('Modern.TButton', font=('Segoe UI', 11, 'bold'), background='#ffffff', foreground='#000000', padding=8, borderwidth=0)
        style.map('Modern.TButton', background=[('active', '#e3e8ee')], foreground=[('active', '#000000')])
        ttk.Button(input_frame, text="Add Patient", command=self.add_demo_patient, style='Modern.TButton').pack(side=tk.LEFT, padx=10)
        ttk.Button(input_frame, text="Serve Next", command=self.serve_demo_patient, style='Modern.TButton').pack(side=tk.LEFT, padx=5)

        # Canvas for visualization
        self.canvas = tk.Canvas(queue_card, height=120, bg='#f7fafd', highlightthickness=0)
        self.canvas.grid(row=2, column=0, sticky='ew', padx=20, pady=(0, 10))
        self.status_label = tk.Label(queue_card, text="Current Queue: Empty", font=('Segoe UI', 10, 'bold'), fg='#7b8a97', bg='white')
        self.status_label.grid(row=3, column=0, sticky='w', padx=20, pady=(0, 10))

        # Initialize demo queue
        self.demo_queue = self.load_demo_queue()
        self.refresh_stats()
        self.bind_events()
        self.update_visualization()

    def load_demo_queue(self):
        try:
            with open(self.queue_file, 'r') as f:
                data = json.load(f)
                # Ensure it's a list of [priority, name]
                if isinstance(data, list) and all(isinstance(item, list) and len(item) == 2 for item in data):
                    return [(int(priority), str(name)) for priority, name in data]
        except Exception:
            pass
        return []

    def save_demo_queue(self):
        try:
            with open(self.queue_file, 'w') as f:
                json.dump(self.demo_queue, f)
        except Exception:
            pass

    def bind_events(self):
        # Add hover effects to buttons
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.bind("<Enter>", lambda e: e.widget.state(['pressed']))
                widget.bind("<Leave>", lambda e: e.widget.state(['!pressed']))

    def add_demo_patient(self):
        name = self.name_entry.get().strip()
        priority = self.priority_entry.get().strip()
        if not name or not priority.isdigit() or not (1 <= int(priority) <= 10):
            messagebox.showerror("Error", "Please enter valid name and priority (1-10)")
            return
        self.demo_queue.append((int(priority), name))
        self.demo_queue.sort()
        self.name_entry.delete(0, tk.END)
        self.priority_entry.delete(0, tk.END)
        self.save_demo_queue()
        self.update_visualization()

    def serve_demo_patient(self):
        if not self.demo_queue:
            messagebox.showinfo("Queue Empty", "No patients in queue")
            return
        priority, name = self.demo_queue.pop(0)
        messagebox.showinfo("Serving Patient", f"Now serving: {name} (Priority: {priority})")
        self.save_demo_queue()
        self.update_visualization()

    def update_visualization(self):
        self.canvas.delete("all")
        if not self.demo_queue:
            self.status_label.config(text="Current Queue: Empty")
            return
        self.status_label.config(text=f"Current Queue: {len(self.demo_queue)} patients")
        box_width = 100
        box_height = 50
        spacing = 30
        start_x = 40
        y = 60
        for i, (priority, name) in enumerate(self.demo_queue):
            x = start_x + i * (box_width + spacing)
            self.canvas.create_rectangle(x, y-box_height/2, x+box_width, y+box_height/2, fill='#ffffff', outline='#4f8cff', width=2)
            self.canvas.create_text(x+box_width/2, y-10, text=name, font=('Segoe UI', 11, 'bold'), fill='#2c3e50')
            self.canvas.create_text(x+box_width/2, y+12, text=f"Priority: {priority}", font=('Segoe UI', 10), fill='#2c3e50')
            if i < len(self.demo_queue) - 1:
                self.canvas.create_line(x+box_width+10, y, x+box_width+spacing-10, y, arrow=tk.LAST, fill='#4f8cff', width=2)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def refresh_stats(self):
        total_patients = len(self.controller.patient_db.get_all_patients())
        self.stats_labels['total_patients'].config(text=str(total_patients))
        active_alerts = len(self.controller.emergency.active_alerts)
        self.stats_labels['active_alerts'].config(text=str(active_alerts))
        departments = len(self.controller.department_mgr.departments)
        self.stats_labels['departments'].config(text=str(departments))
        appointments = len(self.controller.scheduler.get_waiting_list())
        self.stats_labels['appointments'].config(text=str(appointments))

# ---------------------------
# Appointment Page
# ---------------------------
class AppointmentPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(background=self.controller.style.bg_color)
        
        # Create main content frame
        content_frame = ttk.Frame(self)
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title = ttk.Label(content_frame,
                         text="Appointment Scheduling",
                         style="Header.TLabel")
        title.pack(pady=(0, 20))
        
        # Create two columns
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=(0, 10))
        
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill='both', expand=True, padx=(10, 0))
        
        # Appointment Form
        form_frame = ttk.LabelFrame(left_frame, text="Book Appointment")
        form_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Form fields
        fields = [
            ("Patient Name", "name_entry"),
            ("Severity (1-10)", "severity_entry"),
            ("Department", "department_entry")
        ]
        
        self.entries = {}
        for i, (label, var_name) in enumerate(fields):
            field_frame = ttk.Frame(form_frame)
            field_frame.pack(fill='x', padx=10, pady=5)
            
            ttk.Label(field_frame,
                     text=label + ":",
                     style="Subheader.TLabel").pack(side=tk.LEFT, padx=5)
            
            if var_name == "department_entry":
                self.entries[var_name] = ttk.Combobox(field_frame, state='readonly')
                self.update_department_list()  # Initial department list update
            else:
                self.entries[var_name] = ttk.Entry(field_frame)
            
            self.entries[var_name].pack(side=tk.RIGHT, fill='x', expand=True, padx=5)
        
        # Buttons frame
        button_frame = ttk.Frame(form_frame)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(button_frame,
                  text="Add Appointment",
                  command=self.add_appointment,
                  style="Success.TButton").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame,
                  text="Serve Next Patient",
                  command=self.serve_patient,
                  style="Warning.TButton").pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame,
                  text="Refresh Queue",
                  command=self.refresh_lists,
                  style="TButton").pack(side=tk.LEFT, padx=5)
        
        # Add Clear Appointment History button
        ttk.Button(button_frame,
                  text="Clear Appointment History",
                  command=self.clear_appointment_history,
                  style="Error.TButton").pack(side=tk.LEFT, padx=5)
        
        # Lists Frame
        lists_frame = ttk.LabelFrame(right_frame, text="Appointment Status")
        lists_frame.pack(fill='both', expand=True)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(lists_frame)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Waiting Queue Tab
        wait_frame = ttk.Frame(notebook)
        notebook.add(wait_frame, text="Waiting Queue")
        
        # Create Treeview for waiting queue
        self.waiting_tree = ttk.Treeview(wait_frame,
                                       columns=('Name', 'Severity', 'Department'),
                                       show='headings')
        
        self.waiting_tree.heading('Name', text='Name')
        self.waiting_tree.heading('Severity', text='Severity')
        self.waiting_tree.heading('Department', text='Department')
        
        # Add scrollbar
        wait_scrollbar = ttk.Scrollbar(wait_frame, orient=tk.VERTICAL, command=self.waiting_tree.yview)
        self.waiting_tree.configure(yscrollcommand=wait_scrollbar.set)
        
        self.waiting_tree.pack(side=tk.LEFT, fill='both', expand=True)
        wait_scrollbar.pack(side=tk.RIGHT, fill='y')
        
        # Served Patients Tab
        served_frame = ttk.Frame(notebook)
        notebook.add(served_frame, text="Appointment History")
        
        # Create Treeview for served patients
        self.served_tree = ttk.Treeview(served_frame,
                                      columns=('Name', 'Severity', 'Department', 'Time'),
                                      show='headings')
        
        self.served_tree.heading('Name', text='Name')
        self.served_tree.heading('Severity', text='Severity')
        self.served_tree.heading('Department', text='Department')
        self.served_tree.heading('Time', text='Time')
        
        # Add scrollbar
        served_scrollbar = ttk.Scrollbar(served_frame, orient=tk.VERTICAL, command=self.served_tree.yview)
        self.served_tree.configure(yscrollcommand=served_scrollbar.set)
        
        self.served_tree.pack(side=tk.LEFT, fill='both', expand=True)
        served_scrollbar.pack(side=tk.RIGHT, fill='y')
        
        # Add hover effects
        self.bind_events()
        
        # Initial refresh
        self.refresh_lists()
    
    def bind_events(self):
        # Add hover effects to buttons
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.bind("<Enter>", lambda e: e.widget.state(['pressed']))
                widget.bind("<Leave>", lambda e: e.widget.state(['!pressed']))

    def update_department_list(self):
        """Update the department combobox with current departments"""
        departments = list(self.controller.department_mgr.departments.keys())
        self.entries['department_entry']['values'] = departments
        if departments:
            self.entries['department_entry'].set(departments[0])

    def add_appointment(self):
        name = self.entries['name_entry'].get().strip()
        severity = self.entries['severity_entry'].get().strip()
        department = self.entries['department_entry'].get().strip()
        if not name or not severity.isdigit() or not (1 <= int(severity) <= 10) or not department:
            messagebox.showerror("Invalid Input", "Please enter valid name, severity (1-10), and department")
            return
        # Check for duplicate name and department in waiting list
        for sev, _, n, dept in self.controller.scheduler.get_waiting_list():
            if n == name and dept == department:
                messagebox.showerror("Duplicate Error", f"An appointment for {name} in {department} already exists.")
                return
        # Add patient with department information
        self.controller.scheduler.add_patient(name, int(severity), department)
        self.controller.analytics.add_patient_visit(department, int(severity))
        messagebox.showinfo("Success", f"Appointment booked for {name} in {department}")
        # Clear entries
        for entry in self.entries.values():
            if isinstance(entry, ttk.Entry):
                entry.delete(0, tk.END)
        self.refresh_lists()
        self.controller.frames[HomePage].refresh_stats()
        self.controller.frames[AnalyticsPage].update_analytics()

    def serve_patient(self):
        result = self.controller.scheduler.serve_patient()
        # Also decrement analytics severity count
        # (Handled in HospitalScheduler.serve_patient if analytics is set)
        messagebox.showinfo("Serving Patient", result)
        self.refresh_lists()
        self.controller.frames[HomePage].refresh_stats()
        self.controller.frames[AnalyticsPage].update_analytics()

    def refresh_lists(self):
        # Update department list first
        self.update_department_list()
        
        # Clear existing items
        for item in self.waiting_tree.get_children():
            self.waiting_tree.delete(item)
        for item in self.served_tree.get_children():
            self.served_tree.delete(item)
        
        # Add waiting patients with their departments
        for severity, _, name, department in self.controller.scheduler.get_waiting_list():  # Modified to include department
            self.waiting_tree.insert('', 'end', values=(name, severity, department))
        
        # Add served patients with their departments
        for name, severity, department, timestamp in self.controller.scheduler.get_served_list():  # Modified to include department
            self.served_tree.insert('', 'end', values=(
                name,
                severity,
                department,
                timestamp.strftime("%H:%M:%S") if isinstance(timestamp, datetime) else timestamp
            ))

    def clear_appointment_history(self):
        # Clear scheduler's waiting and served lists
        self.controller.scheduler.pq = []
        self.controller.scheduler.served_patients = []
        self.controller.scheduler.counter = 0
        self.controller.scheduler.save_appointments()
        # Reset analytics
        self.controller.analytics.severity_counts = {i: 0 for i in range(1, 11)}
        self.controller.analytics.save_analytics()
        self.refresh_lists()
        self.controller.frames[HomePage].refresh_stats()
        self.controller.frames[AnalyticsPage].update_analytics()
        messagebox.showinfo("Cleared", "All appointment history and analytics have been cleared.")

# ---------------------------
# Patient Management Page
# ---------------------------
class PatientManagementPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(background=self.controller.style.bg_color)
        
        # Create main content frame
        content_frame = ttk.Frame(self)
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title = ttk.Label(content_frame,
                         text="Patient Management",
                         style="Header.TLabel")
        title.pack(pady=(0, 20))
        
        # Create two columns
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=(0, 10))
        
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill='both', expand=True, padx=(10, 0))

        # Patient Registration Form
        form_frame = ttk.LabelFrame(left_frame, text="Patient Registration")
        form_frame.pack(fill='both', expand=True, pady=(0, 10))

        fields = ['Name', 'Age', 'Gender', 'Contact', 'Blood Type', 'Medical History']
        self.patient_entries = {}
        self.gender_var = tk.StringVar(value='Male')
        self.bloodtype_var = tk.StringVar(value='A+')
        blood_types = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
        for i, field in enumerate(fields):
            field_frame = ttk.Frame(form_frame)
            field_frame.pack(fill='x', padx=10, pady=5)
            ttk.Label(field_frame,
                     text=field + ":",
                     style="Subheader.TLabel").pack(side=tk.LEFT, padx=5)
            if field == 'Gender':
                gender_frame = ttk.Frame(field_frame)
                gender_frame.pack(side=tk.RIGHT, fill='x', expand=True, padx=5)
                ttk.Radiobutton(gender_frame, text='Male', variable=self.gender_var, value='Male').pack(side=tk.LEFT, padx=2)
                ttk.Radiobutton(gender_frame, text='Female', variable=self.gender_var, value='Female').pack(side=tk.LEFT, padx=2)
                self.patient_entries[field] = self.gender_var
            elif field == 'Blood Type':
                bloodtype_combo = ttk.Combobox(field_frame, textvariable=self.bloodtype_var, values=blood_types, state='readonly')
                bloodtype_combo.pack(side=tk.RIGHT, fill='x', expand=True, padx=5)
                self.patient_entries[field] = self.bloodtype_var
            else:
                entry = ttk.Entry(field_frame)
                entry.pack(side=tk.RIGHT, fill='x', expand=True, padx=5)
                self.patient_entries[field] = entry

        # Register button
        ttk.Button(form_frame,
                  text="Register Patient",
                  command=self.register_patient,
                  style="Success.TButton").pack(pady=10)
        
        # List of registered patients
        list_frame = ttk.LabelFrame(right_frame, text="Registered Patients")
        list_frame.pack(fill='both', expand=True)
        
        # Create Treeview for patients
        self.patient_tree = ttk.Treeview(list_frame,
                                       columns=('Name', 'Age', 'Gender', 'Contact'),
                                       show='headings')
        
        # Configure columns
        self.patient_tree.heading('Name', text='Name')
        self.patient_tree.heading('Age', text='Age')
        self.patient_tree.heading('Gender', text='Gender')
        self.patient_tree.heading('Contact', text='Contact')
        
        # Set column widths
        self.patient_tree.column('Name', width=150)
        self.patient_tree.column('Age', width=50)
        self.patient_tree.column('Gender', width=80)
        self.patient_tree.column('Contact', width=120)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.patient_tree.yview)
        self.patient_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack tree and scrollbar
        self.patient_tree.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.pack(side=tk.RIGHT, fill='y')
        
        # Delete button
        ttk.Button(right_frame,
                  text="Delete Selected Patient",
                  command=self.delete_selected_patient,
                  style="Error.TButton").pack(pady=10)

        # Load patient list on startup
        self.refresh_patient_list()
        
        # Add hover effects
        self.bind_events()
    
    def bind_events(self):
        # Add hover effects to buttons
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.bind("<Enter>", lambda e: e.widget.state(['pressed']))
                widget.bind("<Leave>", lambda e: e.widget.state(['!pressed']))

    def register_patient(self):
        patient_data = {}
        for field, entry in self.patient_entries.items():
            if field in ['Gender', 'Blood Type']:
                patient_data[field] = entry.get()
            else:
                patient_data[field] = entry.get()
        if not patient_data['Name'] or not patient_data['Age'] or not patient_data['Gender']:
            messagebox.showerror("Error", "Please fill in the required fields: Name, Age, and Gender")
            return
        patient_data["Admission Date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        added = self.controller.patient_db.add_patient(patient_data)
        if added:
            messagebox.showinfo("Success", f"Patient {patient_data['Name']} registered successfully!")
            # Clear entries
            for field, entry in self.patient_entries.items():
                if field == 'Gender':
                    self.gender_var.set('Male')
                elif field == 'Blood Type':
                    self.bloodtype_var.set('A+')
                else:
                    entry.delete(0, tk.END)
            self.refresh_patient_list()
            # Refresh home page stats
            self.controller.frames[HomePage].refresh_stats()

    def refresh_patient_list(self):
        # Clear existing items
        for item in self.patient_tree.get_children():
            self.patient_tree.delete(item)
        
        # Add patients to treeview
        for patient in self.controller.patient_db.get_all_patients():
            self.patient_tree.insert('', 'end', values=(
                patient['Name'],
                patient['Age'],
                patient['Gender'],
                patient['Contact']
            ))

    def delete_selected_patient(self):
        selected = self.patient_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a patient to delete.")
            return
        deleted_any = False
        for sel in selected:
            patient_name = self.patient_tree.item(sel)['values'][0]
            confirm = messagebox.askyesno("Confirm Delete",
                                        f"Are you sure you want to delete patient {patient_name}?")
            if confirm:
                self.controller.patient_db.delete_patient(patient_name)
                deleted_any = True
        if deleted_any:
            messagebox.showinfo("Deleted", "Selected patient(s) have been deleted.")
            self.refresh_patient_list()
            # Refresh home page stats
            self.controller.frames[HomePage].refresh_stats()

# ---------------------------
# Emergency Alerts Page (Creative Version)
# ---------------------------
class EmergencyAlertsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        title = ttk.Label(self, text="Emergency Alerts", font=("Arial", 20))
        title.pack(pady=10)

        # Flash label to show dynamic messages
        self.flash_label = ttk.Label(self, text="", font=("Arial", 16))
        self.flash_label.pack(pady=5)

        # Controls to raise an alert
        control_frame = ttk.LabelFrame(self, text="Raise Alert")
        control_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(control_frame, text="Alert Code:").grid(row=0, column=0, padx=5, pady=5)
        self.alert_code = ttk.Combobox(control_frame, values=list(controller.emergency.alert_config.keys()), state='readonly')
        self.alert_code.grid(row=0, column=1, padx=5, pady=5)
        if controller.emergency.alert_config:
            self.alert_code.set(list(controller.emergency.alert_config.keys())[0])

        ttk.Label(control_frame, text="Location:").grid(row=1, column=0, padx=5, pady=5)
        self.alert_location = ttk.Entry(control_frame)
        self.alert_location.grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(control_frame, text="Raise Alert", command=self.raise_emergency)\
            .grid(row=2, column=0, columnspan=2, pady=10)

        # Buttons to clear alerts
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(btn_frame, text="Clear Selected Alert", command=self.clear_selected_alert)\
            .pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear All Alerts", command=self.clear_all_alerts)\
            .pack(side=tk.LEFT, padx=5)

        # Active Alerts Display
        self.alerts_frame = ttk.LabelFrame(self, text="Active Alerts")
        self.alerts_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.alerts_tree = ttk.Treeview(self.alerts_frame,
                                        columns=('Code', 'Description', 'Location', 'Time'),
                                        show='headings')
        self.alerts_tree.heading('Code', text='Code')
        self.alerts_tree.heading('Description', text='Description')
        self.alerts_tree.heading('Location', text='Location')
        self.alerts_tree.heading('Time', text='Time')
        self.alerts_tree.pack(fill='both', expand=True, padx=5, pady=5)

        # Setup treeview tags dynamically based on the alert configuration
        self.update_tree_tags()

        # Back to Home button
        ttk.Button(self, text="Back to Home", command=lambda: controller.show_frame(HomePage))\
            .pack(pady=10)

        # Show alerts on startup
        self.show_alerts_on_startup()

    def show_alerts_on_startup(self):
        # Show all currently active alerts (if any) in the table
        self.update_emergency_display()

    def update_tree_tags(self):
        # Clear existing tags and set new ones based on alert_config colors
        for code, config in self.controller.emergency.alert_config.items():
            self.alerts_tree.tag_configure(code, background=config.get("color", "white"))

    def raise_emergency(self):
        code = self.alert_code.get()
        location = self.alert_location.get()
        if code and location:
            self.controller.emergency.raise_alert(code, location)
            self.update_emergency_display()
            # Display a flash message in the configured color
            color = self.controller.emergency.alert_config.get(code, {}).get("color", "red")
            self.flash_label.config(text=f"{code} alert raised!", foreground=color)
            self.after(3000, lambda: self.flash_label.config(text=""))
            messagebox.showwarning("Emergency Alert", f"{code} alert raised for {location}!")
            # Refresh HomePage stats
            self.controller.frames[HomePage].refresh_stats()
        else:
            messagebox.showerror("Error", "Please fill in all fields!")

    def update_emergency_display(self):
        # Clear the treeview
        for item in self.alerts_tree.get_children():
            self.alerts_tree.delete(item)
        # Insert each active alert with its color tag
        for alert in self.controller.emergency.active_alerts:
            tag = alert['code'] if alert['code'] in self.controller.emergency.alert_config else ""
            self.alerts_tree.insert('', 'end', values=(
                alert['code'],
                alert['description'],
                alert['location'],
                alert['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            ), tags=(tag,))
        self.update_tree_tags()

    def clear_selected_alert(self):
        selected = self.alerts_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select an alert to clear.")
            return
        # Retrieve details of the selected alert
        item = self.alerts_tree.item(selected[0])
        code = item['values'][0]
        location = item['values'][2]
        # Find and remove the corresponding alert from the active alerts list
        for i, alert in enumerate(self.controller.emergency.active_alerts):
            if alert['code'] == code and alert['location'] == location:
                self.controller.emergency.clear_alert(i)
                break
        self.update_emergency_display()
        messagebox.showinfo("Cleared", "Selected alert has been cleared.")
        # Refresh HomePage stats
        self.controller.frames[HomePage].refresh_stats()

    def clear_all_alerts(self):
        self.controller.emergency.active_alerts = []
        self.update_emergency_display()
        messagebox.showinfo("Cleared", "All alerts have been cleared.")
        # Refresh HomePage stats
        self.controller.frames[HomePage].refresh_stats()

# ---------------------------
# Alert Configuration Page
# ---------------------------
class AlertConfigPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        title = ttk.Label(self, text="Alert Configuration", font=("Arial", 20))
        title.pack(pady=10)

        # Form for adding/updating an alert configuration
        form_frame = ttk.LabelFrame(self, text="Add/Update Alert Configuration")
        form_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(form_frame, text="Alert Code:").grid(row=0, column=0, padx=5, pady=5)
        self.code_entry = ttk.Entry(form_frame)
        self.code_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="Description:").grid(row=1, column=0, padx=5, pady=5)
        self.desc_entry = ttk.Entry(form_frame)
        self.desc_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(form_frame, text="Color:").grid(row=2, column=0, padx=5, pady=5)
        self.color_entry = ttk.Entry(form_frame)
        self.color_entry.grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(form_frame, text="Choose Color", command=self.choose_color).grid(row=2, column=2, padx=5, pady=5)

        ttk.Button(form_frame, text="Add/Update Configuration", command=self.add_update_config)\
            .grid(row=3, column=0, columnspan=3, pady=10)

        # List of current alert configurations
        list_frame = ttk.LabelFrame(self, text="Current Alert Configurations")
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        self.config_listbox = tk.Listbox(list_frame)
        self.config_listbox.pack(fill='both', expand=True, padx=5, pady=5)

        ttk.Button(self, text="Delete Selected Configuration", command=self.delete_selected_config)\
            .pack(pady=5)

        # Back to Home button
        ttk.Button(self, text="Back to Home", command=lambda: controller.show_frame(HomePage)).pack(pady=10)

        # Load existing configurations
        self.refresh_config_list()

    def choose_color(self):
        # Open a color chooser and update the color entry
        color_code = colorchooser.askcolor(title="Choose color")[1]
        if color_code:
            self.color_entry.delete(0, tk.END)
            self.color_entry.insert(0, color_code)

    def add_update_config(self):
        code = self.code_entry.get().strip()
        desc = self.desc_entry.get().strip()
        color = self.color_entry.get().strip()
        if not code or not desc or not color:
            messagebox.showerror("Error", "Please fill in all fields.")
            return
        # Update the emergency alert configuration dynamically
        self.controller.emergency.alert_config[code] = {"description": desc, "color": color}
        messagebox.showinfo("Success", f"Configuration for {code} added/updated.")
        self.refresh_config_list()
        # Clear entries
        self.code_entry.delete(0, tk.END)
        self.desc_entry.delete(0, tk.END)
        self.color_entry.delete(0, tk.END)

    def refresh_config_list(self):
        self.config_listbox.delete(0, tk.END)
        for code, config in self.controller.emergency.alert_config.items():
            self.config_listbox.insert(tk.END, f"{code}: {config['description']} - {config['color']}")

    def delete_selected_config(self):
        selected = self.config_listbox.curselection()
        if not selected:
            messagebox.showerror("Error", "Please select a configuration to delete.")
            return
        index = selected[0]
        config_str = self.config_listbox.get(index)
        # Assume the alert code is the first part before the colon
        alert_code = config_str.split(":")[0]
        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete configuration for {alert_code}?")
        if confirm:
            if alert_code in self.controller.emergency.alert_config:
                del self.controller.emergency.alert_config[alert_code]
            messagebox.showinfo("Deleted", f"Configuration for {alert_code} has been deleted.")
            self.refresh_config_list()
            # Also update the alerts page tags if necessary
            self.controller.frames[EmergencyAlertsPage].update_tree_tags()

# ---------------------------
# Analytics Page
# ---------------------------
class AnalyticsPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(background=self.controller.style.bg_color)
        
        # Create main content frame
        content_frame = ttk.Frame(self)
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title = ttk.Label(content_frame,
                         text="Patient Severity Analytics",
                         style="Header.TLabel")
        title.pack(pady=(0, 20))
        
        # Create matplotlib figure
        self.fig = plt.Figure(figsize=(10, 6))
        self.fig.patch.set_facecolor(self.controller.style.bg_color)
        
        # Create subplot
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('white')
        self.ax.grid(True, linestyle='--', alpha=0.7)
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        
        # Create canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=content_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        # Add statistics frame
        stats_frame = ttk.LabelFrame(content_frame, text="Statistics")
        stats_frame.pack(fill='x', pady=(20, 0))
        
        # Statistics labels
        self.total_patients = ttk.Label(stats_frame, text="Total Patients: 0")
        self.total_patients.pack(side=tk.LEFT, padx=20, pady=10)
        
        self.avg_severity = ttk.Label(stats_frame, text="Average Severity: 0.0")
        self.avg_severity.pack(side=tk.LEFT, padx=20, pady=10)
        
        self.max_severity = ttk.Label(stats_frame, text="Max Severity: 0")
        self.max_severity.pack(side=tk.LEFT, padx=20, pady=10)
        
        # Initial update
        self.update_analytics()

    def update_analytics(self):
        # Clear subplot
        self.ax.clear()
        
        # Get severity data
        severity_data = self.controller.analytics.generate_severity_report()
        
        # Create bar chart
        bars = self.ax.bar(list(severity_data.keys()),
                          list(severity_data.values()),
                          color=self.controller.style.secondary_color,
                          alpha=0.7,
                          width=0.6)
        
        # Customize chart
        self.ax.set_title('Patient Distribution by Severity Level', 
                         pad=20, 
                         fontsize=14, 
                         fontweight='bold')
        self.ax.set_xlabel('Severity Level', fontsize=12)
        self.ax.set_ylabel('Number of Patients', fontsize=12)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            self.ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}',
                        ha='center', va='bottom',
                        fontsize=10)
        
        # Set y-axis to only show integers
        self.ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        
        # Add grid
        self.ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Update statistics
        total = sum(severity_data.values())
        avg = sum(k * v for k, v in severity_data.items()) / total if total > 0 else 0
        max_sev = max(severity_data.keys()) if severity_data else 0
        
        self.total_patients.config(text=f"Total Patients: {total}")
        self.avg_severity.config(text=f"Average Severity: {avg:.1f}")
        self.max_severity.config(text=f"Max Severity: {max_sev}")
        
        # Adjust layout
        self.fig.tight_layout()
        
        # Redraw canvas
        self.canvas.draw()

# ---------------------------
# Department Management Page
# ---------------------------
class DepartmentManagementPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.configure(background=self.controller.style.bg_color)
        
        # Create main content frame
        content_frame = ttk.Frame(self)
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Title
        title = ttk.Label(content_frame,
                         text="Department Management",
                         style="Header.TLabel")
        title.pack(pady=(0, 20))
        
        # Create two columns
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=(0, 10))
        
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill='both', expand=True, padx=(10, 0))
        
        # Department Form
        form_frame = ttk.LabelFrame(left_frame, text="Add Department")
        form_frame.pack(fill='x', pady=(0, 10))
        
        # Department Name
        name_frame = ttk.Frame(form_frame)
        name_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(name_frame,
                 text="Department Name:",
                 style="Subheader.TLabel").pack(side=tk.LEFT, padx=5)
        
        self.name_entry = ttk.Entry(name_frame)
        self.name_entry.pack(side=tk.RIGHT, fill='x', expand=True, padx=5)
        
        # Capacity
        capacity_frame = ttk.Frame(form_frame)
        capacity_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(capacity_frame,
                 text="Capacity:",
                 style="Subheader.TLabel").pack(side=tk.LEFT, padx=5)
        
        self.capacity_entry = ttk.Entry(capacity_frame)
        self.capacity_entry.pack(side=tk.RIGHT, fill='x', expand=True, padx=5)
        
        # Add Department button
        ttk.Button(form_frame,
                  text="Add Department",
                  command=self.add_department,
                  style="Success.TButton").pack(pady=10)
        
        # Department List
        list_frame = ttk.LabelFrame(right_frame, text="Departments")
        list_frame.pack(fill='both', expand=True)
        
        # Create Treeview
        self.dept_tree = ttk.Treeview(list_frame,
                                    columns=('Name', 'Capacity', 'Current'),
                                    show='headings')
        self.dept_tree.heading('Name', text='Department Name')
        self.dept_tree.heading('Capacity', text='Capacity')
        self.dept_tree.heading('Current', text='Current Patients')
        self.dept_tree.column('Name', width=150)
        self.dept_tree.column('Capacity', width=100)
        self.dept_tree.column('Current', width=100)
        # Set text color to black for all rows and headings
        style = ttk.Style()
        style.configure('Dept.Treeview', foreground='black', font=('Segoe UI', 10))
        style.configure('Dept.Treeview.Heading', foreground='black', font=('Segoe UI', 10, 'bold'))
        self.dept_tree.configure(style='Dept.Treeview')
        self.dept_tree.tag_configure('black_fg', foreground='black')
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.dept_tree.yview)
        self.dept_tree.configure(yscrollcommand=scrollbar.set)
        self.dept_tree.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar.pack(side=tk.RIGHT, fill='y')
        
        # Update Capacity Section
        update_frame = ttk.LabelFrame(right_frame, text="Update Department Capacity")
        update_frame.pack(fill='x', pady=(10, 0))
        ttk.Label(update_frame, text="Selected Department:").grid(row=0, column=0, padx=5, pady=5)
        self.selected_dept_var = tk.StringVar()
        self.selected_dept_entry = ttk.Entry(update_frame, textvariable=self.selected_dept_var, state='readonly')
        self.selected_dept_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(update_frame, text="New Capacity:").grid(row=1, column=0, padx=5, pady=5)
        self.new_capacity_entry = ttk.Entry(update_frame)
        self.new_capacity_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(update_frame, text="Update Capacity", command=self.update_capacity, style="Success.TButton").grid(row=2, column=0, columnspan=2, pady=8)
        self.dept_tree.bind('<<TreeviewSelect>>', self.on_dept_select)

        # Delete button
        ttk.Button(right_frame,
                  text="Delete Selected Department",
                  command=self.delete_department,
                  style="Error.TButton").pack(pady=10)
        
        # Initial refresh
        self.refresh_departments()
    
    def add_department(self):
        name = self.name_entry.get().strip()
        capacity = self.capacity_entry.get().strip()
        
        if not name or not capacity.isdigit():
            messagebox.showerror("Error", "Please enter valid department name and capacity")
            return
        
        try:
            self.controller.department_mgr.add_department(name, int(capacity))
            messagebox.showinfo("Success", f"Department {name} added successfully!")
            
            # Clear entries
            self.name_entry.delete(0, tk.END)
            self.capacity_entry.delete(0, tk.END)
            
            self.refresh_departments()
            # Refresh home page stats
            self.controller.frames[HomePage].refresh_stats()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
    
    def delete_department(self):
        selected = self.dept_tree.selection()
        if not selected:
            messagebox.showerror("Error", "Please select a department to delete")
            return
        
        dept_name = self.dept_tree.item(selected[0])['values'][0]
        
        confirm = messagebox.askyesno("Confirm Delete",
                                    f"Are you sure you want to delete department {dept_name}?")
        if confirm:
            try:
                self.controller.department_mgr.delete_department(dept_name)
                messagebox.showinfo("Success", f"Department {dept_name} deleted successfully!")
                self.refresh_departments()
                # Refresh home page stats
                self.controller.frames[HomePage].refresh_stats()
            except ValueError as e:
                messagebox.showerror("Error", str(e))
    
    def refresh_departments(self):
        # Clear existing items
        for item in self.dept_tree.get_children():
            self.dept_tree.delete(item)
        
        # Add departments to treeview
        status = self.controller.department_mgr.get_department_status()
        for name, info in status.items():
            self.dept_tree.insert('', 'end', values=(
                name,
                info['capacity'],
                f"{info['current_patients']} ({info['occupancy_rate']:.1f}%)"
            ), tags=('black_fg',))

    def on_dept_select(self, event):
        selected = self.dept_tree.selection()
        if selected:
            dept_name = self.dept_tree.item(selected[0])['values'][0]
            self.selected_dept_var.set(dept_name)
        else:
            self.selected_dept_var.set("")

    def update_capacity(self):
        dept_name = self.selected_dept_var.get()
        new_capacity = self.new_capacity_entry.get().strip()
        if not dept_name:
            messagebox.showerror("Error", "Please select a department to update.")
            return
        if not new_capacity.isdigit():
            messagebox.showerror("Error", "Please enter a valid new capacity.")
            return
        try:
            self.controller.department_mgr.update_department(dept_name, int(new_capacity))
            messagebox.showinfo("Success", f"Capacity for {dept_name} updated to {new_capacity}.")
            self.new_capacity_entry.delete(0, tk.END)
            self.refresh_departments()
            self.controller.frames[HomePage].refresh_stats()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

# ---------------------------
# Main Entry Point
# ---------------------------
if __name__ == "__main__":
    app = HospitalManagementApp()
    app.mainloop()
