// ── ORION SCHOOL MANAGEMENT SYSTEM - SPA FRONTEND CONTROLLER ──

const API_BASE = ""; // Relative to server
let currentToken = localStorage.getItem("orion_token") || null;
let currentUser = null;
let currentBranchId = null;
let currentBranchName = null;
let activeTheme = localStorage.getItem("orion_theme") || "dark";
let enrollmentChart = null;
let attendanceChart = null;
let billingChart = null;

// --- 1. Startup & Initialization ---
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initAppRouting();
    initGlobalEventListeners();
    checkSetupAndVerifyAuth();
});

function initTheme() {
    if (activeTheme === "light") {
        document.body.classList.remove("dark-theme");
        document.body.classList.add("light-theme");
        document.getElementById("btn-theme-toggle").innerHTML = '<i class="fa-solid fa-sun"></i>';
    } else {
        document.body.classList.add("dark-theme");
        document.body.classList.remove("light-theme");
        document.getElementById("btn-theme-toggle").innerHTML = '<i class="fa-solid fa-moon"></i>';
    }
}

function checkSetupAndVerifyAuth() {
    fetch("/api/setup/status")
        .then(res => res.json())
        .then(data => {
            if (!data.setup_completed) {
                showView("view-setup");
                initSetupWizard();
            } else {
                if (currentToken) {
                    parseTokenAndRoute();
                } else {
                    showView("view-login");
                    loadBranchSelector();
                }
            }
        })
        .catch(err => {
            showToast("Failed to connect to backend api", "error");
            console.error("Connection error:", err);
        });
}

// --- 2. Security & Routing ---
function showView(viewId) {
    document.querySelectorAll(".view-panel").forEach(panel => {
        panel.classList.remove("active");
    });
    const target = document.getElementById(viewId);
    if (target) {
        target.classList.add("active");
    }
}

function parseTokenAndRoute() {
    try {
        const payload = JSON.parse(atob(currentToken.split(".")[1]));
        const now = Math.floor(Date.now() / 1000);
        if (payload.exp && payload.exp < now) {
            handleLogout();
            return;
        }
        
        currentUser = payload;
        currentBranchId = payload.branch_id;
        currentBranchName = payload.branch_name;
        
        // Update header badges
        document.getElementById("user-display-name").innerText = payload.full_name || payload.username;
        document.getElementById("user-display-role").innerText = payload.role;
        
        if (payload.role === "System Admin") {
            document.getElementById("header-branch-badge").style.display = "none";
            document.getElementById("header-academic-badge").style.display = "none";
            document.getElementById("sidebar-sysadmin-link").style.display = "block";
            // Show system admin panel
            showView("view-main-layout");
            switchPanel("panel-sysadmin");
        } else {
            document.getElementById("header-branch-badge").style.display = "inline-flex";
            document.getElementById("header-branch-badge").innerHTML = `<i class="fa-solid fa-code-branch"></i> ${currentBranchName}`;
            document.getElementById("header-academic-badge").style.display = "inline-flex";
            document.getElementById("sidebar-sysadmin-link").style.display = "none";
            
            showView("view-main-layout");
            switchPanel("panel-dashboard");
        }
    } catch (e) {
        console.error("Token parsing error:", e);
        handleLogout();
    }
}

function switchPanel(panelId) {
    document.querySelectorAll(".content-panel").forEach(panel => {
        panel.classList.remove("active");
    });
    
    document.querySelectorAll(".nav-link").forEach(link => {
        link.classList.remove("active");
        if (link.getAttribute("data-target") === panelId) {
            link.classList.add("active");
        }
    });
    
    const targetPanel = document.getElementById(panelId);
    if (targetPanel) {
        targetPanel.classList.add("active");
        // Load data specific to this panel
        loadPanelData(panelId);
    }
}

function initAppRouting() {
    document.querySelectorAll(".nav-link").forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            const panelId = link.getAttribute("data-target");
            switchPanel(panelId);
        });
    });
}

// --- 3. API Connector Wrapper ---
async function apiFetch(url, options = {}) {
    if (!options.headers) {
        options.headers = {};
    }
    if (currentToken) {
        options.headers["Authorization"] = `Bearer ${currentToken}`;
    }
    if (options.body && !(options.body instanceof FormData) && typeof options.body === "object") {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(options.body);
    }
    
    const response = await fetch(url, options);
    if (response.status === 401) {
        handleLogout();
        throw new Error("Unauthorized access. Logged out.");
    }
    if (!response.ok) {
        const errData = await response.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(errData.detail || "API request failed");
    }
    return response.json();
}

// --- 4. Global Events & Theme ---
function initGlobalEventListeners() {
    // Theme Switcher
    document.getElementById("btn-theme-toggle").addEventListener("click", () => {
        if (document.body.classList.contains("dark-theme")) {
            document.body.classList.remove("dark-theme");
            document.body.classList.add("light-theme");
            localStorage.setItem("orion_theme", "light");
            document.getElementById("btn-theme-toggle").innerHTML = '<i class="fa-solid fa-sun"></i>';
        } else {
            document.body.classList.add("dark-theme");
            document.body.classList.remove("light-theme");
            localStorage.setItem("orion_theme", "dark");
            document.getElementById("btn-theme-toggle").innerHTML = '<i class="fa-solid fa-moon"></i>';
        }
    });
    
    // Profile menu trigger
    const profileTrigger = document.getElementById("profile-info-trigger");
    const dropdownMenu = document.getElementById("profile-dropdown-menu");
    profileTrigger.addEventListener("click", (e) => {
        e.stopPropagation();
        dropdownMenu.classList.toggle("show");
    });
    
    document.addEventListener("click", () => {
        dropdownMenu.classList.remove("show");
    });
    
    // Logout
    document.getElementById("btn-logout").addEventListener("click", (e) => {
        e.preventDefault();
        handleLogout();
    });
    
    // Login form submit
    document.getElementById("login-form").addEventListener("submit", handleLoginSubmit);
    
    // Sysadmin toggle on login card
    const sysadminToggle = document.getElementById("link-sysadmin-toggle");
    sysadminToggle.addEventListener("click", () => {
        const branchGroup = document.getElementById("login-branch-group");
        if (branchGroup.style.display === "none") {
            branchGroup.style.display = "block";
            sysadminToggle.innerText = "Login as System Administrator";
            document.getElementById("login-branch").setAttribute("required", "required");
        } else {
            branchGroup.style.display = "none";
            sysadminToggle.innerText = "Login as Regular Branch Staff";
            document.getElementById("login-branch").removeAttribute("required");
        }
    });
    
    // Open Setup wizard from login page
    document.getElementById("link-setup-wizard").addEventListener("click", () => {
        showView("view-setup");
        initSetupWizard();
    });
    
    // Modals generic close controls
    document.querySelectorAll(".modal-close, .btn-modal-cancel").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            btn.closest(".modal").classList.remove("show");
        });
    });
    
    initBulkUploadFeatures();
}

function handleLogout() {
    currentToken = null;
    currentUser = null;
    currentBranchId = null;
    currentBranchName = null;
    localStorage.removeItem("orion_token");
    showView("view-login");
    loadBranchSelector();
    showToast("Signed out successfully", "info");
}

function handleLoginSubmit(e) {
    e.preventDefault();
    const branchSelect = document.getElementById("login-branch");
    const branchVisible = document.getElementById("login-branch-group").style.display !== "none";
    
    const payload = {
        username: document.getElementById("login-username").value,
        password: document.getElementById("login-password").value,
        branch_id: (branchVisible && branchSelect.value) ? parseInt(branchSelect.value) : null
    };
    
    fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
    .then(res => {
        if (!res.ok) throw new Error("Invalid username or password");
        return res.json();
    })
    .then(data => {
        currentToken = data.token;
        localStorage.setItem("orion_token", currentToken);
        showToast("Signed in successfully", "success");
        parseTokenAndRoute();
        // Clear inputs
        document.getElementById("login-username").value = "";
        document.getElementById("login-password").value = "";
    })
    .catch(err => {
        showToast(err.message, "error");
    });
}

function loadBranchSelector() {
    fetch("/api/auth/branches")
        .then(res => res.json())
        .then(branches => {
            const select = document.getElementById("login-branch");
            select.innerHTML = '<option value="">— Select branch —</option>';
            branches.forEach(b => {
                select.innerHTML += `<option value="${b.id}">${b.name}</option>`;
            });
        });
}

// --- 5. Setup Wizard Flow ---
function initSetupWizard() {
    const steps = document.querySelectorAll(".setup-step");
    const progressDots = document.querySelectorAll(".progress-dot");
    let currentStep = 1;
    
    document.querySelectorAll(".btn-next").forEach(btn => {
        btn.addEventListener("click", () => {
            // Simple validation
            const inputs = steps[currentStep - 1].querySelectorAll("input[required]");
            let valid = true;
            inputs.forEach(i => { if(!i.value) valid = false; });
            
            if(!valid) {
                showToast("Please fill in all required fields", "error");
                return;
            }
            
            currentStep++;
            updateSetupSteps();
        });
    });
    
    document.querySelectorAll(".btn-prev").forEach(btn => {
        btn.addEventListener("click", () => {
            currentStep--;
            updateSetupSteps();
        });
    });
    
    function updateSetupSteps() {
        steps.forEach((s, idx) => {
            s.classList.toggle("active", idx === (currentStep - 1));
        });
        progressDots.forEach((dot, idx) => {
            dot.classList.toggle("active", idx === (currentStep - 1));
        });
    }
    
    document.getElementById("setup-form").addEventListener("submit", (e) => {
        e.preventDefault();
        const payload = {
            school_name: document.getElementById("setup-school-name").value,
            school_motto: document.getElementById("setup-school-motto").value,
            school_phone: document.getElementById("setup-school-phone").value,
            school_email: document.getElementById("setup-school-email").value,
            school_address: document.getElementById("setup-school-address").value,
            admin_user: document.getElementById("setup-admin-user").value,
            admin_pass: document.getElementById("setup-admin-pass").value,
            academic_year: document.getElementById("setup-acad-year").value,
            term_name: document.getElementById("setup-term-name").value
        };
        
        fetch("/api/setup/execute", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        })
        .then(res => {
            if(!res.ok) throw new Error("Initialization failed");
            return res.json();
        })
        .then(data => {
            showToast("System initialized successfully!", "success");
            // Reroute
            checkSetupAndVerifyAuth();
        })
        .catch(err => {
            showToast(err.message, "error");
        });
    });
}

// --- 6. Panel Data Loaders ---
function loadPanelData(panelId) {
    if (panelId === "panel-dashboard") loadDashboard();
    else if (panelId === "panel-students") loadStudentsPanel();
    else if (panelId === "panel-staff") loadStaff();
    else if (panelId === "panel-academics") loadAcademics();
    else if (panelId === "panel-attendance") loadAttendanceConfig();
    else if (panelId === "panel-exams") loadExams();
    else if (panelId === "panel-fees") loadFees();
    else if (panelId === "panel-library") loadLibrary();
    else if (panelId === "panel-inventory") loadInventory();
    else if (panelId === "panel-communication") loadCommunication();
    else if (panelId === "panel-settings") loadSettings();
    else if (panelId === "panel-sysadmin") loadSysadmin();
}

// --- Dashboard Panel logic ---
function loadDashboard() {
    apiFetch("/api/dashboard/stats")
        .then(data => {
            document.getElementById("stat-students").innerText = data.students;
            document.getElementById("stat-staff").innerText = data.staff;
            document.getElementById("stat-books").innerText = data.books;
            document.getElementById("stat-fees").innerText = data.fees_collected.toFixed(2);
            
            // Role checking for billing details display
            const isTeacher = currentUser && currentUser.role === "Teacher";
            const billingCard = document.getElementById("dashboard-billing-card");
            const activityCard = document.getElementById("dashboard-activity-card");
            
            if (isTeacher) {
                if (billingCard) billingCard.style.display = "none";
                if (activityCard) {
                    activityCard.classList.remove("col-span-1");
                    activityCard.classList.add("col-span-3");
                }
            } else {
                if (billingCard) billingCard.style.display = "block";
                if (activityCard) {
                    activityCard.classList.remove("col-span-3");
                    activityCard.classList.add("col-span-1");
                }
            }

            // Build Graph - Enrollment Distribution
            const ctx = document.getElementById("chart-enrollment").getContext("2d");
            if (enrollmentChart) enrollmentChart.destroy();
            
            const labels = data.class_distribution.map(c => c.class_name);
            const counts = data.class_distribution.map(c => c.count);
            
            enrollmentChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Active Students',
                        data: counts,
                        backgroundColor: 'rgba(59, 130, 246, 0.6)',
                        borderColor: '#3b82f6',
                        borderWidth: 1,
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: { precision: 0 }
                        }
                    }
                }
            });

            // Attendance Pie Chart
            const attCtx = document.getElementById("chart-attendance").getContext("2d");
            if (attendanceChart) attendanceChart.destroy();
            
            const attLabels = ["Present", "Absent", "Late"];
            const attCounts = [
                data.attendance_distribution.Present || 0,
                data.attendance_distribution.Absent || 0,
                data.attendance_distribution.Late || 0
            ];
            
            attendanceChart = new Chart(attCtx, {
                type: 'pie',
                data: {
                    labels: attLabels,
                    datasets: [{
                        data: attCounts,
                        backgroundColor: [
                            'rgba(16, 185, 129, 0.6)', // success green
                            'rgba(239, 68, 68, 0.6)',  // danger red
                            'rgba(245, 158, 11, 0.6)'  // warning amber
                        ],
                        borderColor: [
                            '#10b981',
                            '#ef4444',
                            '#f59e0b'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: activeTheme === 'dark' ? '#f3f4f6' : '#0f172a',
                                font: { family: 'Plus Jakarta Sans', size: 11 }
                            }
                        }
                    }
                }
            });

            // Billing & Collection Chart
            if (!isTeacher && data.billing_stats) {
                const billCtx = document.getElementById("chart-billing").getContext("2d");
                if (billingChart) billingChart.destroy();
                
                billingChart = new Chart(billCtx, {
                    type: 'bar',
                    data: {
                        labels: ["Amount Billed", "Amount Collected", "Amount Outstanding"],
                        datasets: [{
                            data: [
                                data.billing_stats.billed || 0,
                                data.billing_stats.paid || 0,
                                data.billing_stats.outstanding || 0
                            ],
                            backgroundColor: [
                                'rgba(139, 92, 246, 0.6)', // violet
                                'rgba(16, 185, 129, 0.6)', // green
                                'rgba(245, 158, 11, 0.6)'  // amber
                            ],
                            borderColor: [
                                '#8b5cf6',
                                '#10b981',
                                '#f59e0b'
                            ],
                            borderWidth: 1,
                            borderRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            y: {
                                beginAtZero: true
                            }
                        }
                    }
                });
            }
        })
        .catch(err => showToast(err.message, "error"));
        
    apiFetch("/api/dashboard/recent-activity")
        .then(logs => {
            const list = document.getElementById("dashboard-activity-log");
            list.innerHTML = "";
            if (logs.length === 0) {
                list.innerHTML = "<li>No recent activities logged.</li>";
                return;
            }
            logs.forEach(l => {
                list.innerHTML += `
                    <li>
                        <strong>${l.user}</strong>: ${l.action} - ${l.details} 
                        <br><small style="color: var(--text-muted);">${l.time}</small>
                    </li>`;
            });
        })
        .catch(err => showToast(err.message, "error"));
}

// --- Students Panel logic ---
function loadStudentsPanel() {
    // Tab switching
    initTabs("panel-students");
    
    // Load student directories classes filters
    apiFetch("/api/academics/classes")
        .then(classes => {
            const filter = document.getElementById("filter-student-class");
            const admitSelect = document.getElementById("stud-class");
            const srcSelect = document.getElementById("promo-src-class");
            const destSelect = document.getElementById("promo-target-class");
            
            filter.innerHTML = '<option value="">All Classes</option>';
            admitSelect.innerHTML = '<option value="">— Select class —</option>';
            srcSelect.innerHTML = '<option value="">Select source class...</option>';
            destSelect.innerHTML = '<option value="">Select target class...</option>';
            
            classes.forEach(c => {
                const opt = `<option value="${c.id}">${c.name} (${c.stream || "No Stream"})</option>`;
                filter.innerHTML += opt;
                admitSelect.innerHTML += opt;
                srcSelect.innerHTML += opt;
                destSelect.innerHTML += opt;
            });
        });
        
    // Initial students list load
    loadStudentsList();
    
    // Register search/filter listeners
    document.getElementById("search-student-input").addEventListener("input", loadStudentsList);
    document.getElementById("filter-student-class").addEventListener("change", loadStudentsList);
    document.getElementById("filter-student-status").addEventListener("change", loadStudentsList);
    
    // Promos src class listener to show students to promote
    document.getElementById("promo-src-class").addEventListener("change", loadPromoStudentsList);
}

function loadStudentsList() {
    const search = document.getElementById("search-student-input").value;
    const cid = document.getElementById("filter-student-class").value;
    const stat = document.getElementById("filter-student-status").value;
    
    let url = `/api/students?status=${stat}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (cid) url += `&class_id=${cid}`;
    
    apiFetch(url)
        .then(students => {
            const tbody = document.querySelector("#students-table tbody");
            tbody.innerHTML = "";
            if (students.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center">No students found.</td></tr>';
                return;
            }
            students.forEach(s => {
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${s.id}</strong></td>
                        <td>${s.last_name}, ${s.first_name} ${s.other_names || ""}</td>
                        <td>${s.class_name}</td>
                        <td>${s.parent_phone}</td>
                        <td><span class="badge badge-branch">${s.status}</span></td>
                        <td>
                            <div style="display:flex; gap:6px;">
                                <a href="/api/students/${s.id}/id-card" target="_blank" class="btn btn-secondary btn-icon" title="Print ID Card"><i class="fa-solid fa-address-card"></i></a>
                                <a href="/api/students/${s.id}/admission-form" target="_blank" class="btn btn-secondary btn-icon" title="Print Admission Form"><i class="fa-solid fa-file-pdf"></i></a>
                            </div>
                        </td>
                    </tr>`;
            });
        })
        .catch(err => showToast(err.message, "error"));
}

function loadPromoStudentsList() {
    const cid = document.getElementById("promo-src-class").value;
    const tbody = document.querySelector("#promo-students-table tbody");
    if (!cid) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">Select a source class to load students.</td></tr>';
        return;
    }
    
    apiFetch(`/api/students?class_id=${cid}&status=Active`)
        .then(students => {
            tbody.innerHTML = "";
            if (students.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center">No active students in this class.</td></tr>';
                return;
            }
            students.forEach(s => {
                tbody.innerHTML += `
                    <tr>
                        <td><input type="checkbox" class="promo-select" value="${s.id}"></td>
                        <td><strong>${s.id}</strong></td>
                        <td>${s.last_name}, ${s.first_name} ${s.other_names || ""}</td>
                        <td>${s.class_name}</td>
                        <td>${s.status}</td>
                    </tr>`;
            });
        });
}

// Admit student Trigger and modal
document.getElementById("btn-admit-student-trigger").addEventListener("click", () => {
    document.getElementById("modal-admit-student").classList.add("show");
});

document.getElementById("form-admit-student").addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {
        first_name: document.getElementById("stud-fname").value,
        last_name: document.getElementById("stud-lname").value,
        other_names: document.getElementById("stud-onames").value,
        gender: document.getElementById("stud-gender").value,
        dob: document.getElementById("stud-dob").value,
        class_id: parseInt(document.getElementById("stud-class").value),
        parent: {
            first_name: document.getElementById("parent-fname").value,
            last_name: document.getElementById("parent-lname").value,
            phone: document.getElementById("parent-phone").value,
            email: document.getElementById("parent-email").value,
            occupation: document.getElementById("parent-occ").value,
            address: document.getElementById("parent-addr").value
        }
    };
    
    apiFetch("/api/students", {
        method: "POST",
        body: payload
    })
    .then(data => {
        showToast("Student admitted successfully!", "success");
        document.getElementById("modal-admit-student").classList.remove("show");
        document.getElementById("form-admit-student").reset();
        loadStudentsList();
    })
    .catch(err => showToast(err.message, "error"));
});

// Promos check-all selector
document.getElementById("promo-select-all").addEventListener("change", (e) => {
    document.querySelectorAll(".promo-select").forEach(cb => {
        cb.checked = e.target.checked;
    });
});

// Execute Bulk Promo
document.getElementById("btn-execute-promo").addEventListener("click", () => {
    const targetCid = document.getElementById("promo-target-class").value;
    if (!targetCid) {
        showToast("Please select a target class", "error");
        return;
    }
    const checked = Array.from(document.querySelectorAll(".promo-select:checked")).map(cb => cb.value);
    if (checked.length === 0) {
        showToast("Please select at least one student to promote", "error");
        return;
    }
    
    apiFetch("/api/students/bulk-promote", {
        method: "POST",
        body: { student_ids: checked, target_class_id: parseInt(targetCid) }
    })
    .then(data => {
        showToast(`Successfully promoted ${data.count} students!`, "success");
        loadPromoStudentsList();
        loadStudentsList();
    })
    .catch(err => showToast(err.message, "error"));
});

// Bulk Withdraw
document.getElementById("btn-execute-withdraw").addEventListener("click", () => {
    const checked = Array.from(document.querySelectorAll(".promo-select:checked")).map(cb => cb.value);
    if (checked.length === 0) {
        showToast("Please select at least one student to withdraw", "error");
        return;
    }
    
    if (!confirm("Are you sure you want to mark these students as Withdrawn?")) return;
    
    apiFetch("/api/students/bulk-status", {
        method: "POST",
        body: { student_ids: checked, status: "Withdrawn" }
    })
    .then(data => {
        showToast(`Successfully marked ${data.count} students as Withdrawn.`, "success");
        loadPromoStudentsList();
        loadStudentsList();
    })
    .catch(err => showToast(err.message, "error"));
});

// --- Staff Panel logic ---
function loadStaff() {
    apiFetch("/api/staff")
        .then(staff => {
            const tbody = document.querySelector("#staff-table tbody");
            tbody.innerHTML = "";
            if (staff.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center">No staff found.</td></tr>';
                return;
            }
            staff.forEach(s => {
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${s.id}</strong></td>
                        <td>${s.last_name}, ${s.first_name}</td>
                        <td><span class="badge badge-academic">${s.role_name}</span></td>
                        <td>${s.email}</td>
                        <td>${s.phone}</td>
                        <td>${s.base_salary.toFixed(2)} GHS</td>
                        <td>
                            <div style="display:flex; gap:6px;">
                                <button class="btn btn-secondary btn-icon btn-reset-staff-pwd" data-id="${s.id}" title="Reset Portal Password"><i class="fa-solid fa-key"></i></button>
                            </div>
                        </td>
                    </tr>`;
            });
            
            // Add handler for reset pwd
            document.querySelectorAll(".btn-reset-staff-pwd").forEach(btn => {
                btn.addEventListener("click", (e) => {
                    const sid = btn.getAttribute("data-id");
                    if (confirm("Reset staff portal password to default 'Orion@123'?")) {
                        apiFetch(`/api/staff/${sid}/reset-password`, { method: "POST" })
                            .then(() => showToast("Password reset to 'Orion@123' successfully", "success"))
                            .catch(err => showToast(err.message, "error"));
                    }
                });
            });
        })
        .catch(err => showToast(err.message, "error"));
}

// Modal Register Staff
document.getElementById("btn-register-staff-trigger").addEventListener("click", () => {
    document.getElementById("modal-register-staff").classList.add("show");
});

document.getElementById("form-register-staff").addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {
        first_name: document.getElementById("staff-fname").value,
        last_name: document.getElementById("staff-lname").value,
        username: document.getElementById("staff-username").value,
        role_name: document.getElementById("staff-role").value,
        email: document.getElementById("staff-email").value,
        phone: document.getElementById("staff-phone").value,
        qualification: document.getElementById("staff-qual").value,
        base_salary: parseFloat(document.getElementById("staff-salary").value)
    };
    
    apiFetch("/api/staff", {
        method: "POST",
        body: payload
    })
    .then(() => {
        showToast("Staff registered successfully", "success");
        document.getElementById("modal-register-staff").classList.remove("show");
        document.getElementById("form-register-staff").reset();
        loadStaff();
    })
    .catch(err => showToast(err.message, "error"));
});

// --- Academics Panel logic ---
function loadAcademics() {
    initTabs("panel-academics");
    
    // Academic Period Subtab
    loadAcademicCalendar();
    
    // Load Classes
    loadClassesList();
    
    // Load Subjects
    loadSubjectsList();
    
    // Load Assignments
    loadAssignmentsList();
}

function loadAcademicCalendar() {
    // Fetch Years
    apiFetch("/api/academics/years")
        .then(years => {
            const list = document.getElementById("list-academic-years");
            const select = document.getElementById("acad-term-year-select");
            list.innerHTML = "";
            select.innerHTML = '<option value="">Select year...</option>';
            
            years.forEach(y => {
                const badge = y.is_current ? '<span class="badge badge-branch">Current</span>' : `<button class="btn btn-secondary btn-xs btn-set-current-year" data-id="${y.id}">Set Active</button>`;
                list.innerHTML += `<li><strong>${y.name}</strong> ${badge}</li>`;
                select.innerHTML += `<option value="${y.id}">${y.name}</option>`;
            });
            
            // Set active listener
            document.querySelectorAll(".btn-set-current-year").forEach(btn => {
                btn.addEventListener("click", () => {
                    const yid = btn.getAttribute("data-id");
                    apiFetch(`/api/academics/years/${yid}/set-current`, { method: "POST" })
                        .then(() => {
                            showToast("Academic year updated successfully", "success");
                            loadAcademicCalendar();
                            // Update header info dynamically
                            checkSetupAndVerifyAuth();
                        });
                });
            });
        });
        
    // Fetch Terms
    apiFetch("/api/academics/terms")
        .then(terms => {
            const list = document.getElementById("list-academic-terms");
            list.innerHTML = "";
            terms.forEach(t => {
                const badge = t.is_current ? '<span class="badge badge-academic">Current</span>' : `<button class="btn btn-secondary btn-xs btn-set-current-term" data-id="${t.id}">Set Active</button>`;
                list.innerHTML += `<li><strong>${t.name}</strong> (${t.year_name}) ${badge}</li>`;
            });
            
            document.querySelectorAll(".btn-set-current-term").forEach(btn => {
                btn.addEventListener("click", () => {
                    const tid = btn.getAttribute("data-id");
                    apiFetch(`/api/academics/terms/${tid}/set-current`, { method: "POST" })
                        .then(() => {
                            showToast("Term updated successfully", "success");
                            loadAcademicCalendar();
                            checkSetupAndVerifyAuth();
                        });
                });
            });
        });
}

document.getElementById("form-add-year").addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {
        name: document.getElementById("acad-year-name").value,
        start_date: document.getElementById("acad-year-start").value,
        end_date: document.getElementById("acad-year-end").value,
        is_current: false
    };
    apiFetch("/api/academics/years", { method: "POST", body: payload })
        .then(() => {
            showToast("Academic year added", "success");
            document.getElementById("form-add-year").reset();
            loadAcademicCalendar();
        })
        .catch(err => showToast(err.message, "error"));
});

document.getElementById("form-add-term").addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {
        academic_year_id: parseInt(document.getElementById("acad-term-year-select").value),
        name: document.getElementById("acad-term-name").value,
        start_date: document.getElementById("acad-term-start").value,
        end_date: document.getElementById("acad-term-end").value,
        is_current: false
    };
    apiFetch("/api/academics/terms", { method: "POST", body: payload })
        .then(() => {
            showToast("Term added", "success");
            document.getElementById("form-add-term").reset();
            loadAcademicCalendar();
        })
        .catch(err => showToast(err.message, "error"));
});

// Classes list loader
function loadClassesList() {
    apiFetch("/api/academics/classes")
        .then(classes => {
            const tbody = document.querySelector("#classes-list-table tbody");
            tbody.innerHTML = "";
            if (classes.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4">No classes registered.</td></tr>';
                return;
            }
            classes.forEach(c => {
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${c.id}</strong></td>
                        <td>${c.name}</td>
                        <td>${c.level}</td>
                        <td>${c.stream}</td>
                    </tr>`;
            });
        });
}

document.getElementById("form-add-class").addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {
        name: document.getElementById("class-name-input").value,
        level: document.getElementById("class-level-select").value,
        stream: document.getElementById("class-stream-input").value
    };
    apiFetch("/api/academics/classes", { method: "POST", body: payload })
        .then(() => {
            showToast("Class created successfully", "success");
            document.getElementById("form-add-class").reset();
            loadClassesList();
        })
        .catch(err => showToast(err.message, "error"));
});

// Subjects list loader
function loadSubjectsList() {
    apiFetch("/api/academics/subjects")
        .then(subjects => {
            const tbody = document.querySelector("#subjects-list-table tbody");
            tbody.innerHTML = "";
            if(subjects.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4">No subjects catalogued.</td></tr>';
                return;
            }
            subjects.forEach(s => {
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${s.id}</strong></td>
                        <td>${s.name}</td>
                        <td>${s.code}</td>
                        <td><span class="badge badge-branch">${s.category}</span></td>
                    </tr>`;
            });
        });
}

document.getElementById("form-add-subject").addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {
        name: document.getElementById("subject-name-input").value,
        code: document.getElementById("subject-code-input").value,
        category: document.getElementById("subject-category-select").value
    };
    apiFetch("/api/academics/subjects", { method: "POST", body: payload })
        .then(() => {
            showToast("Subject added successfully", "success");
            document.getElementById("form-add-subject").reset();
            loadSubjectsList();
        })
        .catch(err => showToast(err.message, "error"));
});

// Assignments list loader
function loadAssignmentsList() {
    // Pull select options first
    apiFetch("/api/staff")
        .then(teachers => {
            const select = document.getElementById("assign-teacher-select");
            select.innerHTML = '<option value="">— Select Teacher —</option>';
            teachers.forEach(t => {
                select.innerHTML += `<option value="${t.id}">${t.last_name}, ${t.first_name}</option>`;
            });
        });
        
    apiFetch("/api/academics/classes")
        .then(classes => {
            const select = document.getElementById("assign-class-select");
            select.innerHTML = '<option value="">— Select Class —</option>';
            classes.forEach(c => {
                select.innerHTML += `<option value="${c.id}">${c.name}</option>`;
            });
        });
        
    apiFetch("/api/academics/subjects")
        .then(subjects => {
            const select = document.getElementById("assign-subject-select");
            select.innerHTML = '<option value="">— Select Subject —</option>';
            subjects.forEach(s => {
                select.innerHTML += `<option value="${s.id}">${s.name}</option>`;
            });
        });
        
    apiFetch("/api/academics/assignments")
        .then(assigns => {
            const tbody = document.querySelector("#assignments-list-table tbody");
            tbody.innerHTML = "";
            if (assigns.length === 0) {
                tbody.innerHTML = '<tr><td colspan="3">No teaching assignments recorded.</td></tr>';
                return;
            }
            assigns.forEach(a => {
                tbody.innerHTML += `
                    <tr>
                        <td>${a.class_name}</td>
                        <td>${a.subject_name}</td>
                        <td><strong>${a.teacher_name}</strong></td>
                    </tr>`;
            });
        });
}

document.getElementById("form-add-assignment").addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {
        teacher_id: parseInt(document.getElementById("assign-teacher-select").value),
        class_id: parseInt(document.getElementById("assign-class-select").value),
        subject_id: parseInt(document.getElementById("assign-subject-select").value)
    };
    apiFetch("/api/academics/assignments", { method: "POST", body: payload })
        .then(() => {
            showToast("Teacher assigned to subject successfully", "success");
            loadAssignmentsList();
        })
        .catch(err => showToast(err.message, "error"));
});

// --- Attendance Panel logic ---
function loadAttendanceConfig() {
    initTabs("panel-attendance");
    
    // Hide/show staff attendance sub-tab based on role
    const isTeacher = currentUser && currentUser.role === "Teacher";
    const staffTabBtn = document.getElementById("tab-btn-staff-att");
    if (staffTabBtn) {
        staffTabBtn.style.display = isTeacher ? "none" : "inline-block";
    }

    apiFetch("/api/academics/classes")
        .then(classes => {
            const select = document.getElementById("att-class-select");
            select.innerHTML = '<option value="">Select Class...</option>';
            
            const repSelect = document.getElementById("rep-att-class-select");
            repSelect.innerHTML = '<option value="">Select Class...</option>';
            
            classes.forEach(c => {
                const opt = `<option value="${c.id}">${c.name}</option>`;
                select.innerHTML += opt;
                repSelect.innerHTML += opt;
            });
        });
        
    const todayStr = new Date().toISOString().substring(0, 10);
    document.getElementById("att-date-input").value = todayStr;
    document.getElementById("staff-att-date-input").value = todayStr;
    
    // Default dates for reports (start of month to today)
    const now = new Date();
    const firstDay = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().substring(0, 10);
    document.getElementById("rep-att-start-date").value = firstDay;
    document.getElementById("rep-att-end-date").value = todayStr;
}

document.getElementById("btn-load-attendance").addEventListener("click", () => {
    const cid = document.getElementById("att-class-select").value;
    const date = document.getElementById("att-date-input").value;
    if (!cid || !date) {
        showToast("Please choose class and date", "error");
        return;
    }
    
    apiFetch(`/api/attendance?class_id=${cid}&date=${date}`)
        .then(records => {
            const form = document.getElementById("attendance-sheet-form");
            const tbody = document.querySelector("#attendance-table tbody");
            tbody.innerHTML = "";
            
            if(records.length === 0) {
                 tbody.innerHTML = '<tr><td colspan="3" class="text-center">No active students in this class.</td></tr>';
                 form.style.display = "block";
                 return;
            }
            
            records.forEach(r => {
                 const presentChecked = r.status === "Present" ? "checked" : "";
                 const absentChecked = r.status === "Absent" ? "checked" : "";
                 const lateChecked = r.status === "Late" ? "checked" : "";
                 tbody.innerHTML += `
                     <tr data-id="${r.student_id}">
                         <td><strong>${r.student_id}</strong></td>
                         <td>${r.student_name}</td>
                         <td>
                             <label style="margin-right:15px;"><input type="radio" name="att-${r.student_id}" value="Present" ${presentChecked}> Present</label>
                             <label style="margin-right:15px;"><input type="radio" name="att-${r.student_id}" value="Absent" ${absentChecked}> Absent</label>
                             <label><input type="radio" name="att-${r.student_id}" value="Late" ${lateChecked}> Late</label>
                         </td>
                     </tr>`;
            });
            form.style.display = "block";
        })
        .catch(err => showToast(err.message, "error"));
});

document.getElementById("attendance-sheet-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const cid = parseInt(document.getElementById("att-class-select").value);
    const date = document.getElementById("att-date-input").value;
    
    const records = [];
    document.querySelectorAll("#attendance-table tbody tr").forEach(row => {
         const sid = row.getAttribute("data-id");
         const checkedRadio = row.querySelector(`input[name="att-${sid}"]:checked`);
         const stat = checkedRadio ? checkedRadio.value : "Present";
         records.push({ student_id: sid, status: stat });
    });
    
    apiFetch("/api/attendance", {
         method: "POST",
         body: { class_id: cid, date: date, records: records }
    })
    .then(() => {
         showToast("Attendance roll-call saved successfully!", "success");
    })
    .catch(err => showToast(err.message, "error"));
});

// Staff Attendance implementation
document.getElementById("btn-load-staff-attendance").addEventListener("click", () => {
    const date = document.getElementById("staff-att-date-input").value;
    if (!date) {
        showToast("Please choose a date", "error");
        return;
    }
    
    apiFetch(`/api/attendance/staff?date=${date}`)
        .then(records => {
            const form = document.getElementById("staff-attendance-sheet-form");
            const tbody = document.querySelector("#staff-attendance-table tbody");
            tbody.innerHTML = "";
            
            if(records.length === 0) {
                 tbody.innerHTML = '<tr><td colspan="4" class="text-center">No active staff members found.</td></tr>';
                 form.style.display = "block";
                 return;
            }
            
            records.forEach(r => {
                 const presentChecked = r.status === "Present" ? "checked" : "";
                 const absentChecked = r.status === "Absent" ? "checked" : "";
                 const lateChecked = r.status === "Late" ? "checked" : "";
                 tbody.innerHTML += `
                     <tr data-id="${r.staff_id}">
                         <td><strong>${r.staff_id}</strong></td>
                         <td>${r.staff_name}</td>
                         <td>${r.role_title}</td>
                         <td>
                             <label style="margin-right:15px;"><input type="radio" name="staff-att-${r.staff_id}" value="Present" ${presentChecked}> Present</label>
                             <label style="margin-right:15px;"><input type="radio" name="staff-att-${r.staff_id}" value="Absent" ${absentChecked}> Absent</label>
                             <label><input type="radio" name="staff-att-${r.staff_id}" value="Late" ${lateChecked}> Late</label>
                         </td>
                     </tr>`;
            });
            form.style.display = "block";
        })
        .catch(err => showToast(err.message, "error"));
});

document.getElementById("staff-attendance-sheet-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const date = document.getElementById("staff-att-date-input").value;
    
    const records = [];
    document.querySelectorAll("#staff-attendance-table tbody tr").forEach(row => {
         const sid = row.getAttribute("data-id");
         const checkedRadio = row.querySelector(`input[name="staff-att-${sid}"]:checked`);
         const stat = checkedRadio ? checkedRadio.value : "Present";
         records.push({ staff_id: parseInt(sid), status: stat });
    });
    
    apiFetch("/api/attendance/staff", {
         method: "POST",
         body: { date: date, records: records }
    })
    .then(() => {
         showToast("Staff attendance roll-call saved successfully!", "success");
    })
    .catch(err => showToast(err.message, "error"));
});

// Attendance Report implementation
document.getElementById("btn-load-attendance-report").addEventListener("click", () => {
    const cid = document.getElementById("rep-att-class-select").value;
    const startDate = document.getElementById("rep-att-start-date").value;
    const endDate = document.getElementById("rep-att-end-date").value;
    
    if (!cid || !startDate || !endDate) {
        showToast("Please select class, start date, and end date", "error");
        return;
    }
    
    apiFetch(`/api/attendance/report?class_id=${cid}&start_date=${startDate}&end_date=${endDate}`)
        .then(rows => {
            const container = document.getElementById("attendance-report-container");
            const tbody = document.querySelector("#attendance-report-table tbody");
            tbody.innerHTML = "";
            
            if(rows.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center">No attendance data found in this range.</td></tr>';
                container.style.display = "block";
                return;
            }
            
            rows.forEach(row => {
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${row.student_id}</strong></td>
                        <td>${row.student_name}</td>
                        <td>${row.present}</td>
                        <td>${row.absent}</td>
                        <td>${row.late}</td>
                        <td>${row.total_days}</td>
                        <td><strong>${row.percentage}%</strong></td>
                    </tr>`;
            });
            container.style.display = "block";
        })
        .catch(err => showToast(err.message, "error"));
});

document.getElementById("btn-export-attendance-pdf").addEventListener("click", () => {
    const cid = document.getElementById("rep-att-class-select").value;
    const startDate = document.getElementById("rep-att-start-date").value;
    const endDate = document.getElementById("rep-att-end-date").value;
    
    if (!cid || !startDate || !endDate) {
        showToast("Please select class, start date, and end date", "error");
        return;
    }
    
    const url = `/api/attendance/report/pdf?class_id=${cid}&start_date=${startDate}&end_date=${endDate}`;
    
    showToast("Generating Attendance PDF...", "info");
    
    fetch(url, {
        headers: {
            "Authorization": `Bearer ${currentToken}`
        }
    })
    .then(res => {
        if (!res.ok) throw new Error("Failed to export attendance report PDF");
        return res.blob();
    })
    .then(blob => {
        const fileUrl = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = fileUrl;
        a.download = `Attendance_Report_Class_${cid}_${startDate}_to_${endDate}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        showToast("PDF exported successfully", "success");
    })
    .catch(err => showToast(err.message, "error"));
});

// --- Exams Panel logic ---
function loadExams() {
    initTabs("panel-exams");
    
    // Config Exams
    apiFetch("/api/exams")
        .then(exams => {
            const tbody = document.querySelector("#exams-list-table tbody");
            const select = document.getElementById("results-exam-select");
            tbody.innerHTML = "";
            select.innerHTML = '<option value="">Select exam...</option>';
            
            if (exams.length === 0) {
                 tbody.innerHTML = '<tr><td colspan="4">No exams configured.</td></tr>';
                 return;
            }
            
            exams.forEach(e => {
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${e.id}</strong></td>
                        <td>${e.name}</td>
                        <td>${e.term_name}</td>
                        <td><span class="badge badge-branch">${e.is_active ? 'Active' : 'Completed'}</span></td>
                    </tr>`;
                select.innerHTML += `<option value="${e.id}">${e.name}</option>`;
            });
        });
        
    // Results dropdown loaders
    apiFetch("/api/academics/classes")
        .then(classes => {
             const select = document.getElementById("results-class-select");
             select.innerHTML = '<option value="">Select class...</option>';
             classes.forEach(c => select.innerHTML += `<option value="${c.id}">${c.name}</option>`);
        });
    apiFetch("/api/academics/subjects")
        .then(subjects => {
             const select = document.getElementById("results-subject-select");
             select.innerHTML = '<option value="">Select subject...</option>';
             subjects.forEach(s => select.innerHTML += `<option value="${s.id}">${s.name}</option>`);
        });
        
    // Grading scale
    apiFetch("/api/exams/grades")
        .then(grades => {
             const wrapper = document.getElementById("grades-wrapper");
             wrapper.innerHTML = "";
             grades.forEach((g, idx) => {
                 wrapper.innerHTML += `
                     <div style="display:flex; gap:10px; margin-bottom:10px; align-items:center;">
                         <strong>Grade ${g.grade}:</strong>
                         <input type="number" step="0.1" class="form-control grade-score-input" data-grade="${g.grade}" value="${g.min_score}" style="width:120px;" placeholder="Min Score">
                         <input type="text" class="form-control grade-remark-input" data-grade="${g.grade}" value="${g.remark}" placeholder="Remark">
                     </div>`;
             });
        });
}

document.getElementById("btn-add-exam-trigger").addEventListener("click", () => {
     document.getElementById("modal-add-exam").classList.add("show");
});

document.getElementById("form-add-exam").addEventListener("submit", (e) => {
     e.preventDefault();
     const name = document.getElementById("exam-title-input").value;
     apiFetch("/api/exams", { method: "POST", body: { name: name } })
         .then(() => {
              showToast("New examination setup created", "success");
              document.getElementById("modal-add-exam").classList.remove("show");
              loadExams();
         })
         .catch(err => showToast(err.message, "error"));
});

document.getElementById("btn-load-results").addEventListener("click", () => {
    const eid = document.getElementById("results-exam-select").value;
    const cid = document.getElementById("results-class-select").value;
    const sid = document.getElementById("results-subject-select").value;
    
    if(!eid || !cid || !sid) {
        showToast("Please choose exam, class, and subject", "error");
        return;
    }
    
    apiFetch(`/api/exams/results?class_id=${cid}&subject_id=${sid}&exam_id=${eid}`)
        .then(records => {
             const form = document.getElementById("results-sheet-form");
             const tbody = document.querySelector("#results-table tbody");
             tbody.innerHTML = "";
             
             if (records.length === 0) {
                  tbody.innerHTML = '<tr><td colspan="5" class="text-center">No students in this class.</td></tr>';
                  form.style.display = "block";
                  document.getElementById("btn-print-summary-pdf").removeAttribute("disabled");
                  return;
             }
             
             records.forEach(r => {
                  tbody.innerHTML += `
                      <tr data-id="${r.student_id}">
                          <td><strong>${r.student_id}</strong></td>
                          <td>${r.student_name}</td>
                          <td><input type="number" step="0.1" class="form-control res-class-score" value="${r.class_score}" style="width:100px;"></td>
                          <td><input type="number" step="0.1" class="form-control res-exam-score" value="${r.exam_score}" style="width:100px;"></td>
                          <td><input type="text" class="form-control res-remarks" value="${r.remarks || ""}"></td>
                      </tr>`;
             });
             form.style.display = "block";
             document.getElementById("btn-print-summary-pdf").removeAttribute("disabled");
        })
        .catch(err => showToast(err.message, "error"));
});

document.getElementById("btn-print-summary-pdf").addEventListener("click", () => {
     const eid = document.getElementById("results-exam-select").value;
     const cid = document.getElementById("results-class-select").value;
     if(!eid || !cid) {
          showToast("Please select exam and class first", "error");
          return;
     }
     window.open(`/api/exams/reports/summary?class_id=${cid}&exam_id=${eid}`, "_blank");
});

document.getElementById("results-sheet-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const eid = parseInt(document.getElementById("results-exam-select").value);
    const cid = parseInt(document.getElementById("results-class-select").value);
    const sid = parseInt(document.getElementById("results-subject-select").value);
    
    const scores = [];
    document.querySelectorAll("#results-table tbody tr").forEach(row => {
         const studentId = row.getAttribute("data-id");
         const classScore = parseFloat(row.querySelector(".res-class-score").value) || 0.0;
         const examScore = parseFloat(row.querySelector(".res-exam-score").value) || 0.0;
         const remarks = row.querySelector(".res-remarks").value;
         scores.push({ student_id: studentId, class_score: classScore, exam_score: examScore, remarks: remarks });
    });
    
    apiFetch("/api/exams/results", {
         method: "POST",
         body: { class_id: cid, subject_id: sid, exam_id: eid, scores: scores }
    })
    .then(() => showToast("Scoresheet saved successfully!", "success"))
    .catch(err => showToast(err.message, "error"));
});

document.getElementById("form-grades-scale").addEventListener("submit", (e) => {
     e.preventDefault();
     const list = [];
     document.querySelectorAll("#grades-wrapper div").forEach(row => {
          const inpScore = row.querySelector(".grade-score-input");
          const inpRemark = row.querySelector(".grade-remark-input");
          list.push({
              grade: inpScore.getAttribute("data-grade"),
              min_score: parseFloat(inpScore.value),
              remark: inpRemark.value
          });
     });
     
     apiFetch("/api/exams/grades", { method: "PUT", body: list })
         .then(() => showToast("Grading scale configurations saved", "success"))
         .catch(err => showToast(err.message, "error"));
});

// --- Fees Panel logic ---
function loadFees() {
    initTabs("panel-fees");
    
    // Ledger List
    apiFetch("/api/fees/structures")
        .then(bills => {
             const tbody = document.querySelector("#fees-bills-table tbody");
             tbody.innerHTML = "";
             if (bills.length === 0) {
                  tbody.innerHTML = '<tr><td colspan="6" class="text-center">No bills registered for active term.</td></tr>';
                  return;
             }
             bills.forEach(b => {
                 tbody.innerHTML += `
                     <tr>
                         <td><strong>${b.student_id}</strong></td>
                         <td>${b.student_name}</td>
                         <td>${b.term_name}</td>
                         <td>${b.total_billed.toFixed(2)} GHS</td>
                         <td>${b.total_paid.toFixed(2)} GHS</td>
                         <td><span class="badge ${b.balance > 0 ? 'badge-branch' : 'badge-academic'}">${b.balance.toFixed(2)} GHS</span></td>
                     </tr>`;
             });
        });
        
    // Payments records list
    apiFetch("/api/fees/payments")
        .then(payments => {
             const tbody = document.querySelector("#fees-payments-table tbody");
             tbody.innerHTML = "";
             if(payments.length === 0) {
                  tbody.innerHTML = '<tr><td colspan="8" class="text-center">No payments logged yet.</td></tr>';
                  return;
             }
             payments.forEach(p => {
                  tbody.innerHTML += `
                      <tr>
                          <td><strong>#${p.id}</strong></td>
                          <td>${p.student_id}</td>
                          <td>${p.student_name}</td>
                          <td>${p.amount.toFixed(2)} GHS</td>
                          <td>${p.payment_mode}</td>
                          <td>${p.ref_number || "N/A"}</td>
                          <td>${p.date}</td>
                          <td><a href="/api/fees/payments/${p.id}/receipt" target="_blank" class="btn btn-secondary btn-icon" title="Receipt"><i class="fa-solid fa-file-pdf"></i></a></td>
                      </tr>`;
             });
        });
        
    // Outstanding balances list
    apiFetch("/api/fees/balances")
        .then(balances => {
             const tbody = document.querySelector("#fees-balances-table tbody");
             tbody.innerHTML = "";
             if(balances.length === 0) {
                  tbody.innerHTML = '<tr><td colspan="6" class="text-center">No outstanding fee balances!</td></tr>';
                  return;
             }
             balances.forEach(b => {
                  tbody.innerHTML += `
                      <tr>
                          <td><strong>${b.student_id}</strong></td>
                          <td>${b.student_name}</td>
                          <td>${b.class_name}</td>
                          <td>${b.total_billed.toFixed(2)} GHS</td>
                          <td>${b.total_paid.toFixed(2)} GHS</td>
                          <td style="color:var(--accent-danger); font-weight:600;">${b.balance.toFixed(2)} GHS</td>
                      </tr>`;
             });
        });
}

// Receive Payment triggers
document.getElementById("btn-record-payment-trigger").addEventListener("click", () => {
    // Pull student list
    apiFetch("/api/students?status=Active")
        .then(students => {
             const select = document.getElementById("payment-student-select");
             select.innerHTML = '<option value="">— Select Student —</option>';
             students.forEach(s => {
                 select.innerHTML += `<option value="${s.id}">${s.last_name}, ${s.first_name} (${s.id})</option>`;
             });
             document.getElementById("modal-record-payment").classList.add("show");
        });
});

document.getElementById("form-record-payment").addEventListener("submit", (e) => {
     e.preventDefault();
     const payload = {
         student_id: document.getElementById("payment-student-select").value,
         amount: parseFloat(document.getElementById("payment-amount-input").value),
         payment_mode: document.getElementById("payment-mode-select").value,
         ref_number: document.getElementById("payment-ref-input").value
     };
     
     apiFetch("/api/fees/payments", { method: "POST", body: payload })
         .then(data => {
              showToast("Fee payment recorded successfully!", "success");
              document.getElementById("modal-record-payment").classList.remove("show");
              document.getElementById("form-record-payment").reset();
              loadFees();
              // Trigger receipt download automatically
              window.open(`/api/fees/payments/${data.payment_id}/receipt`, "_blank");
         })
         .catch(err => showToast(err.message, "error"));
});

// Bill Class Trigger
document.getElementById("btn-bill-class-trigger").addEventListener("click", () => {
     apiFetch("/api/academics/classes")
         .then(classes => {
              const select = document.getElementById("bill-class-select");
              select.innerHTML = '<option value="">Select class...</option>';
              classes.forEach(c => select.innerHTML += `<option value="${c.id}">${c.name}</option>`);
              document.getElementById("modal-bill-class").classList.add("show");
         });
});

document.getElementById("form-bill-class").addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {
         class_id: parseInt(document.getElementById("bill-class-select").value),
         bill_item: document.getElementById("bill-description-input").value,
         amount: parseFloat(document.getElementById("bill-amount-input").value)
    };
    
    apiFetch("/api/fees/structures", { method: "POST", body: payload })
        .then(data => {
             showToast(`Invoiced ${data.billed_students} students successfully!`, "success");
             document.getElementById("modal-bill-class").classList.remove("show");
             document.getElementById("form-bill-class").reset();
             loadFees();
        })
        .catch(err => showToast(err.message, "error"));
});

// --- Library Panel logic ---
function loadLibrary() {
    initTabs("panel-library");
    
    // Books catalogue
    apiFetch("/api/library/books")
        .then(books => {
             const tbody = document.querySelector("#lib-books-table tbody");
             tbody.innerHTML = "";
             if (books.length === 0) {
                  tbody.innerHTML = '<tr><td colspan="7" class="text-center">No books registered.</td></tr>';
                  return;
             }
             books.forEach(b => {
                  tbody.innerHTML += `
                      <tr>
                          <td><strong>#${b.id}</strong></td>
                          <td>${b.title}</td>
                          <td>${b.author}</td>
                          <td>${b.isbn}</td>
                          <td>${b.location}</td>
                          <td>${b.quantity}</td>
                          <td><span class="badge ${b.available > 0 ? 'badge-academic' : 'badge-branch'}">${b.available}</span></td>
                      </tr>`;
             });
        });
        
    // Issued history
    apiFetch("/api/library/logs")
        .then(logs => {
             const tbody = document.querySelector("#lib-logs-table tbody");
             tbody.innerHTML = "";
             if(logs.length === 0) {
                  tbody.innerHTML = '<tr><td colspan="8" class="text-center">No issued logs found.</td></tr>';
                  return;
             }
             logs.forEach(l => {
                  const actBtn = l.status === "Issued" ? `<button class="btn btn-success btn-xs btn-return-book" data-id="${l.id}">Return</button>` : '—';
                  tbody.innerHTML += `
                      <tr>
                          <td><strong>#${l.id}</strong></td>
                          <td>${l.book_title}</td>
                          <td>${l.student_name}</td>
                          <td>${l.issue_date}</td>
                          <td>${l.due_date}</td>
                          <td>${l.return_date || "N/A"}</td>
                          <td><span class="badge badge-branch">${l.status}</span></td>
                          <td>${actBtn}</td>
                      </tr>`;
             });
             
             document.querySelectorAll(".btn-return-book").forEach(btn => {
                 btn.addEventListener("click", () => {
                     const lid = btn.getAttribute("data-id");
                     apiFetch(`/api/library/return/${lid}`, { method: "POST" })
                         .then(() => {
                              showToast("Book returned successfully", "success");
                              loadLibrary();
                         })
                         .catch(err => showToast(err.message, "error"));
                 });
             });
        });
}

document.getElementById("btn-add-book-trigger").addEventListener("click", () => {
     document.getElementById("modal-add-book").classList.add("show");
});

document.getElementById("form-add-book").addEventListener("submit", (e) => {
     e.preventDefault();
     const payload = {
         title: document.getElementById("book-title").value,
         author: document.getElementById("book-author").value,
         isbn: document.getElementById("book-isbn").value,
         location: document.getElementById("book-location").value,
         quantity: parseInt(document.getElementById("book-qty").value)
     };
     
     apiFetch("/api/library/books", { method: "POST", body: payload })
         .then(() => {
              showToast("Book catalogue updated", "success");
              document.getElementById("modal-add-book").classList.remove("show");
              document.getElementById("form-add-book").reset();
              loadLibrary();
         })
         .catch(err => showToast(err.message, "error"));
});

document.getElementById("btn-issue-book-trigger").addEventListener("click", () => {
     // Pull books & active students
     Promise.all([
         apiFetch("/api/library/books"),
         apiFetch("/api/students?status=Active")
     ]).then(([books, students]) => {
          const bSelect = document.getElementById("issue-book-select");
          const sSelect = document.getElementById("issue-student-select");
          
          bSelect.innerHTML = '<option value="">— Select Book —</option>';
          sSelect.innerHTML = '<option value="">— Select Student —</option>';
          
          books.filter(b => b.available > 0).forEach(b => bSelect.innerHTML += `<option value="${b.id}">${b.title} (${b.available} left)</option>`);
          students.forEach(s => sSelect.innerHTML += `<option value="${s.id}">${s.last_name}, ${s.first_name} (${s.id})</option>`);
          
          document.getElementById("modal-issue-book").classList.add("show");
     });
});

document.getElementById("form-issue-book").addEventListener("submit", (e) => {
     e.preventDefault();
     const payload = {
          book_id: parseInt(document.getElementById("issue-book-select").value),
          student_id: document.getElementById("issue-student-select").value
     };
     apiFetch("/api/library/borrow", { method: "POST", body: payload })
         .then(() => {
              showToast("Book issued successfully!", "success");
              document.getElementById("modal-issue-book").classList.remove("show");
              loadLibrary();
         })
         .catch(err => showToast(err.message, "error"));
});

// --- Inventory Panel logic ---
function loadInventory() {
    apiFetch("/api/inventory")
        .then(items => {
             const tbody = document.querySelector("#inventory-table tbody");
             tbody.innerHTML = "";
             if(items.length === 0) {
                 tbody.innerHTML = '<tr><td colspan="6" class="text-center">No inventory assets logged.</td></tr>';
                 return;
             }
             items.forEach(i => {
                  tbody.innerHTML += `
                      <tr>
                          <td><strong>#${i.id}</strong></td>
                          <td>${i.item_name}</td>
                          <td>${i.category}</td>
                          <td>${i.quantity}</td>
                          <td>${i.condition}</td>
                          <td>${i.value.toFixed(2)} GHS</td>
                      </tr>`;
             });
        });
}

const btnAddInventoryTrigger = document.getElementById("btn-add-inventory-trigger");
if (btnAddInventoryTrigger) {
    btnAddInventoryTrigger.addEventListener("click", () => {
         const modal = document.getElementById("modal-add-inventory");
         if (modal) modal.classList.add("show");
    });
}

const formAddInventory = document.getElementById("form-add-inventory");
if (formAddInventory) {
    formAddInventory.addEventListener("submit", (e) => {
         e.preventDefault();
         const payload = {
             item_name: document.getElementById("inv-item-name").value,
             category: document.getElementById("inv-category").value,
             quantity: parseInt(document.getElementById("inv-qty").value),
             condition: document.getElementById("inv-condition").value,
             value: parseFloat(document.getElementById("inv-value").value)
         };
         
         apiFetch("/api/inventory", { method: "POST", body: payload })
             .then(() => {
                  showToast("Inventory record added", "success");
                  const modal = document.getElementById("modal-add-inventory");
                  if (modal) modal.classList.remove("show");
                  formAddInventory.reset();
                  loadInventory();
             })
             .catch(err => showToast(err.message, "error"));
    });
}

// --- Communication Panel logic ---
function loadCommunication() {
    initTabs("panel-communication");
    
    // Announcements list
    apiFetch("/api/communication/announcements")
        .then(list => {
             const div = document.getElementById("list-announcements");
             div.innerHTML = "";
             if (list.length === 0) {
                 div.innerHTML = "<p>No active announcements posted.</p>";
                 return;
             }
             list.forEach(a => {
                 div.innerHTML += `
                     <div class="announcement-item mt-15" style="border-bottom:1px solid var(--border-glass); padding-bottom:10px;">
                         <h4><strong>${a.title}</strong> <span class="badge badge-branch" style="display:inline-block; font-size:9px; padding:2px 8px;">Target: ${a.audience}</span></h4>
                         <p style="font-size:12px; margin-top:5px; color:var(--text-secondary);">${a.content}</p>
                         <small style="color:var(--text-muted);">${a.date}</small>
                     </div>`;
             });
        });
        
    // SMS history logs
    apiFetch("/api/communication/sms-logs")
        .then(logs => {
             const tbody = document.querySelector("#sms-logs-table tbody");
             tbody.innerHTML = "";
             if(logs.length === 0) {
                 tbody.innerHTML = '<tr><td colspan="4">No SMS logs recorded.</td></tr>';
                 return;
             }
             logs.forEach(l => {
                 tbody.innerHTML += `
                     <tr>
                         <td>${l.date}</td>
                         <td><strong>${l.phone}</strong></td>
                         <td>${l.content}</td>
                         <td><span class="badge badge-academic">${l.status}</span></td>
                     </tr>`;
             });
        });
        
    // Character count listener on SMS input
    document.getElementById("sms-message-input").addEventListener("input", (e) => {
         const count = e.target.value.length;
         document.getElementById("sms-chars-hint").innerText = `${count} / 160 characters`;
    });

    // Populate bulk broadcast class selection
    apiFetch("/api/academics/classes")
        .then(classes => {
            const select = document.getElementById("sms-broadcast-class");
            if (select) {
                select.innerHTML = '<option value="">All Classes (School-wide)</option>';
                classes.forEach(c => {
                    select.innerHTML += `<option value="${c.id}">${c.name} (${c.stream || "No Stream"})</option>`;
                });
            }
        });
}

document.getElementById("form-add-announcement").addEventListener("submit", (e) => {
     e.preventDefault();
     const payload = {
         title: document.getElementById("ann-title-input").value,
         audience: document.getElementById("ann-audience-select").value,
         content: document.getElementById("ann-content-input").value
     };
     
     apiFetch("/api/communication/announcements", { method: "POST", body: payload })
         .then(() => {
              showToast("Announcement broadcasted successfully", "success");
              document.getElementById("form-add-announcement").reset();
              loadCommunication();
         })
         .catch(err => showToast(err.message, "error"));
});

document.getElementById("form-send-sms").addEventListener("submit", (e) => {
     e.preventDefault();
     const payload = {
         phone: document.getElementById("sms-phone-input").value,
         message: document.getElementById("sms-message-input").value
     };
     
     apiFetch("/api/communication/sms", { method: "POST", body: payload })
         .then(data => {
              showToast("SMS dispatched successfully (Simulated)", "success");
              document.getElementById("form-send-sms").reset();
              loadCommunication();
         })
         .catch(err => showToast(err.message, "error"));
});

// Bulk SMS Broadcaster listeners
document.getElementById("btn-broadcast-fees").addEventListener("click", () => {
    const classId = document.getElementById("sms-broadcast-class").value;
    const payload = {
        broadcast_type: "fee_reminder",
        class_id: classId ? parseInt(classId) : null
    };
    
    if (confirm("Are you sure you want to broadcast simulated outstanding fee reminders to parents?")) {
        apiFetch("/api/communication/sms/broadcast", { method: "POST", body: payload })
            .then(res => {
                showToast(res.message, "success");
                loadCommunication();
            })
            .catch(err => showToast(err.message, "error"));
    }
});

document.getElementById("btn-broadcast-reports").addEventListener("click", () => {
    const classId = document.getElementById("sms-broadcast-class").value;
    const payload = {
        broadcast_type: "report_summary",
        class_id: classId ? parseInt(classId) : null
    };
    
    if (confirm("Are you sure you want to broadcast simulated report card summaries to parents?")) {
        apiFetch("/api/communication/sms/broadcast", { method: "POST", body: payload })
            .then(res => {
                showToast(res.message, "success");
                loadCommunication();
            })
            .catch(err => showToast(err.message, "error"));
    }
});

// --- Settings Panel logic ---
function loadSettings() {
    initTabs("panel-settings");
    
    // Profiles details
    apiFetch("/api/settings/school-profile")
        .then(profile => {
             document.getElementById("set-school-name").value = profile.school_name;
             document.getElementById("set-school-motto").value = profile.school_motto;
             document.getElementById("set-school-phone").value = profile.school_phone;
             document.getElementById("set-school-email").value = profile.school_email;
             document.getElementById("set-school-address").value = profile.school_address;
        });
        
    // Backups table list
    loadBackupsTable();
}

function loadBackupsTable() {
    apiFetch("/api/settings/backups")
        .then(backups => {
             const tbody = document.querySelector("#backups-table tbody");
             tbody.innerHTML = "";
             if (backups.length === 0) {
                 tbody.innerHTML = '<tr><td colspan="3">No backup files found.</td></tr>';
                 return;
             }
             backups.forEach(b => {
                 const mbSize = (b.size / (1024 * 1024)).toFixed(2);
                 tbody.innerHTML += `
                     <tr>
                         <td><strong>${b.filename}</strong></td>
                         <td>${mbSize} MB</td>
                         <td>${b.created}</td>
                     </tr>`;
             });
        });
}

document.getElementById("form-settings-profile").addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {
         school_name: document.getElementById("set-school-name").value,
         school_motto: document.getElementById("set-school-motto").value,
         school_phone: document.getElementById("set-school-phone").value,
         school_email: document.getElementById("set-school-email").value,
         school_address: document.getElementById("set-school-address").value
    };
    
    apiFetch("/api/settings/school-profile", { method: "PUT", body: payload })
        .then(() => showToast("School configurations profile saved successfully!", "success"))
        .catch(err => showToast(err.message, "error"));
});

document.getElementById("btn-trigger-backup-now").addEventListener("click", () => {
     apiFetch("/api/settings/backups", { method: "POST" })
         .then(() => {
              showToast("Manual database zip backup completed", "success");
              loadBackupsTable();
         })
         .catch(err => showToast(err.message, "error"));
});

// --- System Admin Panel (Global Scope) ---
function loadSysadmin() {
    initTabs("panel-sysadmin");
    
    // Branches list
    apiFetch("/api/sysadmin/branches")
        .then(branches => {
             const tbody = document.querySelector("#sys-branches-table tbody");
             tbody.innerHTML = "";
             if(branches.length === 0) {
                  tbody.innerHTML = '<tr><td colspan="7">No branches registered.</td></tr>';
                  return;
             }
             branches.forEach(b => {
                  const activeBadge = b.is_active ? '<span class="badge badge-branch">Active</span>' : '<span class="badge badge-branch" style="background:rgba(239, 68, 68, 0.1); color:#f87171; border-color:rgba(239, 68, 68, 0.2);">Suspended</span>';
                  const activeToggleText = b.is_active ? "Suspend" : "Activate";
                  tbody.innerHTML += `
                      <tr>
                          <td><strong>${b.id}</strong></td>
                          <td>${b.name}</td>
                          <td><strong>${b.code}</strong></td>
                          <td>${activeBadge}</td>
                          <td>${b.students}</td>
                          <td>${b.staff}</td>
                          <td>
                              <button class="btn btn-secondary btn-xs btn-toggle-branch-status" data-id="${b.id}" data-active="${b.is_active}">${activeToggleText}</button>
                          </td>
                      </tr>`;
             });
             
             document.querySelectorAll(".btn-toggle-branch-status").forEach(btn => {
                 btn.addEventListener("click", () => {
                     const bid = btn.getAttribute("data-id");
                     const active = btn.getAttribute("data-active") === "true";
                     
                     // Find the branch details
                     const branch = branches.find(x => x.id == bid);
                     const payload = {
                          name: branch.name,
                          address: branch.address,
                          phone: branch.phone,
                          email: branch.email,
                          is_active: !active,
                          notes: branch.notes
                     };
                     
                     apiFetch(`/api/sysadmin/branches/${bid}`, { method: "PUT", body: payload })
                         .then(() => {
                              showToast("Branch active status toggled", "success");
                              loadSysadmin();
                         })
                         .catch(err => showToast(err.message, "error"));
                 });
             });
        });
        
    // System Admins
    apiFetch("/api/sysadmin/admins")
        .then(admins => {
             const tbody = document.querySelector("#sys-admins-table tbody");
             tbody.innerHTML = "";
             if(admins.length === 0) {
                  tbody.innerHTML = '<tr><td colspan="6">No system administrator accounts found.</td></tr>';
                  return;
             }
             admins.forEach(a => {
                  tbody.innerHTML += `
                      <tr>
                          <td><strong>#${a.id}</strong></td>
                          <td>${a.username}</td>
                          <td>${a.full_name}</td>
                          <td>${a.email}</td>
                          <td><span class="badge badge-branch">${a.is_active ? 'Active' : 'Disabled'}</span></td>
                          <td>${a.created_at}</td>
                      </tr>`;
             });
        });
}

document.getElementById("btn-add-branch-trigger").addEventListener("click", () => {
     document.getElementById("modal-add-branch").classList.add("show");
});

document.getElementById("form-add-branch").addEventListener("submit", (e) => {
     e.preventDefault();
     const payload = {
          name: document.getElementById("branch-name").value,
          code: document.getElementById("branch-code").value,
          phone: document.getElementById("branch-phone").value,
          email: document.getElementById("branch-email").value,
          address: document.getElementById("branch-address").value,
          notes: document.getElementById("branch-notes").value,
          head_username: document.getElementById("branch-head-username").value,
          head_password: document.getElementById("branch-head-password").value,
          head_full_name: document.getElementById("branch-head-fullname").value,
          head_email: document.getElementById("branch-head-email").value
     };
     
     apiFetch("/api/sysadmin/branches", { method: "POST", body: payload })
         .then(() => {
              showToast("New school branch registered and seeded successfully!", "success");
              document.getElementById("modal-add-branch").classList.remove("show");
              document.getElementById("form-add-branch").reset();
              loadSysadmin();
         })
         .catch(err => showToast(err.message, "error"));
});

document.getElementById("btn-add-sysadmin-trigger").addEventListener("click", () => {
     document.getElementById("modal-add-sysadmin").classList.add("show");
});

document.getElementById("form-add-sysadmin").addEventListener("submit", (e) => {
     e.preventDefault();
     const payload = {
          username: document.getElementById("sys-username").value,
          full_name: document.getElementById("sys-fullname").value,
          email: document.getElementById("sys-email").value,
          password: document.getElementById("sys-password").value
     };
     
     apiFetch("/api/sysadmin/admins", { method: "POST", body: payload })
         .then(() => {
              showToast("New System Administrator created", "success");
              document.getElementById("modal-add-sysadmin").classList.remove("show");
              document.getElementById("form-add-sysadmin").reset();
              loadSysadmin();
         })
         .catch(err => showToast(err.message, "error"));
});

// --- 7. Utility helper widgets ---
function initTabs(panelId) {
    const header = document.querySelector(`#${panelId} .tab-header`);
    if (!header || header.hasAttribute("data-init")) return;
    
    header.setAttribute("data-init", "true");
    header.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            header.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            
            const tabId = btn.getAttribute("data-tab");
            const panel = document.getElementById(panelId);
            panel.querySelectorAll(".tab-content").forEach(content => {
                content.classList.remove("active");
            });
            document.getElementById(tabId).classList.add("active");
        });
    });
}

function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let icon = "fa-circle-info";
    if (type === "success") icon = "fa-circle-check";
    else if (type === "error") icon = "fa-circle-xmark";
    
    toast.innerHTML = `
        <i class="fa-solid ${icon}"></i>
        <span>${message}</span>`;
        
    container.appendChild(toast);
    
    // Automatically remove after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

// --- Bulk Admission & Staff Registration Features ---
function initBulkUploadFeatures() {
    // Exporter buttons
    document.getElementById("btn-download-student-template").addEventListener("click", () => {
        const headers = [
            'first_name', 'last_name', 'other_names', 'gender', 'date_of_birth',
            'class_name', 'parent_name', 'parent_phone', 'parent_email',
            'emergency_contact_name', 'emergency_contact_phone'
        ];
        const rows = [
            [
                'John', 'Doe', 'Kofi', 'Male', '2015-06-15',
                'Class 1A', 'Robert Doe', '+233240000000', 'robert.doe@example.com',
                'Mary Doe', '+233241111111'
            ]
        ];
        downloadCSV("student_upload_template.csv", headers, rows);
    });

    document.getElementById("btn-download-staff-template").addEventListener("click", () => {
        const headers = [
            'first_name', 'last_name', 'other_names', 'phone', 'email',
            'role_title', 'department', 'qualification', 'address', 'base_salary'
        ];
        const rows = [
            [
                'Jane', 'Smith', 'Naa', '+233242222222', 'jane.smith@example.com',
                'Teacher', 'Science', 'B.Ed Science', 'Cantonments Accra', '3500.0'
            ]
        ];
        downloadCSV("staff_upload_template.csv", headers, rows);
    });

    // Modal triggers
    document.getElementById("btn-bulk-admit-trigger").addEventListener("click", () => {
        document.getElementById("student-file-input").value = "";
        document.getElementById("student-upload-preview").style.display = "none";
        document.getElementById("student-validation-log").style.display = "none";
        document.getElementById("student-validation-log").querySelector("ul").innerHTML = "";
        document.getElementById("btn-execute-student-upload").disabled = true;
        document.getElementById("modal-bulk-admit-student").classList.add("show");
    });

    document.getElementById("btn-bulk-staff-trigger").addEventListener("click", () => {
        document.getElementById("staff-file-input").value = "";
        document.getElementById("staff-upload-preview").style.display = "none";
        document.getElementById("staff-validation-log").style.display = "none";
        document.getElementById("staff-validation-log").querySelector("ul").innerHTML = "";
        document.getElementById("btn-execute-staff-upload").disabled = true;
        document.getElementById("modal-bulk-register-staff").classList.add("show");
    });

    // Upload zone handlers
    setupUploadZone(
        "student-upload-zone",
        "student-file-input",
        "student-upload-preview",
        "student-file-name",
        "student-file-rows",
        "btn-execute-student-upload",
        "student-validation-log"
    );

    setupUploadZone(
        "staff-upload-zone",
        "staff-file-input",
        "staff-upload-preview",
        "staff-file-name",
        "staff-file-rows",
        "btn-execute-staff-upload",
        "staff-validation-log"
    );

    // Import click handlers
    document.getElementById("btn-execute-student-upload").addEventListener("click", executeStudentImport);
    document.getElementById("btn-execute-staff-upload").addEventListener("click", executeStaffImport);
}

function downloadCSV(filename, headers, rows) {
    const csvLines = [headers.join(",")];
    rows.forEach(row => {
        csvLines.push(row.map(v => {
            v = (v === null || v === undefined) ? "" : String(v);
            if (v.includes(",") || v.includes('"') || v.includes("\n") || v.includes("\r")) {
                return '"' + v.replace(/"/g, '""') + '"';
            }
            return v;
        }).join(","));
    });
    const csvContent = csvLines.join("\n");
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function parseCSVText(text) {
    const lines = [];
    let row = [""];
    let inQuotes = false;
    for (let i = 0; i < text.length; i++) {
        const c = text[i];
        const next = text[i+1];
        if (c === '"') {
            if (inQuotes && next === '"') {
                row[row.length - 1] += '"';
                i++;
            } else {
                inQuotes = !inQuotes;
            }
        } else if (c === ',' && !inQuotes) {
            row.push("");
        } else if ((c === '\r' || c === '\n') && !inQuotes) {
            if (c === '\r' && next === '\n') {
                i++;
            }
            lines.push(row);
            row = [""];
        } else {
            row[row.length - 1] += c;
        }
    }
    if (row.length > 1 || row[0] !== "") {
        lines.push(row);
    }
    return lines;
}

function setupUploadZone(zoneId, inputId, previewId, nameId, rowsId, btnId, logId) {
    const zone = document.getElementById(zoneId);
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    const nameSpan = document.getElementById(nameId);
    const rowsSpan = document.getElementById(rowsId);
    const executeBtn = document.getElementById(btnId);
    const log = document.getElementById(logId);
    
    zone.addEventListener("dragover", (e) => {
        e.preventDefault();
        zone.classList.add("dragover");
    });
    zone.addEventListener("dragleave", () => {
        zone.classList.remove("dragover");
    });
    zone.addEventListener("drop", (e) => {
        e.preventDefault();
        zone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            input.files = e.dataTransfer.files;
            handleFile(input.files[0]);
        }
    });
    zone.addEventListener("click", () => {
        input.click();
    });
    input.addEventListener("change", () => {
        if (input.files.length > 0) {
            handleFile(input.files[0]);
        }
    });
    
    function handleFile(file) {
        nameSpan.innerText = `Selected: ${file.name}`;
        preview.style.display = "block";
        log.style.display = "none";
        log.querySelector("ul").innerHTML = "";
        executeBtn.disabled = true;
        
        const reader = new FileReader();
        reader.onload = function(e) {
            const data = e.target.result;
            try {
                let rows = [];
                if (file.name.endsWith(".csv")) {
                    const text = data;
                    rows = parseCSVText(text);
                } else {
                    const workbook = XLSX.read(new Uint8Array(data), { type: 'array' });
                    const sheetName = workbook.SheetNames[0];
                    const sheet = workbook.Sheets[sheetName];
                    rows = XLSX.utils.sheet_to_json(sheet, { header: 1 });
                }
                
                rows = rows.filter(r => r.length > 0 && r.some(cell => cell !== null && cell !== undefined && String(cell).trim() !== ""));
                
                if (rows.length <= 1) {
                    showToast("The file contains no records", "error");
                    preview.style.display = "none";
                    return;
                }
                
                rowsSpan.innerText = rows.length - 1;
                executeBtn.disabled = false;
                
                zone.parsedData = rows;
            } catch (err) {
                showToast(`Failed to parse file: ${err.message}`, "error");
                preview.style.display = "none";
            }
        };
        
        if (file.name.endsWith(".csv")) {
            reader.readAsText(file);
        } else {
            reader.readAsArrayBuffer(file);
        }
    }
}

function mapRowsToObject(rows) {
    const headers = rows[0].map(h => String(h).trim().toLowerCase());
    const dataRows = rows.slice(1);
    return dataRows.map(row => {
        const obj = {};
        headers.forEach((h, index) => {
            if (row[index] !== undefined && row[index] !== null) {
                obj[h] = String(row[index]).trim();
            } else {
                obj[h] = "";
            }
        });
        return obj;
    });
}

function displayValidationErrors(logId, errorMessage) {
    const logBox = document.getElementById(logId);
    const ul = logBox.querySelector("ul");
    ul.innerHTML = "";
    
    const lines = errorMessage.split("\n");
    lines.forEach(line => {
        if (line.trim()) {
            const li = document.createElement("li");
            li.innerText = line;
            ul.appendChild(li);
        }
    });
    logBox.style.display = "block";
}

function executeStudentImport() {
    const zone = document.getElementById("student-upload-zone");
    if (!zone.parsedData) return;
    
    const objects = mapRowsToObject(zone.parsedData);
    const payload = objects.map(obj => {
        const parentName = obj.parent_name || "";
        const parentParts = parentName.split(/\s+/);
        const parentFname = parentParts[0] || "Parent";
        const parentLname = parentParts.slice(1).join(" ") || "Name";
        
        return {
            first_name: obj.first_name || "",
            last_name: obj.last_name || "",
            other_names: obj.other_names || "",
            gender: obj.gender || "",
            dob: obj.date_of_birth || "",
            class_name: obj.class_name || "",
            parent: {
                first_name: parentFname,
                last_name: parentLname,
                phone: obj.parent_phone || "N/A",
                email: obj.parent_email || "",
                occupation: "",
                address: ""
            },
            emergency_contact_name: obj.emergency_contact_name || "",
            emergency_contact_phone: obj.emergency_contact_phone || ""
        };
    });
    
    const executeBtn = document.getElementById("btn-execute-student-upload");
    executeBtn.disabled = true;
    executeBtn.innerText = "Importing...";
    
    apiFetch("/api/students/bulk", {
        method: "POST",
        body: payload
    })
    .then(data => {
        showToast(`Successfully admitted ${data.count} students!`, "success");
        document.getElementById("modal-bulk-admit-student").classList.remove("show");
        loadStudentsList();
    })
    .catch(err => {
        showToast("Validation failed. Check logs.", "error");
        displayValidationErrors("student-validation-log", err.message);
    })
    .finally(() => {
        executeBtn.disabled = false;
        executeBtn.innerText = "Import Students";
    });
}

async function getExistingStaffUsernames() {
    try {
        const staff = await apiFetch("/api/staff");
        return new Set(staff.map(s => String(s.username).trim().toLowerCase()));
    } catch (err) {
        console.error("Failed to fetch staff list for unique username checks:", err);
        return new Set();
    }
}

async function executeStaffImport() {
    const zone = document.getElementById("staff-upload-zone");
    if (!zone.parsedData) return;
    
    const executeBtn = document.getElementById("btn-execute-staff-upload");
    executeBtn.disabled = true;
    executeBtn.innerText = "Importing...";
    
    const takenUsernames = await getExistingStaffUsernames();
    
    const objects = mapRowsToObject(zone.parsedData);
    const roleMapping = {
        "teacher": "Teacher",
        "accountant": "Accountant",
        "librarian": "Librarian",
        "storekeeper": "Storekeeper",
        "headteacher": "Admin/Headteacher",
        "admin officer": "Admin/Headteacher"
    };
    
    const payload = objects.map(obj => {
        const fname = (obj.first_name || "").replace(/\s+/g, "").toLowerCase();
        const lname = (obj.last_name || "").replace(/\s+/g, "").toLowerCase();
        
        let baseUsername = `${fname}.${lname}`;
        if (!baseUsername || baseUsername === ".") {
            baseUsername = "staff.user";
        }
        let username = baseUsername;
        let suffix = 1;
        while (takenUsernames.has(username)) {
            username = `${baseUsername}${suffix}`;
            suffix++;
        }
        takenUsernames.add(username);
        
        const inputRole = (obj.role_title || "teacher").trim().toLowerCase();
        const mappedRole = roleMapping[inputRole] || "Teacher";
        
        let salary = 0.0;
        if (obj.base_salary) {
            const parsedVal = parseFloat(obj.base_salary);
            if (!isNaN(parsedVal)) {
                salary = parsedVal;
            }
        }
        
        return {
            first_name: obj.first_name || "",
            last_name: obj.last_name || "",
            username: username,
            role_name: mappedRole,
            phone: obj.phone || "",
            email: obj.email || "",
            qualification: obj.qualification || "",
            base_salary: salary
        };
    });
    
    apiFetch("/api/staff/bulk", {
        method: "POST",
        body: payload
    })
    .then(data => {
        showToast(`Successfully registered ${data.count} staff members!`, "success");
        document.getElementById("modal-bulk-register-staff").classList.remove("show");
        loadStaff();
    })
    .catch(err => {
        showToast("Validation failed. Check logs.", "error");
        displayValidationErrors("staff-validation-log", err.message);
    })
    .finally(() => {
        executeBtn.disabled = false;
        executeBtn.innerText = "Import Staff";
    });
}
