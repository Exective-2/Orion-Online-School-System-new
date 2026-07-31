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
    // Restore sidebar state
    const isCollapsed = localStorage.getItem("sidebarCollapsed") === "true";
    const layout = document.querySelector(".app-layout");
    if (isCollapsed && layout) {
        layout.classList.add("sidebar-collapsed");
    }
    
    initTheme();
    initAppRouting();
    initGlobalEventListeners();
    checkSetupAndVerifyAuth();
});

const ALL_THEMES = ["dark", "light", "emerald", "sapphire", "amber", "amethyst", "blossom", "lavender"];

function getThemeStorageKey() {
    if (currentUser && (currentUser.username || currentUser.user_id || currentUser.full_name)) {
        const identifier = currentUser.username || currentUser.user_id || currentUser.full_name;
        const branchKey = currentUser.branch_id ? `_b${currentUser.branch_id}` : "_master";
        return `orion_theme_user_${identifier.toString().replace(/[^a-zA-Z0-9_]/g, '_')}${branchKey}`;
    }
    return "orion_theme_guest";
}

function getUserSavedTheme() {
    const key = getThemeStorageKey();
    const saved = localStorage.getItem(key);
    if (saved && ALL_THEMES.includes(saved)) {
        return saved;
    }
    const fallback = localStorage.getItem("orion_theme");
    if (fallback && ALL_THEMES.includes(fallback)) {
        return fallback;
    }
    return "dark";
}

function setTheme(themeKey) {
    if (!ALL_THEMES.includes(themeKey)) themeKey = "dark";
    activeTheme = themeKey;

    const userKey = getThemeStorageKey();
    localStorage.setItem(userKey, themeKey);
    localStorage.setItem("orion_theme", themeKey);

    ALL_THEMES.forEach(t => {
        document.body.classList.remove(`${t}-theme`, `theme-${t}`);
    });

    if (themeKey === "light") {
        document.body.classList.add("light-theme");
    } else if (themeKey === "dark") {
        document.body.classList.add("dark-theme");
    } else {
        document.body.classList.add(`theme-${themeKey}`);
    }

    document.querySelectorAll(".theme-option-card").forEach(card => {
        if (card.getAttribute("data-theme") === themeKey) {
            card.classList.add("active");
        } else {
            card.classList.remove("active");
        }
    });

    const iconEl = document.getElementById("btn-theme-toggle");
    if (iconEl) {
        const iconMap = {
            dark: '<i class="fa-solid fa-moon"></i>',
            light: '<i class="fa-solid fa-sun"></i>',
            emerald: '<i class="fa-solid fa-tree"></i>',
            sapphire: '<i class="fa-solid fa-water"></i>',
            amber: '<i class="fa-solid fa-fire"></i>',
            amethyst: '<i class="fa-solid fa-gem"></i>',
            blossom: '<i class="fa-solid fa-seedling"></i>',
            lavender: '<i class="fa-solid fa-wand-magic-sparkles"></i>'
        };
        iconEl.innerHTML = iconMap[themeKey] || '<i class="fa-solid fa-palette"></i>';
    }
}

function initTheme() {
    setTheme(getUserSavedTheme());
}

function checkSetupAndVerifyAuth() {
    fetch("/api/setup/status")
        .then(res => res.json())
        .then(data => {
            if (!data.setup_completed) {
                const setupLink = document.getElementById("link-setup-wizard");
                if (setupLink) setupLink.style.display = "inline-flex";
                showView("view-setup");
                initSetupWizard();
            } else {
                const setupLink = document.getElementById("link-setup-wizard");
                if (setupLink) setupLink.style.display = "none";

                if (currentToken) {
                    parseTokenAndRoute();
                } else {
                    showView("view-login");
                    initLoginPage();
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

function updateHeaderAcademicBadge() {
    if (!currentUser || currentUser.role === "System Admin") {
        const badge = document.getElementById("header-academic-badge");
        if (badge) badge.style.display = "none";
        return;
    }
    
    apiFetch("/api/academics/current")
        .then(info => {
            const badge = document.getElementById("header-academic-badge");
            if (badge) {
                badge.style.display = "inline-flex";
                badge.innerHTML = `<i class="fa-solid fa-calendar"></i> ${info.academic_year} - ${info.term}`;
            }
        })
        .catch(err => console.error("Error updating academic badge:", err));
}
window.updateHeaderAcademicBadge = updateHeaderAcademicBadge;

function decodeJwtPayload(token) {
    try {
        const base64Url = token.split('.')[1];
        if (!base64Url) return null;
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        return JSON.parse(jsonPayload);
    } catch (e) {
        try {
            return JSON.parse(atob(token.split('.')[1]));
        } catch (err) {
            console.error("JWT parse error:", err);
            return null;
        }
    }
}

function parseTokenAndRoute() {
    if (!currentToken) {
        showView("view-login");
        return;
    }

    let payload;
    try {
        payload = decodeJwtPayload(currentToken);
        if (!payload) {
            handleLogout();
            return;
        }
        const now = Math.floor(Date.now() / 1000);
        if (payload.exp && payload.exp < now) {
            console.warn("Token expired");
            handleLogout();
            return;
        }
    } catch (e) {
        console.error("JWT token decoding failed:", e);
        handleLogout();
        return;
    }

    try {
        currentUser = payload;
        currentBranchId = payload.branch_id;
        currentBranchName = payload.branch_name;
        
        // Restore user's personal theme preference
        initTheme();

        // Show main application view first
        showView("view-main-layout");

        // Safely update header badges
        const nameEl = document.getElementById("user-display-name");
        if (nameEl) nameEl.innerText = payload.full_name || payload.student_name || payload.username || (payload.role === "Parent" ? "Parent User" : "User");
        
        const roleEl = document.getElementById("user-display-role");
        if (roleEl) roleEl.innerText = payload.role;

        const branchBadge = document.getElementById("header-branch-badge");
        const academicBadge = document.getElementById("header-academic-badge");
        const sysLink = document.getElementById("sidebar-sysadmin-link");
        const parentLink = document.getElementById("sidebar-parent-link");
        const headSel = document.getElementById("header-branch-switcher");

        const appLayout = document.querySelector(".app-layout");
        const searchEl = document.querySelector(".header-search");
        const sideToggle = document.getElementById("btn-sidebar-toggle");

        if (payload.role === "System Admin") {
            if (appLayout) appLayout.classList.remove("is-parent-user");
            if (searchEl) searchEl.style.display = "flex";
            if (sideToggle) sideToggle.style.display = "inline-flex";
            if (branchBadge) branchBadge.style.display = "none";
            if (academicBadge) academicBadge.style.display = "none";
            if (sysLink) sysLink.style.display = "block";
            if (parentLink) parentLink.style.display = "none";
            if (headSel) headSel.style.display = "inline-block";

            applyUserRolePermissions(payload);
            switchPanel("panel-sysadmin");
        } else if (payload.role === "Parent" || payload.role === "Student") {
            activeBranchIdOverride = null;
            if (appLayout) appLayout.classList.add("is-parent-user");
            if (searchEl) searchEl.style.display = "none";
            if (sideToggle) sideToggle.style.display = "inline-flex";
            if (headSel) headSel.style.display = "none";
            if (branchBadge) {
                branchBadge.style.display = "inline-flex";
                branchBadge.innerHTML = `<i class="fa-solid fa-code-branch"></i> ${payload.branch_name || currentBranchName || "Main Campus"}`;
            }
            if (academicBadge) {
                academicBadge.style.display = "inline-flex";
                academicBadge.innerHTML = `<i class="fa-solid fa-graduation-cap"></i> Parent & Student Portal`;
            }
            if (sysLink) sysLink.style.display = "none";
            if (parentLink) parentLink.style.display = "none";

            applyUserRolePermissions(payload);
            switchPanel("panel-parent-portal");
            loadParentPortalData(payload.student_id);
        } else {
            if (appLayout) appLayout.classList.remove("is-parent-user");
            if (searchEl) searchEl.style.display = "flex";
            if (sideToggle) sideToggle.style.display = "inline-flex";
            activeBranchIdOverride = null;
            if (headSel) headSel.style.display = "none";
            if (branchBadge) {
                branchBadge.style.display = "inline-flex";
                branchBadge.innerHTML = `<i class="fa-solid fa-code-branch"></i> ${currentBranchName || "Branch"}`;
            }
            if (academicBadge) academicBadge.style.display = "inline-flex";
            if (sysLink) sysLink.style.display = "none";
            if (parentLink) parentLink.style.display = "none";

            applyUserRolePermissions(payload);
            applyRoleBasedNavigation(payload);
            switchPanel("panel-dashboard");
            updateHeaderAcademicBadge();
        }
    } catch (err) {
        console.error("Error setting up UI layout for user:", err);
    }
}

function isModuleDisabled(targetOrKey, disabledList) {
    if (!disabledList || disabledList.length === 0) return false;
    const rawKey = (targetOrKey || "").replace("panel-", "").toLowerCase().trim();
    
    // Alias mapping between sidebar panel target ID and toggle value keys
    const aliasMap = {
        "academics": ["academics"],
        "students": ["students"],
        "staff": ["teachers", "staff"],
        "teachers": ["teachers", "staff"],
        "parents": ["parents"],
        "attendance": ["attendance"],
        "exams": ["examination", "exams"],
        "examination": ["examination", "exams"],
        "result-approvals": ["approvals", "result-approvals"],
        "approvals": ["approvals", "result-approvals"],
        "report-cards": ["reports", "report-cards"],
        "reports": ["reports", "report-cards"],
        "fees": ["fees"],
        "payroll": ["payroll"],
        "library": ["library"],
        "inventory": ["inventory"],
        "timetable": ["timetable"],
        "communication": ["communication"],
        "settings": ["settings"]
    };

    const keysToCheck = aliasMap[rawKey] || [rawKey];
    return keysToCheck.some(k => disabledList.includes(k));
}

window.isModuleDisabled = isModuleDisabled;

function applyRoleBasedNavigation(payload) {
    if (!payload) return;
    
    const role = payload.role || "";
    const isSysAdmin = role === "System Admin";
    const isAdmin = role === "Admin/Headteacher" || role === "Super Admin" || isSysAdmin;
    const isClassTeacher = payload.is_class_teacher || false;
    const isTeacher = role === "Teacher" || role === "Subject Teacher" || isClassTeacher;
    const isAccountant = role === "Accountant" || role === "Bursar";
    const isLibrarian = role === "Librarian";
    const isStorekeeper = role === "Storekeeper";

    const disabledModules = (payload.disabled_modules || "").toLowerCase().split(",").map(s => s.trim());

    const isParentOrStudent = role === "Parent" || role === "Student";

    const staffMenu = document.getElementById("sidebar-staff-menu");
    const parentMenu = document.getElementById("sidebar-parent-menu");

    if (isParentOrStudent) {
        if (staffMenu) staffMenu.style.display = "none";
        if (parentMenu) parentMenu.style.display = "block";
    } else {
        if (staffMenu) staffMenu.style.display = "block";
        if (parentMenu) parentMenu.style.display = "none";
    }

    // Hide/show sidebar links based on role specifications and branch module access controls
    document.querySelectorAll(".sidebar-nav .nav-link").forEach(link => {
        const target = link.getAttribute("data-target");
        if (!target) return;

        let visible = true;

        if (isParentOrStudent) {
            visible = (target === "panel-parent-portal");
        } else if (target === "panel-parent-portal") {
            visible = isAdmin || isSysAdmin;
        } else if (target === "panel-sysadmin") {
            visible = isSysAdmin;
        } else if (isSysAdmin || isAdmin) {
            visible = true;
        } else if (isClassTeacher) {
            visible = ["panel-dashboard", "panel-attendance", "panel-exams", "panel-result-approvals", "panel-timetable"].includes(target);
        } else if (isTeacher) {
            visible = ["panel-dashboard", "panel-exams", "panel-timetable"].includes(target);
        } else if (isAccountant) {
            visible = ["panel-dashboard", "panel-fees"].includes(target);
        } else if (isLibrarian) {
            visible = ["panel-dashboard", "panel-library"].includes(target);
        } else if (isStorekeeper) {
            visible = ["panel-dashboard", "panel-inventory"].includes(target);
        } else {
            visible = true;
        }

        // Check if module is disabled for this branch by System Administrator
        if (isModuleDisabled(target, disabledModules) && !isSysAdmin) {
            visible = false;
        }

        const parentLi = link.closest("li");
        if (parentLi) {
            parentLi.style.display = visible ? "block" : "none";
        }
    });

    // Result Approvals sub-tab & submit button configuration for Class Teachers vs Headteacher
    const raQueueTabBtn = document.querySelector("#panel-result-approvals .tab-btn[data-tab='tab-ra-head-approval']");
    const raInspectTabBtn = document.querySelector("#panel-result-approvals .tab-btn[data-tab='tab-ra-inspect-sheet']");
    const submitApprBtn = document.getElementById("btn-submit-class-approval");

    if (isClassTeacher && !isAdmin) {
        if (raQueueTabBtn) raQueueTabBtn.style.display = "none";
        if (raInspectTabBtn) {
            raInspectTabBtn.style.display = "inline-block";
            raInspectTabBtn.click();
        }
        if (submitApprBtn) {
            submitApprBtn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Submit to Headteacher for Approval`;
            submitApprBtn.className = "btn btn-primary btn-sm";
        }
    } else if (isAdmin) {
        if (raQueueTabBtn) raQueueTabBtn.style.display = "inline-block";
        if (raInspectTabBtn) raInspectTabBtn.style.display = "inline-block";
        if (submitApprBtn) {
            submitApprBtn.innerHTML = `<i class="fa-solid fa-check-circle"></i> Confirm & Publish Results`;
            submitApprBtn.className = "btn btn-success btn-sm";
        }
    }

    // Sub-tab & New Exam Setup restrictions inside Examinations
    const btnAddExam = document.getElementById("btn-add-exam-trigger");
    if (isTeacher && !isAdmin) {
        if (btnAddExam) btnAddExam.style.display = "none";
        
        const approvalTabBtn = document.querySelector("#panel-exams .tab-btn[data-tab='tab-exam-approvals']");
        if (approvalTabBtn) approvalTabBtn.style.display = "none";
        
        const examListTabBtn = document.querySelector("#panel-exams .tab-btn[data-tab='tab-exam-list']");
        if (examListTabBtn) examListTabBtn.style.display = "none";
        
        const headApprTabBtn = document.querySelector("#panel-exams .tab-btn[data-tab='tab-exam-head-approval']");
        if (headApprTabBtn) headApprTabBtn.style.display = "none";

        const activeTabBtn = document.querySelector("#panel-exams .tab-btn.active");
        if (!activeTabBtn || activeTabBtn.dataset.tab === "tab-exam-list") {
            const resultsTabBtn = document.querySelector("#panel-exams .tab-btn[data-tab='tab-exam-results']");
            if (resultsTabBtn) resultsTabBtn.click();
        }
    } else {
        if (btnAddExam) btnAddExam.style.display = "inline-block";
        const examListTabBtn = document.querySelector("#panel-exams .tab-btn[data-tab='tab-exam-list']");
        if (examListTabBtn) examListTabBtn.style.display = "inline-block";
    }

    // Sub-tab restrictions inside Attendance
    if (isTeacher && !isAdmin) {
        const staffAttTabBtn = document.querySelector("#panel-attendance .tab-btn[data-tab='tab-take-staff-att']");
        if (staffAttTabBtn) {
            staffAttTabBtn.style.display = "none";
        }
    }

    // Timetable generation and setup restrictions for Teachers
    if (isTeacher && !isAdmin) {
        const btnGenTt = document.getElementById("btn-generate-timetable");
        if (btnGenTt) btnGenTt.style.display = "none";
        
        const ttSetupTabBtn = document.querySelector("#panel-timetable .tab-btn[data-tab='tab-timetable-setup']");
        if (ttSetupTabBtn) ttSetupTabBtn.style.display = "none";
    }
}

function applyUserRolePermissions(payload) {
    return applyRoleBasedNavigation(payload);
}
window.applyUserRolePermissions = applyUserRolePermissions;

function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
window.escapeHtml = escapeHtml;

function switchPanel(panelId) {
    if (currentUser) {
        const isSysAdmin = currentUser.role === "System Admin";
        const isAdmin = currentUser.role === "Admin/Headteacher" || currentUser.role === "Super Admin" || isSysAdmin;
        const isClassTeacher = currentUser.is_class_teacher || false;
        const isTeacher = currentUser.role === "Teacher" || currentUser.role === "Subject Teacher" || isClassTeacher;

        if (currentUser.disabled_modules && !isSysAdmin && panelId !== "panel-dashboard") {
            const disabledList = currentUser.disabled_modules.toLowerCase().split(",").map(s => s.trim());
            if (isModuleDisabled(panelId, disabledList)) {
                showToast("This module is currently disabled for your branch by System Administration.", "warning");
                return;
            }
        }

        if (currentUser.role === "Parent" || currentUser.role === "Student") {
            panelId = "panel-parent-portal";
        } else if (panelId === "panel-parent-portal" && !isAdmin) {
            panelId = "panel-dashboard";
        } else if (isTeacher && !isClassTeacher && !isAdmin && panelId === "panel-result-approvals") {
            panelId = "panel-dashboard";
        } else if (isTeacher && !isAdmin && panelId === "panel-report-cards") {
            panelId = "panel-dashboard";
        }
    }

    document.querySelectorAll(".content-panel").forEach(panel => {
        panel.classList.remove("active");
    });
    
    document.querySelectorAll(".nav-link").forEach(link => {
        link.classList.remove("active");
        if (link.getAttribute("data-target") === panelId) {
            link.classList.add("active");
        }
    });
    
    // Branch switcher dropdown visibility (Only shown for System Admin on SysAdmin Panel)
    const headSel = document.getElementById("header-branch-switcher");
    if (headSel) {
        if (currentUser && currentUser.role === "System Admin" && panelId === "panel-sysadmin") {
            headSel.style.display = "inline-block";
        } else {
            headSel.style.display = "none";
        }
    }
    
    const targetPanel = document.getElementById(panelId);
    if (targetPanel) {
        targetPanel.classList.add("active");
        // Scroll content container to top on every panel switch
        const cc = document.querySelector(".content-container");
        if (cc) cc.scrollTop = 0;
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

let activeBranchIdOverride = null;

// --- 3. API Connector Wrapper ---
async function apiFetch(url, options = {}) {
    if (!options.headers) {
        options.headers = {};
    }
    if (currentToken) {
        options.headers["Authorization"] = `Bearer ${currentToken}`;
    }
    if (activeBranchIdOverride) {
        options.headers["X-Branch-ID"] = activeBranchIdOverride.toString();
    }
    if (options.body && !(options.body instanceof FormData)) {
        if (!options.headers["Content-Type"]) {
            options.headers["Content-Type"] = "application/json";
        }
        if (typeof options.body === "object") {
            options.body = JSON.stringify(options.body);
        }
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

function viewPdf(url, filename) {
    const headers = {};
    if (currentToken) {
        headers["Authorization"] = `Bearer ${currentToken}`;
    }
    fetch(url, { headers })
        .then(res => {
            if (res.status === 401) {
                handleLogout();
                throw new Error("Unauthorized access. Logged out.");
            }
            if (!res.ok) {
                throw new Error("Failed to load document");
            }
            return res.blob();
        })
        .then(blob => {
            const blobUrl = URL.createObjectURL(blob);
            window.open(blobUrl, "_blank");
        })
        .catch(err => showToast(err.message, "error"));
}

function openEditStudentModal(studentId) {
    apiFetch(`/api/students/${studentId}`)
        .then(student => {
            document.getElementById("edit-stud-id").value = student.id;
            document.getElementById("edit-stud-fname").value = student.first_name || "";
            document.getElementById("edit-stud-lname").value = student.last_name || "";
            document.getElementById("edit-stud-onames").value = student.other_names || "";
            document.getElementById("edit-stud-gender").value = student.gender || "Male";
            document.getElementById("edit-stud-dob").value = student.dob || "";
            document.getElementById("edit-stud-class").value = student.class_id || "";
            document.getElementById("edit-stud-status").value = student.status || "Active";
            
            // Display photo if it exists
            const img = document.getElementById("edit-photo-preview");
            const placeholder = document.getElementById("edit-photo-placeholder");
            const uploadBtn = document.getElementById("btn-upload-photo");
            const fileInput = document.getElementById("edit-photo-input");
            
            if (fileInput) fileInput.value = "";
            if (uploadBtn) {
                uploadBtn.disabled = true;
                uploadBtn.innerHTML = '<i class="fa-solid fa-upload"></i> Upload';
            }
            
            if (student.photo_path) {
                if (img) {
                    img.src = "/" + student.photo_path + "?t=" + Date.now();
                    img.style.display = "block";
                }
                if (placeholder) placeholder.style.display = "none";
            } else {
                if (img) {
                    img.src = "";
                    img.style.display = "none";
                }
                if (placeholder) placeholder.style.display = "block";
            }

            const parent = student.parent || {};
            document.getElementById("edit-student-parent-fname").value = parent.first_name || "";
            document.getElementById("edit-student-parent-lname").value = parent.last_name || "";
            document.getElementById("edit-student-parent-phone").value = parent.phone || "";
            document.getElementById("edit-student-parent-email").value = parent.email || "";
            document.getElementById("edit-student-parent-occ").value = parent.occupation || "";
            document.getElementById("edit-student-parent-addr").value = parent.address || "";
            
            document.getElementById("modal-edit-student").classList.add("show");
        })
        .catch(err => showToast(err.message, "error"));
}

function openDeleteStudentModal(studentId, name, className) {
    document.getElementById("delete-student-id").value = studentId;
    document.getElementById("delete-student-name").textContent = name;
    document.getElementById("delete-student-meta").textContent = `ID: ${studentId} | Class: ${className}`;
    document.getElementById("modal-delete-student").classList.add("show");
}

// Make them globally available
window.viewPdf = viewPdf;
window.openEditStudentModal = openEditStudentModal;
window.openDeleteStudentModal = openDeleteStudentModal;

// --- 4. Global Events & Theme ---
function initGlobalEventListeners() {
    // Sidebar Toggle Collapse
    const sidebarToggle = document.getElementById("btn-sidebar-toggle");
    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", () => {
            const layout = document.querySelector(".app-layout");
            if (layout) {
                layout.classList.toggle("sidebar-collapsed");
                const isCollapsed = layout.classList.contains("sidebar-collapsed");
                localStorage.setItem("sidebarCollapsed", isCollapsed);
            }
        });
    }

    // Theme Switcher & Dropdown Menu
    const themeBtn = document.getElementById("btn-theme-toggle");
    const themeMenu = document.getElementById("theme-picker-menu");
    const profileTrigger = document.getElementById("profile-info-trigger");
    const dropdownMenu = document.getElementById("profile-dropdown-menu");

    if (themeBtn && themeMenu) {
        themeBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            themeMenu.classList.toggle("show");
            if (dropdownMenu) dropdownMenu.classList.remove("show");
        });
    }

    document.querySelectorAll(".theme-option-card").forEach(card => {
        card.addEventListener("click", (e) => {
            e.stopPropagation();
            const themeKey = card.getAttribute("data-theme");
            setTheme(themeKey);
            if (themeMenu) themeMenu.classList.remove("show");
            const themeName = card.querySelector(".theme-option-name") ? card.querySelector(".theme-option-name").textContent : themeKey;
            showToast(`Theme changed to ${themeName}`, "info");
        });
    });

    if (profileTrigger && dropdownMenu) {
        profileTrigger.addEventListener("click", (e) => {
            e.stopPropagation();
            dropdownMenu.classList.toggle("show");
            if (themeMenu) themeMenu.classList.remove("show");
        });
    }

    document.addEventListener("click", () => {
        if (dropdownMenu) dropdownMenu.classList.remove("show");
        if (themeMenu) themeMenu.classList.remove("show");
    });

    // Logout
    document.getElementById("btn-logout").addEventListener("click", (e) => {
        e.preventDefault();
        handleLogout();
    });

    // User Profile Modal trigger
    document.getElementById("btn-user-profile-modal")?.addEventListener("click", (e) => {
        e.preventDefault();
        if (dropdownMenu) dropdownMenu.classList.remove("show");
        openUserProfileModal();
    });

    // Modals generic close controls
    document.querySelectorAll(".modal-close, .btn-modal-cancel").forEach(btn => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            const modalEl = btn.closest(".modal-backdrop, .modal");
            if (modalEl) modalEl.classList.remove("show");
        });
    });

    // Edit student form submit
    const editForm = document.getElementById("form-edit-student");
    if (editForm) {
        editForm.addEventListener("submit", (e) => {
            e.preventDefault();
            const studentId = document.getElementById("edit-stud-id").value;
            const payload = {
                first_name: document.getElementById("edit-stud-fname").value,
                last_name: document.getElementById("edit-stud-lname").value,
                other_names: document.getElementById("edit-stud-onames").value,
                gender: document.getElementById("edit-stud-gender").value,
                dob: document.getElementById("edit-stud-dob").value,
                class_id: parseInt(document.getElementById("edit-stud-class").value) || null,
                status: document.getElementById("edit-stud-status").value,
                parent: {
                    first_name: document.getElementById("edit-student-parent-fname").value,
                    last_name: document.getElementById("edit-student-parent-lname").value,
                    phone: document.getElementById("edit-student-parent-phone").value,
                    email: document.getElementById("edit-student-parent-email").value,
                    occupation: document.getElementById("edit-student-parent-occ").value,
                    address: document.getElementById("edit-student-parent-addr").value
                }
            };
            
            apiFetch(`/api/students/${studentId}`, {
                method: "PUT",
                body: payload
            })
            .then(() => {
                showToast("Student record updated successfully!", "success");
                document.getElementById("modal-edit-student").classList.remove("show");
                loadStudentsList();
            })
            .catch(err => showToast(err.message, "error"));
        });
    }

    // Student photo input change (local preview & enable upload)
    const photoInput = document.getElementById("edit-photo-input");
    const uploadPhotoBtn = document.getElementById("btn-upload-photo");
    const previewImg = document.getElementById("edit-photo-preview");
    const placeholderIcon = document.getElementById("edit-photo-placeholder");
    
    if (photoInput) {
        photoInput.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (file) {
                if (file.size > 2 * 1024 * 1024) {
                    showToast("File size exceeds 2MB limit", "error");
                    photoInput.value = "";
                    if (uploadPhotoBtn) uploadPhotoBtn.disabled = true;
                    return;
                }
                
                const reader = new FileReader();
                reader.onload = (event) => {
                    if (previewImg) {
                        previewImg.src = event.target.result;
                        previewImg.style.display = "block";
                    }
                    if (placeholderIcon) placeholderIcon.style.display = "none";
                };
                reader.readAsDataURL(file);
                if (uploadPhotoBtn) uploadPhotoBtn.disabled = false;
            }
        });
    }

    // Student photo upload click handler
    if (uploadPhotoBtn) {
        uploadPhotoBtn.addEventListener("click", () => {
            const studentId = document.getElementById("edit-stud-id").value;
            const fileInput = document.getElementById("edit-photo-input");
            const file = fileInput ? fileInput.files[0] : null;
            
            if (!file || !studentId) {
                showToast("Please choose a file first", "error");
                return;
            }
            
            uploadPhotoBtn.disabled = true;
            uploadPhotoBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Uploading...';
            
            const formData = new FormData();
            formData.append("file", file);
            
            apiFetch(`/api/students/${studentId}/photo`, {
                method: "POST",
                body: formData
            })
            .then(data => {
                showToast("Profile picture uploaded successfully!", "success");
                uploadPhotoBtn.innerHTML = '<i class="fa-solid fa-upload"></i> Upload';
                uploadPhotoBtn.disabled = true;
                
                if (previewImg) {
                    previewImg.src = "/" + data.photo_path + "?t=" + Date.now();
                }
                loadStudentsList();
            })
            .catch(err => {
                showToast(err.message, "error");
                uploadPhotoBtn.innerHTML = '<i class="fa-solid fa-upload"></i> Upload';
                uploadPhotoBtn.disabled = false;
            });
        });
    }

    // Delete student confirmation click
    const deleteBtn = document.getElementById("btn-confirm-delete-student");
    if (deleteBtn) {
        deleteBtn.addEventListener("click", () => {
            const studentId = document.getElementById("delete-student-id").value;
            apiFetch(`/api/students/${studentId}`, {
                method: "DELETE"
            })
            .then(res => {
                showToast(res.message || "Student deleted successfully!", "success");
                document.getElementById("modal-delete-student").classList.remove("show");
                loadStudentsList();
            })
            .catch(err => showToast(err.message, "error"));
        });
    }

    initBulkUploadFeatures();
}

// ── LOGIN PAGE CONTROLLER ─────────────────────────────────────────────
// Known sysadmin username prefixes for live indicator (UX only, not security)
const KNOWN_SYSADMIN_PREFIXES = ["sysadmin"];

function initLoginPage() {
    const usernameInput = document.getElementById("login-username");
    const pwdInput      = document.getElementById("login-password");
    const loginForm     = document.getElementById("login-form");
    const togglePwdBtn  = document.getElementById("btn-toggle-password");
    const eyeIcon       = document.getElementById("eye-icon");
    const credsToggle   = document.getElementById("btn-test-creds-toggle");
    const credsPanel    = document.getElementById("test-creds-panel");
    const setupLink     = document.getElementById("link-setup-wizard");

    // Live credential-type indicator
    if (usernameInput) {
        usernameInput.addEventListener("input", () => updateLoginIndicator(usernameInput.value.trim()));
        setTimeout(() => usernameInput.focus(), 300);
    }

    // Password show/hide toggle
    if (togglePwdBtn && pwdInput && eyeIcon) {
        togglePwdBtn.addEventListener("click", () => {
            const hidden = pwdInput.type === "password";
            pwdInput.type = hidden ? "text" : "password";
            eyeIcon.className = hidden ? "fa-solid fa-eye-slash" : "fa-solid fa-eye";
        });
    }

    // Login form submit
    if (loginForm) {
        loginForm.removeEventListener("submit", handleLoginSubmit);
        loginForm.addEventListener("submit", handleLoginSubmit);
    }

    // Test credentials collapsible toggle
    if (credsToggle && credsPanel) {
        credsToggle.addEventListener("click", () => {
            const isOpen = credsPanel.classList.toggle("open");
            credsToggle.classList.toggle("open", isOpen);
            const label = credsToggle.querySelector("span");
            if (label) label.textContent = isOpen ? "Hide test credentials" : "View test credentials";
        });
    }

    // Setup wizard link
    if (setupLink) {
        setupLink.addEventListener("click", () => {
            showView("view-setup");
            initSetupWizard();
        });
    }

    // OTP request & verification listeners
    const btnReqOtp = document.getElementById("btn-request-otp");
    const otpForm   = document.getElementById("login-otp-form");

    if (btnReqOtp) {
        btnReqOtp.addEventListener("click", handleRequestOtp);
    }
    if (otpForm) {
        otpForm.removeEventListener("submit", handleVerifyOtpSubmit);
        otpForm.addEventListener("submit", handleVerifyOtpSubmit);
    }

    // Reset indicator
    updateLoginIndicator("");
}

function switchLoginAuthMode(mode) {
    const credTab = document.getElementById("tab-login-credentials");
    const otpTab = document.getElementById("tab-login-otp");
    const credForm = document.getElementById("login-form");
    const otpForm = document.getElementById("login-otp-form");

    if (mode === "otp") {
        if (credTab) credTab.classList.remove("active");
        if (otpTab) otpTab.classList.add("active");
        if (credForm) credForm.style.display = "none";
        if (otpForm) otpForm.style.display = "block";
    } else {
        if (otpTab) otpTab.classList.remove("active");
        if (credTab) credTab.classList.add("active");
        if (otpForm) otpForm.style.display = "none";
        if (credForm) credForm.style.display = "block";
    }
}
window.switchLoginAuthMode = switchLoginAuthMode;

function parseApiDetailMessage(data, fallbackMsg) {
    if (!data) return fallbackMsg;
    if (typeof data.detail === "string" && data.detail.trim()) return data.detail;
    if (Array.isArray(data.detail) && data.detail.length > 0) {
        return data.detail.map(e => (typeof e === "string" ? e : e.msg || e.detail || JSON.stringify(e))).join(", ");
    }
    if (typeof data.detail === "object" && data.detail !== null) {
        return data.detail.msg || JSON.stringify(data.detail);
    }
    if (data.message && typeof data.message === "string") return data.message;
    return fallbackMsg;
}

function handleRequestOtp(e) {
    if (e) e.preventDefault();
    const phoneInput = document.getElementById("login-otp-phone");
    const btnReq = document.getElementById("btn-request-otp");
    const phone = phoneInput ? phoneInput.value.trim() : "";

    if (!phone) {
        showToast("Please enter your registered phone number", "error");
        return;
    }

    if (btnReq) {
        btnReq.disabled = true;
        btnReq.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Sending...`;
    }

    fetch("/api/auth/request-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone })
    })
    .then(async res => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            throw new Error(parseApiDetailMessage(data, "Failed to request OTP code"));
        }
        return data;
    })
    .then(data => {
        showToast(data.message || "OTP code sent via SMS!", "success");
        if (data.debug_otp) {
            showToast(`[OTP Code] Your verification code is: ${data.debug_otp}`, "info");
        }
        const groupCode = document.getElementById("group-otp-code");
        const btnVerify = document.getElementById("btn-verify-otp");
        if (groupCode) groupCode.style.display = "block";
        if (btnVerify) btnVerify.style.display = "block";
        const codeInput = document.getElementById("login-otp-code");
        if (codeInput) {
            if (data.debug_otp) codeInput.value = data.debug_otp;
            codeInput.focus();
        }
    })
    .catch(err => {
        showToast(err.message || "Failed to request OTP code", "error");
    })
    .finally(() => {
        if (btnReq) {
            btnReq.disabled = false;
            btnReq.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Resend OTP`;
        }
    });
}

function handleVerifyOtpSubmit(e) {
    e.preventDefault();
    const phone = document.getElementById("login-otp-phone").value.trim();
    const otpCode = document.getElementById("login-otp-code").value.trim();
    const btnVerify = document.getElementById("btn-verify-otp");

    if (!phone || !otpCode) {
        showToast("Please enter both phone number and 6-digit OTP code", "error");
        return;
    }

    if (btnVerify) {
        btnVerify.classList.add("loading");
        btnVerify.disabled = true;
    }

    fetch("/api/auth/verify-otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, otp_code: otpCode })
    })
    .then(async res => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            throw new Error(parseApiDetailMessage(data, "Invalid OTP code"));
        }
        return data;
    })
    .then(data => {
        currentToken = data.token;
        localStorage.setItem("orion_token", currentToken);
        showToast(`Welcome, ${data.full_name || "User"}! Signed in via SMS OTP verification`, "success");
        parseTokenAndRoute();
    })
    .catch(err => {
        showToast(err.message || "OTP verification failed", "error");
    })
    .finally(() => {
        if (btnVerify) {
            btnVerify.classList.remove("loading");
            btnVerify.disabled = false;
        }
    });
}

/**
 * Update the live login-type indicator pill.
 * Visual UX only — no auth decision is made client-side.
 */
function updateLoginIndicator(username) {
    const indicator = document.getElementById("login-type-indicator");
    const label     = document.getElementById("indicator-label");
    const icon      = document.getElementById("indicator-icon");
    if (!indicator || !label) return;

    if (!username) {
        indicator.className = "login-type-indicator";
        label.textContent = "Enter your credentials to sign in";
        if (icon) icon.className = "fa-solid fa-circle-info indicator-icon";
        return;
    }

    const looksLikeSysadmin = KNOWN_SYSADMIN_PREFIXES.some(p => username.toLowerCase().startsWith(p));
    if (looksLikeSysadmin) {
        indicator.className = "login-type-indicator is-sysadmin";
        label.textContent = "Detected: System Administrator login";
        if (icon) icon.className = "fa-solid fa-shield-halved indicator-icon";
    } else {
        indicator.className = "login-type-indicator is-branch";
        label.textContent = "Detected: Branch Staff login";
        if (icon) icon.className = "fa-solid fa-school indicator-icon";
    }
}

/**
 * Auto-fill login credentials from the test credentials panel.
 * Called via inline onclick in HTML.
 */
function fillCredentials(username, password) {
    const userInput = document.getElementById("login-username");
    const passInput = document.getElementById("login-password");
    if (userInput) {
        userInput.value = username;
        updateLoginIndicator(username);
    }
    if (passInput) passInput.value = password;
    [userInput, passInput].forEach(el => {
        if (!el) return;
        el.style.transition = "border-color 0.2s, box-shadow 0.2s";
        el.style.borderColor = "var(--accent-primary)";
        el.style.boxShadow = "0 0 0 3px var(--accent-primary-glow)";
        setTimeout(() => { el.style.borderColor = ""; el.style.boxShadow = ""; }, 900);
    });
}

function handleLogout() {
    currentToken = null;
    currentUser = null;
    currentBranchId = null;
    currentBranchName = null;
    initTheme();
    localStorage.removeItem("orion_token");
    const appLayout = document.querySelector(".app-layout");
    if (appLayout) appLayout.classList.remove("is-parent-user");
    showView("view-login");
    initLoginPage();
    showToast("Signed out successfully", "info");
}

function handleLoginSubmit(e) {
    e.preventDefault();

    const username  = document.getElementById("login-username").value.trim();
    const password  = document.getElementById("login-password").value;
    const submitBtn = document.getElementById("btn-login-submit");

    if (!username || !password) {
        showToast("Please enter both username and password", "error");
        return;
    }

    // Show loading state on button
    if (submitBtn) { submitBtn.classList.add("loading"); submitBtn.disabled = true; }

    // First try standard auth endpoint (/api/auth/login) for System Admin, Staff, and Phone logins
    fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, branch_id: null })
    })
    .then(async res => {
        if (!res.ok) {
            // Fallback to parent portal login if standard auth fails
            const parentRes = await fetch("/api/parent/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ branch_code: "MAIN", identifier: username, pin: password })
            });
            if (parentRes.ok) {
                const pData = await parentRes.json();
                return { token: pData.access_token, role: "Parent", full_name: pData.user.full_name, branch_name: pData.user.branch_name, student_id: pData.user.student_id };
            }
            const err = await res.json().catch(() => ({}));
            throw new Error(parseApiDetailMessage(err, "Invalid username or password"));
        }
        return res.json();
    })
    .then(data => {
        const userObj = data.user || data;
        currentToken = data.token || data.access_token;
        localStorage.setItem("orion_token", currentToken);
        const roleLabel = userObj.role === "System Admin"
            ? "System Administrator"
            : `${userObj.role || "User"}${userObj.branch_name ? " — " + userObj.branch_name : ""}`;
        showToast(`Welcome, ${userObj.full_name || userObj.username || "User"}! Signed in as ${roleLabel}`, "success");
        document.getElementById("login-username").value = "";
        document.getElementById("login-password").value = "";
        updateLoginIndicator("");
        parseTokenAndRoute();
    })
    .catch(err => {
        showToast(err.message, "error");
        const card = document.querySelector(".login-card");
        if (card) { card.style.animation = "none"; card.offsetHeight; card.style.animation = "shakeCard 0.4s ease"; }
    })
    .finally(() => {
        if (submitBtn) { submitBtn.classList.remove("loading"); submitBtn.disabled = false; }
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
        
        const btn = document.getElementById("btn-setup-finish");
        if (btn) { btn.disabled = true; btn.innerHTML = 'Initializing... <i class="fa-solid fa-spinner fa-spin"></i>'; }

        fetch("/api/setup/execute", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        })
        .then(async res => {
            if (res.status === 400) {
                const errData = await res.json().catch(() => ({}));
                const msg = errData.detail || "";
                if (msg.toLowerCase().includes("already been completed")) {
                    showToast("Setup is already complete. Please log in.", "info");
                    showView("view-login");
                    initLoginPage();
                    return null;
                }
                throw new Error(msg || "Initialization failed");
            }
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || "Initialization failed");
            }
            return res.json();
        })
        .then(data => {
            if (!data) return; // redirected already
            showToast("System initialized successfully!", "success");
            checkSetupAndVerifyAuth();
        })
        .catch(err => {
            showToast(err.message, "error");
        })
        .finally(() => {
            if (btn) { btn.disabled = false; btn.innerHTML = 'Initialize &amp; Launch <i class="fa-solid fa-rocket"></i>'; }
        });
    });
}

// --- 6. Panel Data Loaders ---
function loadPanelData(panelId) {
    if (panelId === "panel-dashboard") loadDashboard();
    else if (panelId === "panel-students") loadStudentsPanel();
    else if (panelId === "panel-staff") loadStaff();
    else if (panelId === "panel-parents") loadParentsData();
    else if (panelId === "panel-academics") loadAcademics();
    else if (panelId === "panel-attendance") loadAttendanceConfig();
    else if (panelId === "panel-exams") loadExams();
    else if (panelId === "panel-result-approvals") loadResultApprovalsPanel();
    else if (panelId === "panel-report-cards") loadReportCardsPanel();
    else if (panelId === "panel-fees") loadFees();
    else if (panelId === "panel-payroll") loadPayrollPanel();
    else if (panelId === "panel-library") loadLibrary();
    else if (panelId === "panel-inventory") loadInventory();
    else if (panelId === "panel-timetable") loadTimetablePanel();
    else if (panelId === "panel-communication") loadCommunication();
    else if (panelId === "panel-settings") loadSettings();
    else if (panelId === "panel-support-tickets") loadBranchTickets();
    else if (panelId === "panel-sysadmin") loadSysadmin();
    else if (panelId === "panel-parent-portal") loadParentPortalData();
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
            const editSelect = document.getElementById("edit-stud-class");
            const srcSelect = document.getElementById("promo-src-class");
            const destSelect = document.getElementById("promo-target-class");
            
            filter.innerHTML = '<option value="">All Classes</option>';
            admitSelect.innerHTML = '<option value="">— Select class —</option>';
            if (editSelect) editSelect.innerHTML = '<option value="">— Select class —</option>';
            srcSelect.innerHTML = '<option value="">Select source class...</option>';
            destSelect.innerHTML = '<option value="">Select target class...</option>';
            
            classes.forEach(c => {
                const opt = `<option value="${c.id}">${c.name} (${c.stream || "No Stream"})</option>`;
                filter.innerHTML += opt;
                admitSelect.innerHTML += opt;
                if (editSelect) editSelect.innerHTML += opt;
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
                const fullName = `${s.first_name} ${s.last_name}`;
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${s.id}</strong></td>
                        <td>${s.last_name}, ${s.first_name} ${s.other_names || ""}</td>
                        <td>${s.class_name}</td>
                        <td>${s.parent_phone}</td>
                        <td><span class="badge badge-branch">${s.status}</span></td>
                        <td>
                            <div style="display:flex; gap:6px;">
                                <button type="button" class="btn btn-secondary btn-icon" title="Print ID Card" onclick="viewPdf('/api/students/${s.id}/id-card', 'ID_Card_${s.id}.pdf')">
                                    <i class="fa-solid fa-address-card"></i>
                                </button>
                                <button type="button" class="btn btn-secondary btn-icon" title="Print Admission Form" onclick="viewPdf('/api/students/${s.id}/admission-form', 'Admission_Form_${s.id}.pdf')">
                                    <i class="fa-solid fa-file-pdf"></i>
                                </button>
                                <button type="button" class="btn btn-primary btn-icon" title="Edit Student" onclick="openEditStudentModal('${s.id}')">
                                    <i class="fa-solid fa-user-pen"></i>
                                </button>
                                <button type="button" class="btn btn-danger btn-icon" title="Delete Student" onclick="openDeleteStudentModal('${s.id}', '${fullName.replace(/'/g, "\\'")}', '${s.class_name.replace(/'/g, "\\'")}')">
                                    <i class="fa-solid fa-trash"></i>
                                </button>
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
            first_name: document.getElementById("admit-parent-fname").value,
            last_name: document.getElementById("admit-parent-lname").value,
            phone: document.getElementById("admit-parent-phone").value,
            email: document.getElementById("admit-parent-email").value,
            occupation: document.getElementById("admit-parent-occ").value,
            address: document.getElementById("admit-parent-addr").value
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
function bindStaffFilterListeners() {
    const searchInput = document.getElementById("search-staff-input");
    const roleSelect = document.getElementById("filter-staff-role");
    if (searchInput && !searchInput.hasAttribute("data-listener")) {
        searchInput.setAttribute("data-listener", "true");
        searchInput.addEventListener("input", loadStaff);
    }
    if (roleSelect && !roleSelect.hasAttribute("data-listener")) {
        roleSelect.setAttribute("data-listener", "true");
        roleSelect.addEventListener("change", loadStaff);
    }
}

function loadStaff() {
    bindStaffFilterListeners();
    const searchVal = (document.getElementById("search-staff-input")?.value || "").trim();
    const roleVal = (document.getElementById("filter-staff-role")?.value || "").trim();
    
    let url = "/api/staff";
    const params = new URLSearchParams();
    if (searchVal) params.append("search", searchVal);
    if (roleVal) params.append("role", roleVal);
    if (params.toString()) url += `?${params.toString()}`;

    apiFetch(url)
        .then(staff => {
            // Smart client-side filter fallback
            if (searchVal || roleVal) {
                const searchTerms = searchVal.toLowerCase().split(/\s+/).filter(Boolean);
                const rLower = roleVal.toLowerCase();

                staff = staff.filter(s => {
                    const searchableText = [
                        s.id,
                        s.first_name,
                        s.last_name,
                        `${s.first_name} ${s.last_name}`,
                        `${s.last_name}, ${s.first_name}`,
                        s.email,
                        s.phone,
                        s.role_name,
                        s.role_title
                    ].filter(Boolean).join(" ").toLowerCase();

                    const matchesSearch = searchTerms.length === 0 || searchTerms.every(term => searchableText.includes(term));

                    const staffRole = `${s.role_name || ""} ${s.role_title || ""}`.toLowerCase();
                    const matchesRole = !rLower || staffRole.includes(rLower) || rLower.includes(staffRole.split("/")[0] || "");

                    return matchesSearch && matchesRole;
                });
            }

            const tbody = document.querySelector("#staff-table tbody");
            if (!tbody) return;
            tbody.innerHTML = "";

            if (staff.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center">No staff found matching criteria.</td></tr>';
                return;
            }

            staff.forEach(s => {
                const fullName = `${s.first_name} ${s.last_name}`;
                const displayRole = s.role_name || s.role_title || "Staff";
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${s.id}</strong></td>
                        <td>${s.last_name}, ${s.first_name}</td>
                        <td><span class="badge badge-academic">${displayRole}</span></td>
                        <td>${s.email || "N/A"}</td>
                        <td>${s.phone || "N/A"}</td>
                        <td>${(s.base_salary || 0).toFixed(2)} GHS</td>
                        <td>
                            <div style="display:flex; gap:6px;">
                                <button class="btn btn-secondary btn-icon btn-reset-staff-pwd" data-id="${s.id}" title="Reset Portal Password"><i class="fa-solid fa-key"></i></button>
                                <button class="btn btn-primary btn-icon" title="Edit Staff" onclick="openEditStaffModal(${s.id})"><i class="fa-solid fa-user-pen"></i></button>
                                <button class="btn btn-danger btn-icon" title="Delete Staff" onclick="openDeleteStaffModal(${s.id}, '${fullName.replace(/'/g, "\\'")}', '${displayRole.replace(/'/g, "\\'")}')"><i class="fa-solid fa-trash"></i></button>
                            </div>
                        </td>
                    </tr>`;
            });
            
            // Add handler for reset pwd
            document.querySelectorAll(".btn-reset-staff-pwd").forEach(btn => {
                btn.addEventListener("click", () => {
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

function openEditStaffModal(staffId) {
    apiFetch(`/api/staff`)
        .then(staffList => {
            const staff = staffList.find(s => s.id === staffId);
            if (!staff) {
                showToast("Staff member not found", "error");
                return;
            }
            document.getElementById("edit-staff-id").value = staff.id;
            document.getElementById("edit-staff-fname").value = staff.first_name || "";
            document.getElementById("edit-staff-lname").value = staff.last_name || "";
            document.getElementById("edit-staff-username").value = staff.username || "";
            document.getElementById("edit-staff-role").value = staff.role_name || "Teacher";
            document.getElementById("edit-staff-password").value = "";
            document.getElementById("edit-staff-email").value = staff.email || "";
            document.getElementById("edit-staff-phone").value = staff.phone || "";
            document.getElementById("edit-staff-qual").value = staff.qualification || "";
            document.getElementById("edit-staff-salary").value = staff.base_salary || 0.00;
            
            document.getElementById("modal-edit-staff").classList.add("show");
        })
        .catch(err => showToast(err.message, "error"));
}

function openDeleteStaffModal(staffId, name, role) {
    document.getElementById("delete-staff-id").value = staffId;
    document.getElementById("delete-staff-name").textContent = name;
    document.getElementById("delete-staff-meta").textContent = `ID: ${staffId} | Role: ${role}`;
    document.getElementById("modal-delete-staff").classList.add("show");
}

window.openEditStaffModal = openEditStaffModal;
window.openDeleteStaffModal = openDeleteStaffModal;

// Search & filter listeners for Staff Directory
document.getElementById("search-staff-input")?.addEventListener("input", loadStaff);
document.getElementById("filter-staff-role")?.addEventListener("change", loadStaff);

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
        password: document.getElementById("staff-password").value,
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

// Edit Staff form submit handler
document.getElementById("form-edit-staff").addEventListener("submit", (e) => {
    e.preventDefault();
    const staffId = document.getElementById("edit-staff-id").value;
    const payload = {
        first_name: document.getElementById("edit-staff-fname").value,
        last_name: document.getElementById("edit-staff-lname").value,
        username: document.getElementById("edit-staff-username").value,
        role_name: document.getElementById("edit-staff-role").value,
        email: document.getElementById("edit-staff-email").value,
        phone: document.getElementById("edit-staff-phone").value,
        qualification: document.getElementById("edit-staff-qual").value,
        base_salary: parseFloat(document.getElementById("edit-staff-salary").value)
    };
    
    const pwd = document.getElementById("edit-staff-password").value;
    if (pwd && pwd.trim()) {
        payload.password = pwd.trim();
    }
    
    apiFetch(`/api/staff/${staffId}`, {
        method: "PUT",
        body: payload
    })
    .then(() => {
        showToast("Staff member updated successfully", "success");
        document.getElementById("modal-edit-staff").classList.remove("show");
        loadStaff();
    })
    .catch(err => showToast(err.message, "error"));
});

// Delete Staff confirmation handler
document.getElementById("btn-confirm-delete-staff").addEventListener("click", () => {
    const staffId = document.getElementById("delete-staff-id").value;
    apiFetch(`/api/staff/${staffId}`, {
        method: "DELETE"
    })
    .then(res => {
        showToast(res.message || "Staff member deleted successfully", "success");
        document.getElementById("modal-delete-staff").classList.remove("show");
        loadStaff();
    })
    .catch(err => showToast(err.message, "error"));
});

// --- Payroll Panel logic ---
function loadPayrollPanel() {
    apiFetch("/api/payroll/periods")
        .then(periods => {
            const filterSelect = document.getElementById("filter-payroll-period");
            if (!filterSelect) return;
            
            filterSelect.innerHTML = "";
            if (periods.length === 0) {
                filterSelect.innerHTML = '<option value="">— No periods generated —</option>';
                const tbody = document.querySelector("#payroll-table tbody");
                if (tbody) tbody.innerHTML = '<tr><td colspan="9" class="text-center">No payroll generated yet. Click "Run Monthly Payroll" to start.</td></tr>';
                
                document.getElementById("payroll-stat-gross").textContent = "GHS 0.00";
                document.getElementById("payroll-stat-deductions").textContent = "GHS 0.00";
                document.getElementById("payroll-stat-net").textContent = "GHS 0.00";
                return;
            }
            
            periods.forEach(p => {
                filterSelect.innerHTML += `<option value="${p}">${p}</option>`;
            });
            
            loadPayrollForPeriod(filterSelect.value);
        })
        .catch(err => showToast(err.message, "error"));
}

function updatePayrollSelectedState() {
    const selectedCbs = document.querySelectorAll(".payroll-row-cb:checked");
    const countEl = document.getElementById("payroll-selected-count");
    const selectedBtn = document.getElementById("btn-bulk-pay-selected");
    
    let totalSelectedNet = 0;
    selectedCbs.forEach(cb => {
        totalSelectedNet += parseFloat(cb.getAttribute("data-net") || "0");
    });
    
    if (selectedCbs.length > 0) {
        if (countEl) countEl.textContent = `${selectedCbs.length} staff - GHS ${totalSelectedNet.toFixed(2)}`;
        if (selectedBtn) selectedBtn.style.display = "inline-flex";
    } else {
        if (countEl) countEl.textContent = "0";
        if (selectedBtn) selectedBtn.style.display = "none";
    }
}

function loadPayrollForPeriod(period) {
    if (!period) return;
    
    apiFetch(`/api/payroll?pay_period=${encodeURIComponent(period)}`)
        .then(payslips => {
            const tbody = document.querySelector("#payroll-table tbody");
            if (!tbody) return;
            tbody.innerHTML = "";
            
            const selectAllCb = document.getElementById("payroll-select-all");
            if (selectAllCb) {
                selectAllCb.checked = false;
                selectAllCb.onclick = (e) => {
                    document.querySelectorAll(".payroll-row-cb").forEach(cb => {
                        cb.checked = e.target.checked;
                    });
                    updatePayrollSelectedState();
                };
            }
            updatePayrollSelectedState();
            
            let totalGross = 0;
            let totalDeductions = 0;
            let totalNet = 0;
            
            if (payslips.length === 0) {
                tbody.innerHTML = '<tr><td colspan="10" class="text-center">No records found for this period.</td></tr>';
                return;
            }
            
            payslips.forEach(p => {
                totalGross += p.base_salary + p.allowances;
                totalDeductions += p.tax_deductions + p.pension_deductions;
                totalNet += p.net_salary;
                
                const statusBadge = p.status === "Paid" 
                    ? '<span class="badge badge-branch">Paid</span>' 
                    : '<span class="badge badge-academic">Pending</span>';
                    
                const actionButton = p.status === "Paid"
                    ? `<button type="button" class="btn btn-secondary btn-icon" title="Print Payslip" onclick="viewPdf('/api/payroll/payslips/${p.id}/pdf', 'Payslip_${p.staff_id}.pdf')"><i class="fa-solid fa-file-pdf"></i></button>`
                    : `<div style="display:flex; gap:6px;">
                           <button type="button" class="btn btn-primary btn-icon" title="Process Payout" onclick="processSalaryPayment(${p.id}, '${p.staff_name.replace(/'/g, "\\'")}', '${p.pay_period}')"><i class="fa-solid fa-wallet"></i></button>
                           <button type="button" class="btn btn-secondary btn-icon" style="background-color: var(--accent-info); border-color: var(--accent-info);" title="Edit/Adjust Payout" onclick="openEditPayslipModal(${p.id})"><i class="fa-solid fa-pen-to-square"></i></button>
                           <button type="button" class="btn btn-secondary btn-icon" title="Print Payslip" onclick="viewPdf('/api/payroll/payslips/${p.id}/pdf', 'Payslip_${p.staff_id}.pdf')"><i class="fa-solid fa-file-pdf"></i></button>
                       </div>`;
                       
                const rowCb = p.status === "Pending"
                    ? `<input type="checkbox" class="payroll-row-cb" value="${p.id}" data-net="${p.net_salary}" style="cursor:pointer; width:16px; height:16px;" onchange="updatePayrollSelectedState()">`
                    : `<i class="fa-solid fa-circle-check" style="color:var(--accent-success);" title="Paid"></i>`;

                tbody.innerHTML += `
                    <tr>
                        <td style="text-align:center;">${rowCb}</td>
                        <td><strong>STF-${p.staff_id.toString().padStart(4, '0')}</strong></td>
                        <td>${p.staff_name}</td>
                        <td>${p.role_title}</td>
                        <td>${p.base_salary.toFixed(2)} GHS</td>
                        <td>${p.allowances.toFixed(2)} GHS</td>
                        <td>${(p.tax_deductions + p.pension_deductions).toFixed(2)} GHS</td>
                        <td><strong>${p.net_salary.toFixed(2)} GHS</strong></td>
                        <td>${statusBadge}</td>
                        <td>${actionButton}</td>
                    </tr>`;
            });
            
            document.getElementById("payroll-stat-gross").textContent = `GHS ${totalGross.toFixed(2)}`;
            document.getElementById("payroll-stat-deductions").textContent = `GHS ${totalDeductions.toFixed(2)}`;
            document.getElementById("payroll-stat-net").textContent = `GHS ${totalNet.toFixed(2)}`;
        })
        .catch(err => showToast(err.message, "error"));
}

function processSalaryPayment(payslipId, staffName, period) {
    if (!confirm(`Are you sure you want to process salary payment for ${staffName} for the period ${period}? This will update status to Paid and record a Salaries Expense entry.`)) return;
    
    apiFetch(`/api/payroll/${payslipId}/pay`, {
        method: "POST"
    })
    .then(() => {
        showToast(`Salary payment processed for ${staffName} successfully!`, "success");
        const filterSelect = document.getElementById("filter-payroll-period");
        if (filterSelect) loadPayrollForPeriod(filterSelect.value);
    })
    .catch(err => showToast(err.message, "error"));
}

function bulkPayPeriodSalaries() {
    const period = document.getElementById("filter-payroll-period")?.value;
    if (!period) {
        showToast("Please select a pay period first.", "error");
        return;
    }
    
    if (!confirm(`Are you sure you want to process bulk salary payments for ALL pending staff in period ${period}?\n\nThis will mark pending payslips as Paid and record Salaries Expense entries for each staff member.`)) {
        return;
    }

    apiFetch("/api/payroll/bulk-pay", {
        method: "POST",
        body: { pay_period: period }
    })
    .then(res => {
        showToast(res.message || `Bulk salary payment completed for period ${period}!`, "success");
        loadPayrollForPeriod(period);
    })
    .catch(err => showToast(parseApiDetailMessage ? parseApiDetailMessage(err, err.message || "Failed to process bulk payout") : err.message, "error"));
}

function bulkPaySelectedSalaries() {
    const selectedCbs = Array.from(document.querySelectorAll(".payroll-row-cb:checked"));
    if (selectedCbs.length === 0) {
        showToast("No pending staff selected for payout.", "error");
        return;
    }
    
    const ids = selectedCbs.map(cb => parseInt(cb.value));
    let totalNet = 0;
    selectedCbs.forEach(cb => {
        totalNet += parseFloat(cb.getAttribute("data-net") || "0");
    });

    if (!confirm(`Are you sure you want to process bulk salary payment for ${ids.length} selected staff members totaling GHS ${totalNet.toFixed(2)}?`)) {
        return;
    }

    apiFetch("/api/payroll/bulk-pay", {
        method: "POST",
        body: { payslip_ids: ids }
    })
    .then(res => {
        showToast(res.message || `Bulk salary payment completed for ${ids.length} staff!`, "success");
        const period = document.getElementById("filter-payroll-period")?.value;
        if (period) loadPayrollForPeriod(period);
    })
    .catch(err => showToast(parseApiDetailMessage ? parseApiDetailMessage(err, err.message || "Failed to process bulk payout") : err.message, "error"));
}

window.updatePayrollSelectedState = updatePayrollSelectedState;
window.bulkPayPeriodSalaries = bulkPayPeriodSalaries;
window.bulkPaySelectedSalaries = bulkPaySelectedSalaries;

document.getElementById("btn-bulk-pay-period")?.addEventListener("click", bulkPayPeriodSalaries);
document.getElementById("btn-bulk-pay-selected")?.addEventListener("click", bulkPaySelectedSalaries);

function openEditPayslipModal(payslipId) {
    const period = document.getElementById("filter-payroll-period").value;
    apiFetch(`/api/payroll?pay_period=${encodeURIComponent(period)}`)
        .then(payslips => {
            const p = payslips.find(item => item.id === payslipId);
            if (!p) {
                showToast("Payslip not found", "error");
                return;
            }
            
            document.getElementById("edit-payslip-id").value = p.id;
            document.getElementById("edit-payslip-staff-name").textContent = p.staff_name;
            document.getElementById("edit-payslip-meta").textContent = `Period: ${p.pay_period} | Designation: ${p.role_title}`;
            
            document.getElementById("edit-payslip-base").value = p.base_salary.toFixed(2);
            document.getElementById("edit-payslip-allowance").value = p.allowances.toFixed(2);
            document.getElementById("edit-payslip-tax").value = p.tax_deductions.toFixed(2);
            document.getElementById("edit-payslip-tax-type").value = "fixed"; // default to fixed GHS
            document.getElementById("edit-payslip-pension").value = p.pension_deductions.toFixed(2);
            document.getElementById("edit-payslip-pension-type").value = "fixed"; // default to fixed GHS
            document.getElementById("edit-payslip-apply-all").checked = false; // default unchecked
            
            recalculateEditPayslipNet();
            document.getElementById("modal-edit-payslip").classList.add("show");
        })
        .catch(err => showToast(err.message, "error"));
}

function recalculateEditPayslipNet() {
    const base = parseFloat(document.getElementById("edit-payslip-base").value) || 0;
    const allowance = parseFloat(document.getElementById("edit-payslip-allowance").value) || 0;
    
    const taxVal = parseFloat(document.getElementById("edit-payslip-tax").value) || 0;
    const taxType = document.getElementById("edit-payslip-tax-type").value;
    const pensionVal = parseFloat(document.getElementById("edit-payslip-pension").value) || 0;
    const pensionType = document.getElementById("edit-payslip-pension-type").value;
    
    const taxDeduction = taxType === "percent" ? base * (taxVal / 100) : taxVal;
    const pensionDeduction = pensionType === "percent" ? base * (pensionVal / 100) : pensionVal;
    
    const net = base + allowance - taxDeduction - pensionDeduction;
    document.getElementById("edit-payslip-net").textContent = `GHS ${net.toFixed(2)}`;
}

window.loadPayrollPanel = loadPayrollPanel;
window.loadPayrollForPeriod = loadPayrollForPeriod;
window.processSalaryPayment = processSalaryPayment;
window.openEditPayslipModal = openEditPayslipModal;
window.recalculateEditPayslipNet = recalculateEditPayslipNet;

// Trigger monthly payroll modal
document.getElementById("btn-generate-payroll-trigger").addEventListener("click", () => {
    document.getElementById("modal-generate-payroll").classList.add("show");
});

// Generate payroll form submit
document.getElementById("form-generate-payroll").addEventListener("submit", (e) => {
    e.preventDefault();
    const period = document.getElementById("generate-payroll-month").value;
    
    apiFetch("/api/payroll/generate", {
        method: "POST",
        body: { pay_period: period }
    })
    .then(res => {
        showToast(`Successfully generated monthly payroll sheets for ${res.count} active staff members!`, "success");
        document.getElementById("modal-generate-payroll").classList.remove("show");
        loadPayrollPanel();
    })
    .catch(err => showToast(err.message, "error"));
});

// Edit payslip form submit
document.getElementById("form-edit-payslip").addEventListener("submit", (e) => {
    e.preventDefault();
    const id = document.getElementById("edit-payslip-id").value;
    const payload = {
        base_salary: parseFloat(document.getElementById("edit-payslip-base").value) || 0,
        allowances: parseFloat(document.getElementById("edit-payslip-allowance").value) || 0,
        tax_value: parseFloat(document.getElementById("edit-payslip-tax").value) || 0,
        tax_type: document.getElementById("edit-payslip-tax-type").value,
        pension_value: parseFloat(document.getElementById("edit-payslip-pension").value) || 0,
        pension_type: document.getElementById("edit-payslip-pension-type").value,
        apply_to_all: document.getElementById("edit-payslip-apply-all").checked
    };
    
    apiFetch(`/api/payroll/payslips/${id}`, {
        method: "PUT",
        body: payload
    })
    .then(() => {
        showToast("Payslip adjustments processed successfully!", "success");
        document.getElementById("modal-edit-payslip").classList.remove("show");
        const filterSelect = document.getElementById("filter-payroll-period");
        if (filterSelect) loadPayrollForPeriod(filterSelect.value);
    })
    .catch(err => showToast(err.message, "error"));
});

// Add auto recalculation listeners to edit payslip fields
["edit-payslip-base", "edit-payslip-allowance", "edit-payslip-tax", "edit-payslip-tax-type", "edit-payslip-pension", "edit-payslip-pension-type"].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
        el.addEventListener("input", recalculateEditPayslipNet);
        el.addEventListener("change", recalculateEditPayslipNet);
    }
});

// Period filter change listener
document.getElementById("filter-payroll-period").addEventListener("change", (e) => {
    loadPayrollForPeriod(e.target.value);
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

    // Load Class Teachers
    loadClassTeachersList();
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
                            updateHeaderAcademicBadge();
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
                            updateHeaderAcademicBadge();
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
                tbody.innerHTML = '<tr><td colspan="5">No classes registered.</td></tr>';
                return;
            }
            classes.forEach(c => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${c.id}</strong></td>
                    <td>${c.name}</td>
                    <td>${c.level}</td>
                    <td>${c.stream || '—'}</td>
                    <td>
                        <button class="btn btn-sm btn-secondary btn-edit-class"
                            data-id="${c.id}" data-name="${c.name}" data-level="${c.level}" data-stream="${c.stream || ''}">
                            <i class="fa-solid fa-pencil"></i> Edit
                        </button>
                        <button class="btn btn-sm btn-danger btn-delete-class" data-id="${c.id}" data-name="${c.name}" style="margin-left:6px;">
                            <i class="fa-solid fa-trash"></i> Delete
                        </button>
                    </td>`;
                tbody.appendChild(tr);
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
                tbody.innerHTML = '<tr><td colspan="5">No subjects catalogued.</td></tr>';
                return;
            }
            subjects.forEach(s => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${s.id}</strong></td>
                    <td>${s.name}</td>
                    <td>${s.code}</td>
                    <td><span class="badge badge-branch">${s.category}</span></td>
                    <td>
                        <button class="btn btn-sm btn-primary btn-edit-subject" data-id="${s.id}" data-name="${s.name}" data-code="${s.code}" data-category="${s.category}" style="margin-right: 6px;">
                            <i class="fa-solid fa-pen-to-square"></i> Edit
                        </button>
                        <button class="btn btn-sm btn-danger btn-delete-subject" data-id="${s.id}" data-name="${s.name}">
                            <i class="fa-solid fa-trash"></i> Delete
                        </button>
                    </td>`;
                tbody.appendChild(tr);
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
                tbody.innerHTML = '<tr><td colspan="4">No teaching assignments recorded.</td></tr>';
                return;
            }
            assigns.forEach(a => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td>${a.class_name}</td>
                    <td>${a.subject_name}</td>
                    <td><strong>${a.teacher_name}</strong></td>
                    <td>
                        <button class="btn btn-sm btn-secondary btn-edit-assignment" data-id="${a.id}"
                            data-teacher="${a.teacher_id || ''}" data-class="${a.class_id || ''}" data-subject="${a.subject_id || ''}">
                            <i class="fa-solid fa-pencil"></i> Edit
                        </button>
                        <button class="btn btn-sm btn-danger btn-delete-assignment" data-id="${a.id}" style="margin-left:6px;">
                            <i class="fa-solid fa-trash"></i> Delete
                        </button>
                    </td>`;
                tbody.appendChild(tr);
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

// ── Class Teachers Tab ──────────────────────────────────────────────────────

function loadClassTeachersList() {
    // Populate class selects
    apiFetch("/api/academics/classes")
        .then(classes => {
            const sel = document.getElementById("ct-class-select");
            const editSel = document.getElementById("edit-ct-class-select");
            if (sel) {
                sel.innerHTML = '<option value="">— Select Class —</option>';
                classes.forEach(c => {
                    sel.innerHTML += `<option value="${c.id}">${c.name} (${c.level}${c.stream ? ' ' + c.stream : ''})</option>`;
                });
            }
            if (editSel) {
                editSel.innerHTML = '<option value="">— Select Class —</option>';
                classes.forEach(c => {
                    editSel.innerHTML += `<option value="${c.id}">${c.name} (${c.level}${c.stream ? ' ' + c.stream : ''})</option>`;
                });
            }
        });

    // Populate teacher selects (only staff with teacher-like roles)
    apiFetch("/api/staff")
        .then(staff => {
            const sel = document.getElementById("ct-teacher-select");
            const editSel = document.getElementById("edit-ct-teacher-select");
            if (sel) {
                sel.innerHTML = '<option value="">— Select Teacher —</option>';
                staff.forEach(t => {
                    sel.innerHTML += `<option value="${t.id}">${t.first_name} ${t.last_name} (${t.role_name})</option>`;
                });
            }
            if (editSel) {
                editSel.innerHTML = '<option value="">— Select Teacher —</option>';
                staff.forEach(t => {
                    editSel.innerHTML += `<option value="${t.id}">${t.first_name} ${t.last_name} (${t.role_name})</option>`;
                });
            }
        });

    // Load existing assignments table
    apiFetch("/api/academics/class-teachers")
        .then(list => {
            const tbody = document.querySelector("#class-teachers-table tbody");
            if (!tbody) return;
            tbody.innerHTML = "";
            if (list.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center">No class teachers assigned yet.</td></tr>';
                return;
            }
            list.forEach((a, i) => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${i + 1}</strong></td>
                    <td>
                        <span style="font-weight:600;">${a.class_name}</span>
                    </td>
                    <td>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#8b5cf6);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:13px;flex-shrink:0;">
                                ${a.teacher_name.charAt(0).toUpperCase()}
                            </div>
                            <strong>${a.teacher_name}</strong>
                        </div>
                    </td>
                    <td><span class="badge badge-academic">${a.academic_year}</span></td>
                    <td>
                        <button class="btn btn-sm btn-secondary btn-edit-class-teacher" data-id="${a.id}" data-class="${a.class_id}" data-teacher="${a.staff_id}" style="margin-right:6px;">
                            <i class="fa-solid fa-pencil"></i> Edit
                        </button>
                        <button class="btn btn-sm btn-danger btn-remove-class-teacher" data-id="${a.id}" data-class="${a.class_name}" data-teacher="${a.teacher_name}">
                            <i class="fa-solid fa-user-minus"></i> Remove
                        </button>
                    </td>`;
                tbody.appendChild(tr);
            });
        });
}

// Form submit — assign class teacher
const formAssignCT = document.getElementById("form-assign-class-teacher");
if (formAssignCT) {
    formAssignCT.addEventListener("submit", (e) => {
        e.preventDefault();
        const classId = document.getElementById("ct-class-select").value;
        const staffId = document.getElementById("ct-teacher-select").value;
        if (!classId || !staffId) {
            showToast("Please select both a class and a teacher.", "error");
            return;
        }
        apiFetch("/api/academics/class-teachers", {
            method: "POST",
            body: { class_id: parseInt(classId), staff_id: parseInt(staffId) }
        })
        .then(() => {
            showToast("Class teacher assigned successfully!", "success");
            formAssignCT.reset();
            loadClassTeachersList();
        })
        .catch(err => showToast(err.message, "error"));
    });
}

// Delete delegation — remove class teacher
document.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-remove-class-teacher");
    if (btn) {
        const id = btn.dataset.id;
        const className = btn.dataset.class;
        const teacherName = btn.dataset.teacher;
        if (!confirm(`Remove ${teacherName} as class teacher for ${className}?`)) return;
        apiFetch(`/api/academics/class-teachers/${id}`, { method: "DELETE" })
            .then(() => {
                showToast(`Class teacher removed from ${className}.`, "success");
                loadClassTeachersList();
            })
            .catch(err => showToast(err.message, "error"));
        return;
    }

    const editBtn = e.target.closest(".btn-edit-class-teacher");
    if (editBtn) {
        document.getElementById("edit-ct-id").value = editBtn.dataset.id;
        
        const classSel = document.getElementById("edit-ct-class-select");
        if (classSel) classSel.value = editBtn.dataset.class;
        
        const teacherSel = document.getElementById("edit-ct-teacher-select");
        if (teacherSel) teacherSel.value = editBtn.dataset.teacher;
        
        const modal = document.getElementById("modal-edit-class-teacher");
        if (modal) modal.classList.add("show");
    }
});

// Save edited class teacher
const formEditCT = document.getElementById("form-edit-class-teacher");
if (formEditCT) {
    formEditCT.addEventListener("submit", (e) => {
        e.preventDefault();
        const id = document.getElementById("edit-ct-id").value;
        const classId = document.getElementById("edit-ct-class-select").value;
        const staffId = document.getElementById("edit-ct-teacher-select").value;
        
        apiFetch(`/api/academics/class-teachers/${id}`, {
            method: "PUT",
            body: { class_id: parseInt(classId), staff_id: parseInt(staffId) }
        })
        .then(() => {
            showToast("Class teacher assignment updated successfully!", "success");
            const modal = document.getElementById("modal-edit-class-teacher");
            if (modal) modal.classList.remove("show");
            loadClassTeachersList();
        })
        .catch(err => showToast(err.message, "error"));
    });
}

// --- Academic Item Deletion / Edit Handlers (delegated) ---

// Delete Subject
document.querySelector("#subjects-list-table tbody").addEventListener("click", (e) => {
    // Delete Subject
    const btnDel = e.target.closest(".btn-delete-subject");
    if (btnDel) {
        const id = btnDel.dataset.id;
        const name = btnDel.dataset.name;
        if (!confirm(`Delete subject "${name}"? This will remove it from all teacher assignments.`)) return;
        apiFetch(`/api/academics/subjects/${id}`, { method: "DELETE" })
            .then(() => {
                showToast(`Subject "${name}" deleted.`, "success");
                loadSubjectsList();
                loadAssignmentsList();
            })
            .catch(err => showToast(err.message, "error"));
        return;
    }

    // Edit Subject
    const btnEdit = e.target.closest(".btn-edit-subject");
    if (btnEdit) {
        document.getElementById("edit-subject-id").value = btnEdit.dataset.id;
        document.getElementById("edit-subject-name-input").value = btnEdit.dataset.name;
        document.getElementById("edit-subject-code-input").value = btnEdit.dataset.code;
        const catSel = document.getElementById("edit-subject-category-select");
        [...catSel.options].forEach(o => o.selected = (o.value === btnEdit.dataset.category));
        document.getElementById("modal-edit-subject").classList.add("show");
    }
});

// Delete Class
document.querySelector("#classes-list-table tbody").addEventListener("click", (e) => {
    const delBtn = e.target.closest(".btn-delete-class");
    if (delBtn) {
        const id = delBtn.dataset.id;
        const name = delBtn.dataset.name;
        if (!confirm(`Delete class "${name}"? Students assigned to this class will be unlinked.`)) return;
        apiFetch(`/api/academics/classes/${id}`, { method: "DELETE" })
            .then(() => {
                showToast(`Class "${name}" deleted.`, "success");
                loadClassesList();
                loadAssignmentsList();
            })
            .catch(err => showToast(err.message, "error"));
        return;
    }

    // Edit Class — open modal
    const editBtn = e.target.closest(".btn-edit-class");
    if (editBtn) {
        document.getElementById("edit-class-id").value = editBtn.dataset.id;
        document.getElementById("edit-class-name").value = editBtn.dataset.name;
        document.getElementById("edit-class-stream").value = editBtn.dataset.stream;
        const levelSel = document.getElementById("edit-class-level");
        [...levelSel.options].forEach(o => o.selected = (o.value === editBtn.dataset.level));
        document.getElementById("modal-edit-class").classList.add("show");
    }
});

// Save edited subject
document.getElementById("form-edit-subject").addEventListener("submit", (e) => {
    e.preventDefault();
    const id = document.getElementById("edit-subject-id").value;
    const payload = {
        name: document.getElementById("edit-subject-name-input").value,
        code: document.getElementById("edit-subject-code-input").value,
        category: document.getElementById("edit-subject-category-select").value
    };
    apiFetch(`/api/academics/subjects/${id}`, { method: "PUT", body: payload })
        .then(() => {
            showToast("Subject updated successfully", "success");
            document.getElementById("modal-edit-subject").classList.remove("show");
            loadSubjectsList();
            loadAssignmentsList();
        })
        .catch(err => showToast(err.message, "error"));
});

// Save edited class
document.getElementById("form-edit-class").addEventListener("submit", (e) => {
    e.preventDefault();
    const id = document.getElementById("edit-class-id").value;
    const payload = {
        name: document.getElementById("edit-class-name").value,
        level: document.getElementById("edit-class-level").value,
        stream: document.getElementById("edit-class-stream").value
    };
    apiFetch(`/api/academics/classes/${id}`, { method: "PUT", body: payload })
        .then(() => {
            showToast("Class updated successfully", "success");
            document.getElementById("modal-edit-class").classList.remove("show");
            loadClassesList();
        })
        .catch(err => showToast(err.message, "error"));
});

// Assignments — Edit / Delete
document.querySelector("#assignments-list-table tbody").addEventListener("click", (e) => {
    const delBtn = e.target.closest(".btn-delete-assignment");
    if (delBtn) {
        const id = delBtn.dataset.id;
        if (!confirm("Remove this teacher assignment?")) return;
        apiFetch(`/api/academics/assignments/${id}`, { method: "DELETE" })
            .then(() => {
                showToast("Assignment removed.", "success");
                loadAssignmentsList();
            })
            .catch(err => showToast(err.message, "error"));
        return;
    }

    const editBtn = e.target.closest(".btn-edit-assignment");
    if (editBtn) {
        document.getElementById("edit-assignment-id").value = editBtn.dataset.id;
        // Pre-populate dropdowns
        Promise.all([
            apiFetch("/api/staff"),
            apiFetch("/api/academics/classes"),
            apiFetch("/api/academics/subjects")
        ]).then(([teachers, classes, subjects]) => {
            const tSel = document.getElementById("edit-assign-teacher-select");
            const cSel = document.getElementById("edit-assign-class-select");
            const sSel = document.getElementById("edit-assign-subject-select");
            tSel.innerHTML = '<option value="">— Select Teacher —</option>';
            teachers.forEach(t => {
                tSel.innerHTML += `<option value="${t.id}">${t.last_name}, ${t.first_name}</option>`;
            });
            cSel.innerHTML = '<option value="">— Select Class —</option>';
            classes.forEach(c => {
                cSel.innerHTML += `<option value="${c.id}">${c.name}</option>`;
            });
            sSel.innerHTML = '<option value="">— Select Subject —</option>';
            subjects.forEach(s => {
                sSel.innerHTML += `<option value="${s.id}">${s.name}</option>`;
            });
            // Set pre-selected values after population
            tSel.value = editBtn.dataset.teacher || "";
            cSel.value = editBtn.dataset.class || "";
            sSel.value = editBtn.dataset.subject || "";
            document.getElementById("modal-edit-assignment").classList.add("show");
        });
    }
});

// Save edited assignment
document.getElementById("form-edit-assignment").addEventListener("submit", (e) => {
    e.preventDefault();
    const id = document.getElementById("edit-assignment-id").value;
    const payload = {
        teacher_id: parseInt(document.getElementById("edit-assign-teacher-select").value),
        class_id: parseInt(document.getElementById("edit-assign-class-select").value),
        subject_id: parseInt(document.getElementById("edit-assign-subject-select").value)
    };
    apiFetch(`/api/academics/assignments/${id}`, { method: "PUT", body: payload })
        .then(() => {
            showToast("Assignment updated successfully", "success");
            document.getElementById("modal-edit-assignment").classList.remove("show");
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

let currentGradingScale = [];

function ensureGradingScaleLoaded() {
    if (currentGradingScale.length > 0) return Promise.resolve(currentGradingScale);
    return apiFetch("/api/settings/grades")
        .then(grades => {
            currentGradingScale = grades.sort((a, b) => b.min_score - a.min_score);
            return currentGradingScale;
        });
}

function getRemarkForScore(score) {
    if (!currentGradingScale || currentGradingScale.length === 0) return "";
    for (let i = 0; i < currentGradingScale.length; i++) {
        if (score >= currentGradingScale[i].min_score) {
            return currentGradingScale[i].remark;
        }
    }
    return "";
}

function getGradeForScore(score) {
    if (!currentGradingScale || currentGradingScale.length === 0) return "9";
    for (let i = 0; i < currentGradingScale.length; i++) {
        if (score >= currentGradingScale[i].min_score) {
            return currentGradingScale[i].grade;
        }
    }
    return "9";
}

// --- Exams Panel logic ---
function loadExams() {
    initTabs("panel-exams");
    applyRoleBasedNavigation(currentUser);
    ensureGradingScaleLoaded();
    loadResultApprovalDropdowns();
    loadPendingApprovals();
    
    // Config Exams
    apiFetch("/api/exams")
        .then(exams => {
             const tbody = document.querySelector("#exams-list-table tbody");
             const select = document.getElementById("results-exam-select");
             const selectReport = document.getElementById("reports-exam-select");
             tbody.innerHTML = "";
             select.innerHTML = '<option value="">Select exam...</option>';
             selectReport.innerHTML = '<option value="">Select exam...</option>';
             
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
                 selectReport.innerHTML += `<option value="${e.id}">${e.name}</option>`;
             });
        });
        
    // Results dropdown loaders
    apiFetch("/api/academics/classes")
        .then(classes => {
             const select = document.getElementById("results-class-select");
             const selectReport = document.getElementById("reports-class-select");
             select.innerHTML = '<option value="">Select class...</option>';
             selectReport.innerHTML = '<option value="">Select class...</option>';
             classes.forEach(c => {
                 select.innerHTML += `<option value="${c.id}">${c.name}</option>`;
                 selectReport.innerHTML += `<option value="${c.id}">${c.name}</option>`;
             });
        });
    apiFetch("/api/academics/subjects")
        .then(subjects => {
             const select = document.getElementById("results-subject-select");
             select.innerHTML = '<option value="">Select subject...</option>';
             subjects.forEach(s => select.innerHTML += `<option value="${s.id}">${s.name}</option>`);
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
    
    ensureGradingScaleLoaded().then(() => {
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
                      const totalScore = parseFloat(r.class_score) + parseFloat(r.exam_score);
                      const gradeLetter = getGradeForScore(totalScore);
                      tbody.innerHTML += `
                          <tr data-id="${r.student_id}">
                              <td><strong>${r.student_id}</strong></td>
                              <td>${r.student_name}</td>
                              <td><input type="number" step="0.1" min="0" max="30" class="form-control res-class-score" value="${r.class_score}" style="width:100px;" placeholder="Max 30"></td>
                              <td><input type="number" step="0.1" min="0" max="70" class="form-control res-exam-score" value="${r.exam_score}" style="width:100px;" placeholder="Max 70"></td>
                              <td class="res-total-score-val" style="font-weight: 600; vertical-align: middle;">${totalScore.toFixed(1)}</td>
                              <td style="vertical-align: middle;"><span class="badge badge-branch res-grade-val">${gradeLetter}</span></td>
                              <td><input type="text" class="form-control res-remarks" value="${r.remarks || ""}"></td>
                          </tr>`;
                 });
                 form.style.display = "block";
                 document.getElementById("btn-print-summary-pdf").removeAttribute("disabled");
            })
            .catch(err => showToast(err.message, "error"));
    });
});

document.getElementById("results-table").addEventListener("input", (e) => {
    if (e.target.classList.contains("res-class-score") || e.target.classList.contains("res-exam-score")) {
        const row = e.target.closest("tr");
        const classInput = row.querySelector(".res-class-score");
        const examInput = row.querySelector(".res-exam-score");
        
        let classVal = parseFloat(classInput.value) || 0.0;
        let examVal = parseFloat(examInput.value) || 0.0;
        
        if (classVal > 30.0) {
            classInput.value = 30;
            classVal = 30.0;
        } else if (classVal < 0.0) {
            classInput.value = 0;
            classVal = 0.0;
        }
        
        if (examVal > 70.0) {
            examInput.value = 70;
            examVal = 70.0;
        } else if (examVal < 0.0) {
            examInput.value = 0;
            examVal = 0.0;
        }
        
        const total = classVal + examVal;
        const remark = getRemarkForScore(total);
        const grade = getGradeForScore(total);
        row.querySelector(".res-total-score-val").innerText = total.toFixed(1);
        row.querySelector(".res-grade-val").innerText = grade;
        row.querySelector(".res-remarks").value = remark;
    }
});

document.getElementById("btn-print-summary-pdf").addEventListener("click", () => {
     const eid = document.getElementById("results-exam-select").value;
     const cid = document.getElementById("results-class-select").value;
     if(!eid || !cid) {
          showToast("Please select exam and class first", "error");
          return;
     }
     const tokenParam = currentToken ? `&token=${encodeURIComponent(currentToken)}` : '';
     window.open(`/api/exams/reports/summary?class_id=${cid}&exam_id=${eid}${tokenParam}`, "_blank");
});

document.getElementById("results-sheet-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const eid = parseInt(document.getElementById("results-exam-select").value);
    const cid = parseInt(document.getElementById("results-class-select").value);
    const sid = parseInt(document.getElementById("results-subject-select").value);
    
    const scores = [];
    let hasValidationError = false;
    document.querySelectorAll("#results-table tbody tr").forEach(row => {
         const studentId = row.getAttribute("data-id");
         const classScore = parseFloat(row.querySelector(".res-class-score").value) || 0.0;
         const examScore = parseFloat(row.querySelector(".res-exam-score").value) || 0.0;
         const remarks = row.querySelector(".res-remarks").value;
         
         if (classScore > 30.0) {
              showToast(`Student ${studentId}: Class Score cannot exceed 30`, "error");
              hasValidationError = true;
         }
         if (examScore > 70.0) {
              showToast(`Student ${studentId}: Exam Score cannot exceed 70`, "error");
              hasValidationError = true;
         }
         
         scores.push({ student_id: studentId, class_score: classScore, exam_score: examScore, remarks: remarks });
    });
    
    if (hasValidationError) return;
    
    apiFetch("/api/exams/results", {
         method: "POST",
         body: { class_id: cid, subject_id: sid, exam_id: eid, scores: scores }
    })
    .then(() => showToast("Scoresheet saved successfully!", "success"))
    .catch(err => showToast(err.message, "error"));
});

// Grading scale updates are handled via the Save button on the configurations table.

document.getElementById("btn-load-reports-summary").addEventListener("click", () => {
    const eid = document.getElementById("reports-exam-select").value;
    const cid = document.getElementById("reports-class-select").value;
    
    if (!eid || !cid) {
        showToast("Please choose exam and class first", "error");
        return;
    }
    
    apiFetch(`/api/exams/reports/summary-data?class_id=${cid}&exam_id=${eid}`)
        .then(data => {
            const container = document.getElementById("reports-summary-container");
            const headerRow = document.getElementById("reports-summary-headers");
            const tbody = document.getElementById("reports-summary-body");
            const btnPdf = document.getElementById("btn-download-reports-pdf");
            
            // Set title
            document.getElementById("reports-summary-title").innerText = `${data.class_name} - ${data.exam_title} Summary`;
            
            // Build headers
            headerRow.innerHTML = `
                <th style="width: 120px;">Student ID</th>
                <th>Student Name</th>
            `;
            data.subjects.forEach(sub => {
                headerRow.innerHTML += `<th>${sub.name}</th>`;
            });
            headerRow.innerHTML += `
                <th style="width: 100px; text-align: center;">Total Score</th>
                <th style="width: 100px; text-align: center;">Average</th>
                <th style="width: 80px; text-align: center;">Rank</th>
            `;
            
            // Build rows
            tbody.innerHTML = "";
            if (data.results.length === 0) {
                tbody.innerHTML = `<tr><td colspan="${3 + data.subjects.length}" class="text-center">No students or assessment records found for this class.</td></tr>`;
                btnPdf.setAttribute("disabled", "true");
            } else {
                data.results.forEach(r => {
                    let subCells = "";
                    data.subjects.forEach(sub => {
                        const sc = r.scores[sub.id] !== undefined ? r.scores[sub.id] : 0.0;
                        subCells += `<td>${sc.toFixed(1)}</td>`;
                    });
                    
                    tbody.innerHTML += `
                        <tr>
                            <td><strong>${r.student_id}</strong></td>
                            <td>${r.name}</td>
                            ${subCells}
                            <td class="text-center" style="font-weight: 600;">${r.total.toFixed(1)}</td>
                            <td class="text-center" style="font-weight: 600;">${r.avg.toFixed(1)}</td>
                            <td class="text-center" style="font-weight: 700; color: var(--accent-primary);">${r.rank}</td>
                        </tr>
                    `;
                });
                btnPdf.removeAttribute("disabled");
            }
            
            container.style.display = "block";
        })
        .catch(err => showToast(err.message, "error"));
});

document.getElementById("btn-download-reports-pdf").addEventListener("click", () => {
    const eid = document.getElementById("reports-exam-select").value;
    const cid = document.getElementById("reports-class-select").value;
    if(!eid || !cid) {
        showToast("Please choose exam and class first", "error");
        return;
    }
    const tokenParam = currentToken ? `&token=${encodeURIComponent(currentToken)}` : '';
    window.open(`/api/exams/reports/summary?class_id=${cid}&exam_id=${eid}${tokenParam}`, "_blank");
});

// --- Standalone Result Approvals Module logic ---
function loadResultApprovalsPanel() {
    initTabs("panel-result-approvals");
    loadResultApprovalDropdowns();
    loadPendingApprovals();
}

// --- Standalone Report Cards Module logic ---
function loadReportCardsPanel() {
    initTabs("panel-report-cards");
    loadResultApprovalDropdowns();
    loadPendingApprovals();
}

function loadResultApprovalDropdowns() {
    apiFetch("/api/academics/years")
        .then(years => {
            const selects = [
                document.getElementById("approval-year-select"),
                document.getElementById("rc-search-year-select"),
                document.getElementById("rc-student-year-select"),
                document.getElementById("rc-class-year-select")
            ];
            selects.forEach(select => {
                if (!select) return;
                select.innerHTML = '<option value="">Select academic year...</option>';
                years.forEach(y => {
                    const selected = y.is_current ? 'selected' : '';
                    select.innerHTML += `<option value="${y.id}" ${selected}>${y.name}</option>`;
                });
            });
        });

    apiFetch("/api/academics/terms")
        .then(terms => {
            const selects = [
                document.getElementById("approval-term-select"),
                document.getElementById("rc-search-term-select"),
                document.getElementById("rc-student-term-select"),
                document.getElementById("rc-class-term-select")
            ];
            selects.forEach(select => {
                if (!select) return;
                select.innerHTML = '<option value="">Select term/semester...</option>';
                terms.forEach(t => {
                    const selected = t.is_current ? 'selected' : '';
                    select.innerHTML += `<option value="${t.id}" ${selected}>${t.name} (${t.year_name})</option>`;
                });
            });
        });

    apiFetch("/api/academics/classes")
        .then(classes => {
            const selects = [
                document.getElementById("approval-class-select"),
                document.getElementById("rc-search-class-select"),
                document.getElementById("rc-class-class-select")
            ];
            selects.forEach(select => {
                if (!select) return;
                select.innerHTML = '<option value="">Select class...</option>';
                classes.forEach(c => {
                    select.innerHTML += `<option value="${c.id}">${c.name}</option>`;
                });
            });
        });
}

function loadResultApprovalSheet(customCid = null, customYid = null, customTid = null) {
    if (customCid && typeof customCid === 'object') customCid = null;
    if (customYid && typeof customYid === 'object') customYid = null;
    if (customTid && typeof customTid === 'object') customTid = null;

    const yid = customYid || document.getElementById("approval-year-select")?.value;
    const tid = customTid || document.getElementById("approval-term-select")?.value;
    const cid = customCid || document.getElementById("approval-class-select")?.value;

    if (!yid || !tid || !cid) {
        showToast("Please choose Academic Year, Term/Semester, and Class", "error");
        return;
    }

    if (customYid && document.getElementById("approval-year-select")) document.getElementById("approval-year-select").value = customYid;
    if (customTid && document.getElementById("approval-term-select")) document.getElementById("approval-term-select").value = customTid;
    if (customCid && document.getElementById("approval-class-select")) document.getElementById("approval-class-select").value = customCid;

    apiFetch(`/api/exams/approvals/sheet?class_id=${cid}&academic_year_id=${yid}&term_id=${tid}`)
        .then(data => {
            const form = document.getElementById("approval-sheet-form");
            const banner = document.getElementById("approval-status-banner");
            const tbody = document.getElementById("approval-table-body");
            tbody.innerHTML = "";

            banner.style.display = "block";
            let statusBadgeClass = "status-draft";
            let statusIcon = "fa-file-lines";
            let statusText = `Status: DRAFT — Enter remarks & interests, then click 'Confirm and Submit'`;

            if (data.status === "Pending Approval") {
                statusBadgeClass = "status-pending";
                statusIcon = "fa-clock";
                statusText = `Status: PENDING HEADTEACHER APPROVAL (Submitted by ${data.submitted_by || 'Class Teacher'} on ${data.submitted_at || 'N/A'})`;
            } else if (data.status === "Approved") {
                statusBadgeClass = "status-approved";
                statusIcon = "fa-circle-check";
                statusText = `Status: APPROVED & PUBLISHED (Approved by ${data.approved_by || 'Headteacher'} on ${data.approved_at || 'N/A'})`;
            } else if (data.status === "Rejected") {
                statusBadgeClass = "status-rejected";
                statusIcon = "fa-circle-xmark";
                statusText = `Status: REJECTED / REVISION REQUESTED (Reason: ${data.rejection_reason || 'See feedback'})`;
            }

            banner.className = `status-banner ${statusBadgeClass} mt-15 mb-15`;
            banner.innerHTML = `
                <div style="display:flex; align-items:center; gap:8px;">
                    <i class="fa-solid ${statusIcon}"></i>
                    <span>${statusText}</span>
                </div>
                ${data.status === "Approved" ? '<span class="badge badge-branch">Locked & Published</span>' : ''}
            `;

            const activeAuthToken = localStorage.getItem("orion_token") || localStorage.getItem("token") || currentToken || "";
            const tokenQuery = activeAuthToken ? `&token=${encodeURIComponent(activeAuthToken)}` : "";

            const pdfBtn = document.getElementById("btn-class-report-pdf");
            const zipBtn = document.getElementById("btn-class-report-zip");
            if (pdfBtn) {
                pdfBtn.style.display = data.exam_id ? "inline-flex" : "none";
                pdfBtn.onclick = () => window.open(`/api/exams/reports/class/${cid}?exam_id=${data.exam_id}${tokenQuery}`, "_blank");
            }
            if (zipBtn) {
                zipBtn.style.display = data.exam_id ? "inline-flex" : "none";
                zipBtn.onclick = () => window.open(`/api/exams/reports/class-zip/${cid}?exam_id=${data.exam_id}${tokenQuery}`, "_blank");
            }

            if (data.students.length === 0) {
                tbody.innerHTML = '<tr><td colspan="10" class="text-center p-20">No active students found in this class.</td></tr>';
                form.style.display = "block";
                return;
            }

            const remarkOptions = [
                "An outstanding academic performance! Keep up the excellent work.",
                "Very good progress made this term. Recommended for higher honors.",
                "Good effort overall. Focus on core subject revisions.",
                "Satisfactory performance. More diligence required.",
                "Needs improvement in continuous assessment scores.",
                "Promising performance. Shows diligence and effort. Keep up the high standard."
            ];

            const interestOptions = [
                "General Agricultural Science",
                "Mathematics & Computing",
                "Science & Technology",
                "Visual & Performing Arts",
                "Sports & Athletics",
                "Languages & Literature",
                "Business & Entrepreneurship",
                "Social Sciences & Leadership",
                "Music & Creative Media"
            ];

            const attitudeOptions = ["Very Good", "Excellent", "Good", "Satisfactory", "Needs Improvement"];

            data.students.forEach((s, idx) => {
                const rankClass = s.class_rank === 1 ? "rank-1" : s.class_rank === 2 ? "rank-2" : s.class_rank === 3 ? "rank-3" : "rank-other";
                const rowId = `app-row-${idx}`;
                const detailRowId = `app-detail-${idx}`;

                let remarkOptionsHtml = `<option value="">Select or type remark...</option>`;
                remarkOptions.forEach(opt => {
                    const sel = (s.teacher_remark === opt) ? 'selected' : '';
                    remarkOptionsHtml += `<option value="${opt}" ${sel}>${opt}</option>`;
                });
                if (s.teacher_remark && !remarkOptions.includes(s.teacher_remark)) {
                    remarkOptionsHtml += `<option value="${s.teacher_remark}" selected>${s.teacher_remark}</option>`;
                }

                let interestOptionsHtml = `<option value="">Select or type interest...</option>`;
                interestOptions.forEach(opt => {
                    const sel = (s.student_interest === opt) ? 'selected' : '';
                    interestOptionsHtml += `<option value="${opt}" ${sel}>${opt}</option>`;
                });
                if (s.student_interest && !interestOptions.includes(s.student_interest)) {
                    interestOptionsHtml += `<option value="${s.student_interest}" selected>${s.student_interest}</option>`;
                }

                let attitudeOptionsHtml = ``;
                attitudeOptions.forEach(opt => {
                    const sel = (s.attitude_score === opt) ? 'selected' : '';
                    attitudeOptionsHtml += `<option value="${opt}" ${sel}>${opt}</option>`;
                });

                tbody.innerHTML += `
                    <tr id="${rowId}" data-student-id="${s.student_id}" data-overall="${s.overall_score}" data-avg="${s.avg_score}" data-rank="${s.class_rank}" data-subjects="${s.total_subjects}">
                        <td style="vertical-align: middle; text-align: center; font-weight: 600;">${idx + 1}</td>
                        <td style="vertical-align: middle;">
                            <div style="display: flex; align-items: center;">
                                <div class="avatar-initials">${s.initials}</div>
                                <div>
                                    <strong style="color: var(--text-primary); font-size: 14px;">${s.student_name}</strong>
                                    <div style="font-size: 11px; color: var(--text-muted);">ID: ${s.student_id}</div>
                                </div>
                            </div>
                        </td>
                        <td style="vertical-align: middle; text-align: center;"><span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #60a5fa; font-weight:700;">${s.overall_score.toFixed(1)}</span></td>
                        <td style="vertical-align: middle; text-align: center;"><span class="badge" style="background: rgba(168, 85, 247, 0.15); color: #c084fc; font-weight:700;">${s.avg_score.toFixed(1)}</span></td>
                        <td style="vertical-align: middle; text-align: center;"><span class="rank-badge ${rankClass}">${s.class_rank}</span></td>
                        <td style="vertical-align: middle; text-align: center;"><span class="badge" style="background: rgba(20, 184, 166, 0.15); color: #2dd4bf; font-weight:700;">${s.total_subjects}</span></td>
                        <td style="vertical-align: middle; text-align: center;">
                            <select class="form-control app-attitude-select" style="font-size: 12px; padding: 4px 8px; width: 110px;">${attitudeOptionsHtml}</select>
                        </td>
                        <td style="vertical-align: middle;">
                            <select class="form-control app-remark-select" style="font-size: 12px; min-width: 200px;" onchange="this.nextElementSibling.style.display = (this.value === 'custom') ? 'block' : 'none'">
                                ${remarkOptionsHtml}
                                <option value="custom">-- Type Custom Remark --</option>
                            </select>
                            <input type="text" class="form-control app-remark-custom mt-5" placeholder="Type custom remark..." style="display:none; font-size:12px;" value="${s.teacher_remark}">
                        </td>
                        <td style="vertical-align: middle;">
                            <select class="form-control app-interest-select" style="font-size: 12px; min-width: 180px;" onchange="this.nextElementSibling.style.display = (this.value === 'custom') ? 'block' : 'none'">
                                ${interestOptionsHtml}
                                <option value="custom">-- Type Custom Interest --</option>
                            </select>
                            <input type="text" class="form-control app-interest-custom mt-5" placeholder="Type custom interest..." style="display:none; font-size:12px;" value="${s.student_interest}">
                        </td>
                        <td style="vertical-align: middle; text-align: center;">
                            <div style="display:flex; gap:4px; justify-content:center;">
                                ${data.exam_id ? `<a href="/api/exams/reports/student/${encodeURIComponent(s.student_id)}?exam_id=${data.exam_id}${tokenQuery}" target="_blank" class="btn btn-info btn-xs" title="Preview / Print Student Report Card"><i class="fa-solid fa-file-pdf"></i> Report</a>` : ''}
                                <button type="button" class="btn btn-secondary btn-xs btn-toggle-detail" data-target="${detailRowId}">
                                    <i class="fa-solid fa-chevron-down"></i> Detail
                                </button>
                            </div>
                        </td>
                    </tr>
                `;

                let detailSubtableRows = '';
                if (s.subject_details.length === 0) {
                    detailSubtableRows = '<tr><td colspan="7" class="text-center">No subject assessment scores recorded yet.</td></tr>';
                } else {
                    s.subject_details.forEach((sd, subIdx) => {
                        detailSubtableRows += `
                            <tr>
                                <td>${subIdx + 1}</td>
                                <td><i class="fa-solid fa-book-open" style="color:#6366f1; margin-right:6px;"></i> <strong>${sd.subject_name}</strong></td>
                                <td><span class="badge" style="background:rgba(59,130,246,0.1); color:#60a5fa;">${sd.class_score.toFixed(1)}</span></td>
                                <td><span class="badge" style="background:rgba(234,179,8,0.1); color:#facc15;">${sd.exam_score.toFixed(1)}</span></td>
                                <td><strong>${sd.total_score.toFixed(1)}</strong></td>
                                <td><span class="badge badge-branch">${sd.grade}</span></td>
                                <td><span class="badge badge-academic">${sd.subject_rank}</span></td>
                            </tr>
                        `;
                    });
                }

                tbody.innerHTML += `
                    <tr id="${detailRowId}" style="display: none;">
                        <td colspan="10" style="padding: 0; border: none;">
                            <div class="detail-subtable-wrapper">
                                <h4 style="margin: 0 0 8px 0; font-size: 13px; font-weight: 700; color: var(--accent-primary);">
                                    <i class="fa-solid fa-list-check"></i> Assessment Breakdown for ${s.student_name}
                                </h4>
                                <table class="detail-subtable">
                                    <thead>
                                        <tr>
                                            <th style="width:30px;">#</th>
                                            <th>Subject Name</th>
                                            <th>Class Score (30)</th>
                                            <th>Exam Score (70)</th>
                                            <th>Total Score (100)</th>
                                            <th>Grade</th>
                                            <th>Subject Rank</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${detailSubtableRows}
                                    </tbody>
                                </table>
                            </div>
                        </td>
                    </tr>
                `;
            });

            document.querySelectorAll(".btn-toggle-detail").forEach(btn => {
                btn.addEventListener("click", () => {
                    const targetId = btn.getAttribute("data-target");
                    const targetRow = document.getElementById(targetId);
                    if (targetRow.style.display === "none") {
                        targetRow.style.display = "table-row";
                        btn.innerHTML = '<i class="fa-solid fa-chevron-up"></i> Hide Detail';
                        btn.classList.replace("btn-secondary", "btn-primary");
                    } else {
                        targetRow.style.display = "none";
                        btn.innerHTML = '<i class="fa-solid fa-chevron-down"></i> Show Detail';
                        btn.classList.replace("btn-primary", "btn-secondary");
                    }
                });
            });

            form.style.display = "block";
        })
        .catch(err => showToast(err.message, "error"));
}

function autoAssignRemarks() {
    const rows = document.querySelectorAll("#approval-table-body tr[data-student-id]");
    if (rows.length === 0) {
        showToast("Please load a class result sheet first", "error");
        return;
    }

    showToast("✨ Generating AI-Assisted Report Card Remarks...", "info");

    const promises = Array.from(rows).map(row => {
        const studentId = row.getAttribute("data-student-id");
        const remarkSelect = row.querySelector(".app-remark-select");
        const remarkCustom = row.querySelector(".app-remark-custom");
        const interestSelect = row.querySelector(".app-interest-select");
        const rank = parseInt(row.getAttribute("data-rank")) || 99;

        const roleType = (currentUser && currentUser.role === "Admin/Headteacher") ? "headteacher" : "class_teacher";

        return apiFetch("/api/academics/generate-ai-remarks", {
            method: "POST",
            body: { student_id: studentId, role_type: roleType }
        })
        .then(res => {
            if (res && res.remark) {
                if (remarkSelect) {
                    let hasOpt = false;
                    for (let opt of remarkSelect.options) {
                        if (opt.value === res.remark) {
                            remarkSelect.value = res.remark;
                            hasOpt = true;
                            break;
                        }
                    }
                    if (!hasOpt) {
                        remarkSelect.value = "custom";
                        if (remarkCustom) {
                            remarkCustom.style.display = "block";
                            remarkCustom.value = res.remark;
                        }
                    }
                }
            }

            if (interestSelect && (!interestSelect.value || interestSelect.value === "")) {
                const defaultInterests = [
                    "Mathematics & Computing",
                    "General Agricultural Science",
                    "Science & Technology",
                    "Visual & Performing Arts",
                    "Sports & Athletics",
                    "Languages & Literature"
                ];
                const interestIdx = (rank - 1) % defaultInterests.length;
                interestSelect.value = defaultInterests[interestIdx];
            }
        })
        .catch(err => console.error(`Error generating AI remark for student ${studentId}:`, err));
    });

    Promise.all(promises).then(() => {
        showToast("✨ AI-Assisted Remarks successfully generated and assigned!", "success");
    });
}

function loadPendingApprovals() {
    const activeAuthToken = localStorage.getItem("orion_token") || localStorage.getItem("token") || currentToken || "";
    const tokenQuery = activeAuthToken ? `&token=${encodeURIComponent(activeAuthToken)}` : "";

    apiFetch("/api/exams/approvals/pending")
        .then(list => {
            const tbody = document.getElementById("pending-approvals-body");
            if (!tbody) return;
            tbody.innerHTML = "";

            if (list.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="text-center p-20">No pending class result approvals.</td></tr>';
                return;
            }

            list.forEach((item, idx) => {
                let badgeClass = "badge-branch";
                if (item.status === "Pending Approval") badgeClass = "badge-academic";
                else if (item.status === "Approved") badgeClass = "badge-success";
                else if (item.status === "Rejected") badgeClass = "badge-danger";

                tbody.innerHTML += `
                    <tr>
                        <td><strong>${idx + 1}</strong></td>
                        <td><strong>${item.class_name}</strong></td>
                        <td>${item.academic_year_name}</td>
                        <td>${item.term_name}</td>
                        <td>${item.submitted_by}</td>
                        <td>${item.submitted_at}</td>
                        <td><span class="badge ${badgeClass}">${item.status}</span></td>
                        <td>
                            <div style="display:flex; gap:6px; flex-wrap:wrap;">
                                <button type="button" class="btn btn-primary btn-xs btn-inspect-approval" data-cid="${item.class_id}" data-yid="${item.academic_year_id}" data-tid="${item.term_id}" title="Inspect Sheet"><i class="fa-solid fa-eye"></i> View</button>
                                <a href="/api/exams/reports/class/${item.class_id}?exam_id=1${tokenQuery}" target="_blank" class="btn btn-info btn-xs" title="Download Whole Class Combined PDF"><i class="fa-solid fa-file-pdf"></i> Class PDF</a>
                                <a href="/api/exams/reports/class-zip/${item.class_id}?exam_id=1${tokenQuery}" target="_blank" class="btn btn-secondary btn-xs" title="Download Class ZIP Bundle"><i class="fa-solid fa-file-zipper"></i> ZIP</a>
                                ${item.status === "Pending Approval" ? `
                                    <button type="button" class="btn btn-success btn-xs btn-approve-class" data-id="${item.id}" title="Approve & Publish"><i class="fa-solid fa-circle-check"></i> Approve & Publish</button>
                                    <button type="button" class="btn btn-danger btn-xs btn-reject-class" data-id="${item.id}" title="Return for Revision"><i class="fa-solid fa-circle-xmark"></i> Reject</button>
                                ` : ''}
                            </div>
                        </td>
                    </tr>
                `;
            });

            document.querySelectorAll(".btn-inspect-approval").forEach(btn => {
                btn.addEventListener("click", () => {
                    const cid = btn.getAttribute("data-cid");
                    const yid = btn.getAttribute("data-yid");
                    const tid = btn.getAttribute("data-tid");
                    
                    const tabBtn = document.querySelector('#panel-result-approvals .tab-btn[data-tab="tab-ra-inspect-sheet"]') || document.querySelector('.tab-btn[data-tab="tab-exam-approvals"]');
                    if (tabBtn) tabBtn.click();
                    loadResultApprovalSheet(cid, yid, tid);
                });
            });

            document.querySelectorAll(".btn-approve-class").forEach(btn => {
                btn.addEventListener("click", () => {
                    const aid = btn.getAttribute("data-id");
                    if (confirm("Approve and publish results for this class? This will finalize marks for official report cards.")) {
                        apiFetch(`/api/exams/approvals/${aid}/approve`, { method: "POST" })
                            .then(res => {
                                showToast(res.message, "success");
                                loadPendingApprovals();
                            })
                            .catch(err => showToast(err.message, "error"));
                    }
                });
            });

            document.querySelectorAll(".btn-reject-class").forEach(btn => {
                btn.addEventListener("click", () => {
                    const aid = btn.getAttribute("data-id");
                    document.getElementById("reject-approval-id").value = aid;
                    document.getElementById("reject-approval-reason").value = "";
                    document.getElementById("modal-reject-approval").classList.add("show");
                });
            });
        })
        .catch(err => showToast(err.message, "error"));
}

document.getElementById("btn-load-approval-sheet")?.addEventListener("click", () => loadResultApprovalSheet());
document.getElementById("btn-auto-remarks")?.addEventListener("click", autoAssignRemarks);
document.getElementById("btn-ra-refresh-queue")?.addEventListener("click", loadPendingApprovals);

document.getElementById("approval-sheet-form")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const yid = document.getElementById("approval-year-select").value;
    const tid = document.getElementById("approval-term-select").value;
    const cid = document.getElementById("approval-class-select").value;
    
    const rows = document.querySelectorAll("#approval-table-body tr[data-student-id]");
    if (rows.length === 0) {
        showToast("No student records to submit", "error");
        return;
    }

    const remarksPayload = [];
    rows.forEach(row => {
        const studentId = row.getAttribute("data-student-id");
        const overallScore = parseFloat(row.getAttribute("data-overall")) || 0.0;
        const avgScore = parseFloat(row.getAttribute("data-avg")) || 0.0;
        const classRank = parseInt(row.getAttribute("data-rank")) || null;
        const totalSubjects = parseInt(row.getAttribute("data-subjects")) || 0;

        const remarkSelect = row.querySelector(".app-remark-select");
        const remarkCustom = row.querySelector(".app-remark-custom");
        let teacherRemark = remarkSelect ? remarkSelect.value : "";
        if (teacherRemark === "custom" && remarkCustom) {
            teacherRemark = remarkCustom.value.trim();
        }

        const interestSelect = row.querySelector(".app-interest-select");
        const interestCustom = row.querySelector(".app-interest-custom");
        let studentInterest = interestSelect ? interestSelect.value : "";
        if (studentInterest === "custom" && interestCustom) {
            studentInterest = interestCustom.value.trim();
        }

        const attitudeSelect = row.querySelector(".app-attitude-select");
        const attitudeScore = attitudeSelect ? attitudeSelect.value : "Very Good";

        remarksPayload.push({
            student_id: studentId,
            teacher_remark: teacherRemark,
            student_interest: studentInterest,
            attitude_score: attitudeScore,
            overall_score: overallScore,
            avg_score: avgScore,
            class_rank: classRank,
            total_subjects: totalSubjects
        });
    });

    apiFetch("/api/exams/approvals/submit", {
        method: "POST",
        body: {
            class_id: parseInt(cid),
            academic_year_id: parseInt(yid),
            term_id: parseInt(tid),
            remarks: remarksPayload
        }
    })
    .then(res => {
        showToast(res.message, "success");
        loadResultApprovalSheet();
        loadPendingApprovals();
    })
    .catch(err => showToast(err.message, "error"));
});

// Standalone Report Cards Interactive Search & Bulk Printing Logic
let currentRCSearchData = [];
let currentRCSearchStatus = "Draft";

function loadRCSearchResults() {
    const cid = document.getElementById("rc-search-class-select")?.value;
    const yid = document.getElementById("rc-search-year-select")?.value;
    const tid = document.getElementById("rc-search-term-select")?.value;
    const searchVal = (document.getElementById("rc-search-input")?.value || "").toLowerCase().trim();

    if (!cid || !yid || !tid) {
        showToast("Please choose Class Stream, Academic Year, and Term/Semester", "error");
        return;
    }

    const panel = document.getElementById("rc-search-results-panel");
    const tbody = document.getElementById("rc-search-results-body");
    const warning = document.getElementById("rc-search-status-warning");
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="9" class="text-center p-20"><i class="fa-solid fa-spinner fa-spin"></i> Loading student report cards...</td></tr>';
    if (panel) panel.style.display = "block";

    apiFetch(`/api/exams/approvals/sheet?class_id=${cid}&academic_year_id=${yid}&term_id=${tid}`)
        .then(data => {
            currentRCSearchData = data.students || [];
            currentRCSearchStatus = data.status || "Draft";

            if (warning) {
                if (currentRCSearchStatus !== "Approved" && currentRCSearchStatus !== "Published") {
                    warning.style.display = "block";
                    warning.innerHTML = `
                        <div style="display:flex; align-items:center; gap:12px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.35); color: #f87171; padding: 14px 18px; border-radius: var(--border-radius); margin-bottom: 15px;">
                            <i class="fa-solid fa-triangle-exclamation fa-xl" style="color: #ef4444;"></i>
                            <div>
                                <strong style="font-size:14px;">Class results not yet approved!</strong>
                                <div style="font-size:12px; color: var(--text-secondary); margin-top:2px;">Headteacher approval is required before generating or printing report cards for this class. Please go to <strong>Result Approvals</strong> to approve results.</div>
                            </div>
                        </div>
                    `;
                } else {
                    warning.style.display = "none";
                    warning.innerHTML = "";
                }
            }

            renderRCSearchResults(searchVal);
        })
        .catch(err => {
            tbody.innerHTML = `<tr><td colspan="9" class="text-center p-20 text-danger">${err.message || 'Failed to load report cards list'}</td></tr>`;
        });
}

function renderRCSearchResults(filterText = "") {
    const tbody = document.getElementById("rc-search-results-body");
    const checkAll = document.getElementById("rc-check-all-students");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (checkAll) checkAll.checked = false;

    const filtered = currentRCSearchData.filter(s => {
        if (!filterText) return true;
        const nameMatch = (s.student_name || "").toLowerCase().includes(filterText);
        const idMatch = (s.student_id || "").toLowerCase().includes(filterText);
        return nameMatch || idMatch;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center p-20">No matching student records found for this class.</td></tr>';
        updateRCSelectedCounts();
        return;
    }

    const activeAuthToken = localStorage.getItem("orion_token") || localStorage.getItem("token") || currentToken || "";
    const tokenQuery = activeAuthToken ? `&token=${encodeURIComponent(activeAuthToken)}` : "";
    const isApproved = (currentRCSearchStatus === "Approved" || currentRCSearchStatus === "Published");

    filtered.forEach((s, idx) => {
        const rankClass = s.class_rank === 1 ? "rank-1" : s.class_rank === 2 ? "rank-2" : s.class_rank === 3 ? "rank-3" : "rank-other";
        const pdfUrl = `/api/exams/reports/student/${encodeURIComponent(s.student_id)}?exam_id=1${tokenQuery}`;

        tbody.innerHTML += `
            <tr data-student-id="${s.student_id}">
                <td style="vertical-align: middle; text-align: center;">
                    <input type="checkbox" class="rc-student-checkbox" value="${s.student_id}" style="transform: scale(1.2); cursor: pointer;">
                </td>
                <td style="vertical-align: middle; text-align: center; font-weight: 600;">${idx + 1}</td>
                <td style="vertical-align: middle;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <div class="avatar-initials">${s.initials || 'ST'}</div>
                        <div>
                            <strong style="color: var(--text-primary); font-size: 14px;">${s.student_name}</strong>
                            <div style="font-size: 11px; color: var(--text-muted);">ID: ${s.student_id}</div>
                        </div>
                    </div>
                </td>
                <td style="vertical-align: middle;"><strong>${s.class_name || 'Class'}</strong></td>
                <td style="vertical-align: middle; text-align: center;"><span class="badge" style="background: rgba(59, 130, 246, 0.15); color: #60a5fa; font-weight:700;">${s.overall_score.toFixed(1)}</span></td>
                <td style="vertical-align: middle; text-align: center;"><span class="badge" style="background: rgba(168, 85, 247, 0.15); color: #c084fc; font-weight:700;">${s.avg_score.toFixed(1)}%</span></td>
                <td style="vertical-align: middle; text-align: center;"><span class="rank-badge ${rankClass}">${s.class_rank}</span></td>
                <td style="vertical-align: middle; text-align: center;"><span class="badge" style="background: rgba(20, 184, 166, 0.15); color: #2dd4bf; font-weight:700;">${s.total_subjects}</span></td>
                <td style="vertical-align: middle; text-align: center;">
                    ${isApproved ? `
                        <a href="${pdfUrl}" target="_blank" class="btn btn-success btn-xs" title="Preview / Print Student Report Card">
                            <i class="fa-solid fa-print"></i> Print Report
                        </a>
                    ` : `
                        <button type="button" class="btn btn-secondary btn-xs btn-rc-unapproved-warning" title="Class result not yet approved by headteacher">
                            <i class="fa-solid fa-lock"></i> Not Approved
                        </button>
                    `}
                </td>
            </tr>
        `;
    });

    document.querySelectorAll(".rc-student-checkbox").forEach(cb => {
        cb.addEventListener("change", updateRCSelectedCounts);
    });

    document.querySelectorAll(".btn-rc-unapproved-warning").forEach(btn => {
        btn.addEventListener("click", () => {
            showToast("Class results have not yet been approved by the headteacher. Please approve class results in Result Approvals before generating report cards.", "error");
        });
    });

    updateRCSelectedCounts();
}

function updateRCSelectedCounts() {
    const checked = document.querySelectorAll(".rc-student-checkbox:checked");
    const count = checked.length;

    const countPdf = document.getElementById("rc-selected-count-pdf");
    const countZip = document.getElementById("rc-selected-count-zip");
    const btnPdf = document.getElementById("btn-rc-download-selected-pdf");
    const btnZip = document.getElementById("btn-rc-download-selected-zip");

    if (countPdf) countPdf.innerText = count;
    if (countZip) countZip.innerText = count;
    if (btnPdf) btnPdf.disabled = (count === 0);
    if (btnZip) btnZip.disabled = (count === 0);
}

document.getElementById("btn-rc-search-submit")?.addEventListener("click", loadRCSearchResults);

document.getElementById("rc-search-input")?.addEventListener("input", (e) => {
    renderRCSearchResults(e.target.value.toLowerCase().trim());
});

document.getElementById("rc-check-all-students")?.addEventListener("change", (e) => {
    const isChecked = e.target.checked;
    document.querySelectorAll(".rc-student-checkbox").forEach(cb => {
        cb.checked = isChecked;
    });
    updateRCSelectedCounts();
});

document.getElementById("btn-rc-download-selected-pdf")?.addEventListener("click", () => {
    const cid = document.getElementById("rc-search-class-select")?.value;
    const checked = Array.from(document.querySelectorAll(".rc-student-checkbox:checked")).map(c => c.value);
    if (!cid || checked.length === 0) {
        showToast("Please select at least one student to download", "error");
        return;
    }
    if (currentRCSearchStatus !== "Approved" && currentRCSearchStatus !== "Published") {
        showToast("Class results have not yet been approved by the headteacher. Please approve class results in Result Approvals before generating report cards.", "error");
        return;
    }
    const activeAuthToken = localStorage.getItem("orion_token") || localStorage.getItem("token") || currentToken || "";
    const tokenQuery = activeAuthToken ? `&token=${encodeURIComponent(activeAuthToken)}` : "";
    window.open(`/api/exams/reports/class/${cid}?exam_id=1&student_ids=${encodeURIComponent(checked.join(','))}${tokenQuery}`, "_blank");
});

document.getElementById("btn-rc-download-selected-zip")?.addEventListener("click", () => {
    const cid = document.getElementById("rc-search-class-select")?.value;
    const checked = Array.from(document.querySelectorAll(".rc-student-checkbox:checked")).map(c => c.value);
    if (!cid || checked.length === 0) {
        showToast("Please select at least one student to download", "error");
        return;
    }
    if (currentRCSearchStatus !== "Approved" && currentRCSearchStatus !== "Published") {
        showToast("Class results have not yet been approved by the headteacher. Please approve class results in Result Approvals before generating report cards.", "error");
        return;
    }
    const activeAuthToken = localStorage.getItem("orion_token") || localStorage.getItem("token") || currentToken || "";
    const tokenQuery = activeAuthToken ? `&token=${encodeURIComponent(activeAuthToken)}` : "";
    window.open(`/api/exams/reports/class-zip/${cid}?exam_id=1&student_ids=${encodeURIComponent(checked.join(','))}${tokenQuery}`, "_blank");
});

document.getElementById("btn-rc-download-all-pdf")?.addEventListener("click", () => {
    const cid = document.getElementById("rc-search-class-select")?.value;
    if (!cid) {
        showToast("Please select a Class Stream first", "error");
        return;
    }
    if (currentRCSearchStatus !== "Approved" && currentRCSearchStatus !== "Published") {
        showToast("Class results have not yet been approved by the headteacher. Please approve class results in Result Approvals before generating report cards.", "error");
        return;
    }
    const activeAuthToken = localStorage.getItem("orion_token") || localStorage.getItem("token") || currentToken || "";
    const tokenQuery = activeAuthToken ? `&token=${encodeURIComponent(activeAuthToken)}` : "";
    window.open(`/api/exams/reports/class/${cid}?exam_id=1${tokenQuery}`, "_blank");
});

document.getElementById("btn-rc-download-all-zip")?.addEventListener("click", () => {
    const cid = document.getElementById("rc-search-class-select")?.value;
    if (!cid) {
        showToast("Please select a Class Stream first", "error");
        return;
    }
    if (currentRCSearchStatus !== "Approved" && currentRCSearchStatus !== "Published") {
        showToast("Class results have not yet been approved by the headteacher. Please approve class results in Result Approvals before generating report cards.", "error");
        return;
    }
    const activeAuthToken = localStorage.getItem("orion_token") || localStorage.getItem("token") || currentToken || "";
    const tokenQuery = activeAuthToken ? `&token=${encodeURIComponent(activeAuthToken)}` : "";
    window.open(`/api/exams/reports/class-zip/${cid}?exam_id=1${tokenQuery}`, "_blank");
});

document.getElementById("btn-rc-class-load")?.addEventListener("click", () => {
    const yid = document.getElementById("rc-class-year-select").value;
    const tid = document.getElementById("rc-class-term-select").value;
    const cid = document.getElementById("rc-class-class-select").value;

    if (!yid || !tid || !cid) {
        showToast("Please select Academic Year, Term/Semester, and Class", "error");
        return;
    }

    document.getElementById("approval-year-select").value = yid;
    document.getElementById("approval-term-select").value = tid;
    document.getElementById("approval-class-select").value = cid;

    loadResultApprovalSheet();

    const activeAuthToken = localStorage.getItem("orion_token") || localStorage.getItem("token") || currentToken || "";
    const tokenQuery = activeAuthToken ? `&token=${encodeURIComponent(activeAuthToken)}` : "";
    const pdfBtn = document.getElementById("btn-rc-class-pdf");
    const zipBtn = document.getElementById("btn-rc-class-zip");
    if (pdfBtn) {
        pdfBtn.style.display = "inline-flex";
        pdfBtn.onclick = () => window.open(`/api/exams/reports/class/${cid}?exam_id=1${tokenQuery}`, "_blank");
    }
    if (zipBtn) {
        zipBtn.style.display = "inline-flex";
        zipBtn.onclick = () => window.open(`/api/exams/reports/class-zip/${cid}?exam_id=1${tokenQuery}`, "_blank");
    }
});

document.getElementById("btn-rc-auto-assign")?.addEventListener("click", autoAssignRemarks);

document.getElementById("btn-rc-save-remarks")?.addEventListener("click", () => {
    const form = document.getElementById("approval-sheet-form");
    if (form) form.requestSubmit();
});

document.getElementById("btn-rc-refresh-approvals")?.addEventListener("click", loadPendingApprovals);

document.getElementById("form-reject-approval")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const aid = document.getElementById("reject-approval-id").value;
    const reason = document.getElementById("reject-approval-reason").value;

    apiFetch(`/api/exams/approvals/${aid}/reject`, {
        method: "POST",
        body: { reason: reason }
    })
    .then(res => {
        showToast(res.message, "success");
        document.getElementById("modal-reject-approval").classList.remove("show");
        loadPendingApprovals();
        loadResultApprovalSheet();
    })
    .catch(err => showToast(err.message, "error"));
});

// --- Fees Panel logic ---
function loadFeeTemplates() {
    apiFetch("/api/fees/templates")
        .then(templates => {
            const tbody = document.querySelector("#fee-templates-table tbody");
            tbody.innerHTML = "";
            if (templates.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" class="text-center">No fee templates defined yet. Click <strong>Add Fee Template</strong> to create one.</td></tr>';
                return;
            }
            templates.forEach(t => {
                const paidBadge = t.students_paid === t.students_billed && t.students_billed > 0
                    ? `<span class="badge badge-academic">${t.students_paid}/${t.students_billed}</span>`
                    : `<span class="badge badge-branch">${t.students_paid}/${t.students_billed}</span>`;
                
                const sysFeeBadge = t.is_system_fee 
                    ? `<span class="badge badge-info" style="margin-left:6px; background:rgba(14,165,233,0.15); color:#38bdf8; border:1px solid rgba(14,165,233,0.3);"><i class="fa-solid fa-lock"></i> System Fee</span>` 
                    : "";
                
                const isSysAdmin = currentUser && currentUser.role === "System Admin";
                const deleteBtnHtml = (t.is_system_fee && !isSysAdmin)
                    ? `<button class="btn btn-sm btn-secondary" disabled title="System Fee managed by System Admin" style="margin-left:6px; opacity:0.5; cursor:not-allowed;"><i class="fa-solid fa-lock"></i> Locked</button>`
                    : `<button class="btn btn-sm btn-danger btn-delete-fee-template" data-id="${t.id}" data-name="${t.name}" style="margin-left:6px;"><i class="fa-solid fa-trash"></i></button>`;

                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>#${t.id}</strong></td>
                    <td>${t.name}${sysFeeBadge}</td>
                    <td><strong>GHS ${t.amount.toFixed(2)}</strong></td>
                    <td><span class="badge" style="background:rgba(99,102,241,0.15); color:#818cf8;">${t.class_level}</span></td>
                    <td>${t.academic_year}</td>
                    <td>${t.term}</td>
                    <td><span class="badge badge-branch">${t.students_billed}</span></td>
                    <td>${paidBadge}</td>
                    <td>
                        <button class="btn btn-sm btn-secondary btn-apply-template" data-id="${t.id}" data-name="${t.name}" data-amount="${t.amount}">
                            <i class="fa-solid fa-bolt"></i> Bill Class
                        </button>
                        ${deleteBtnHtml}
                    </td>`;
                tbody.appendChild(tr);
            });
        })
        .catch(err => {
            const tbody = document.querySelector("#fee-templates-table tbody");
            tbody.innerHTML = `<tr><td colspan="9" class="text-center" style="color:var(--accent-danger);">Failed to load templates: ${err.message}</td></tr>`;
        });
}

function loadFinancialOverviewDashboard() {
    apiFetch("/api/fees/reports/financial")
        .then(data => {
            const billedEl = document.getElementById("fee-dash-total-billed");
            const collectedEl = document.getElementById("fee-dash-total-collected");
            const arrearsEl = document.getElementById("fee-dash-total-arrears");
            const netEl = document.getElementById("fee-dash-net-position");
            const rateEl = document.getElementById("fee-dash-collection-rate");

            const totalBilled = data.total_billed || 0;
            const totalCollected = data.total_collected || 0;
            const outstandingDebt = data.outstanding_debt || data.outstanding_arrears || 0;
            const netPos = data.net_surplus || data.net_financial_position || 0;

            if (billedEl) billedEl.innerText = `GHS ${totalBilled.toFixed(2)}`;
            if (collectedEl) collectedEl.innerText = `GHS ${totalCollected.toFixed(2)}`;
            if (arrearsEl) arrearsEl.innerText = `GHS ${outstandingDebt.toFixed(2)}`;
            if (netEl) netEl.innerText = `GHS ${netPos.toFixed(2)}`;

            const rate = totalBilled > 0 ? ((totalCollected / totalBilled) * 100).toFixed(1) : "0.0";
            if (rateEl) rateEl.innerText = `${rate}% Collected`;
        })
        .catch(err => console.error("Error loading financial overview dashboard:", err));

    apiFetch("/api/students?status=Active")
        .then(students => {
            const sel = document.getElementById("fee-dash-student-select");
            if (!sel) return;
            sel.innerHTML = '<option value="">Select or search a student to inspect fee account...</option>';
            (students || []).forEach(s => {
                const clsName = s.class_name ? ` (${s.class_name})` : '';
                sel.innerHTML += `<option value="${s.id}">[${s.id}] ${s.first_name} ${s.last_name}${clsName}</option>`;
            });
        });
}

document.getElementById("fee-dash-student-select")?.addEventListener("change", (e) => {
    const sid = e.target.value;
    const container = document.getElementById("fee-dash-student-container");
    if (!sid) {
        if (container) container.style.display = "none";
        return;
    }
    loadStudentFeeParticularsCard(sid);
});

function loadStudentFeeParticularsCard(studentId) {
    const container = document.getElementById("fee-dash-student-container");
    if (!container) return;
    container.style.display = "block";
    container.innerHTML = '<div class="text-center p-20"><i class="fa-solid fa-spinner fa-spin"></i> Fetching student fee account breakdown...</div>';

    apiFetch(`/api/fees/student/${encodeURIComponent(studentId)}/particulars`)
        .then(data => {
            const s = data.student || {};
            const arrears = data.previous_term_arrears || 0;
            const currentBill = data.current_term_bill || 0;
            const totalPaid = data.total_paid || 0;
            const balance = data.balance_due || 0;

            const activeAuthToken = localStorage.getItem("orion_token") || localStorage.getItem("token") || currentToken || "";
            const tokenQuery = activeAuthToken ? `&token=${encodeURIComponent(activeAuthToken)}` : "";

            let particularsRows = '';
            (data.particulars || []).forEach((item, idx) => {
                particularsRows += `
                    <tr>
                        <td style="text-align:center; font-weight:700;">${idx + 1}</td>
                        <td><strong>${item.name}</strong></td>
                        <td><span class="badge badge-branch">${item.category}</span></td>
                        <td style="text-align:right;"><strong>GHS ${item.amount.toFixed(2)}</strong></td>
                    </tr>
                `;
            });

            container.innerHTML = `
                <div class="glass-panel p-20" style="border: 1px dashed var(--accent-primary);">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:15px; margin-bottom:15px;">
                        <div style="display:flex; align-items:center; gap:12px;">
                            <div class="avatar-initials" style="width:50px; height:50px; font-size:18px;">${s.initials || 'ST'}</div>
                            <div>
                                <h3 style="margin:0;">${s.name || studentId}</h3>
                                <div style="font-size:12px; color:var(--text-muted);">Student ID: <strong>${s.id}</strong> | Class: <strong>${s.class_name || 'N/A'}</strong> | Guardian: <strong>${s.guardian_name || 'N/A'}</strong> (${s.guardian_phone || 'N/A'})</div>
                            </div>
                        </div>
                        <div style="display:flex; gap:10px;">
                            <button class="btn btn-success btn-sm btn-quick-pay-dash" data-student-id="${s.id}">
                                <i class="fa-solid fa-receipt"></i> Receive Payment
                            </button>
                            <a href="/api/fees/reports/financial/pdf?student_id=${s.id}${tokenQuery}" target="_blank" class="btn btn-secondary btn-sm">
                                <i class="fa-solid fa-file-pdf"></i> Financial Statement
                            </a>
                        </div>
                    </div>

                    <div class="stats-grid mb-15" style="grid-template-columns: repeat(4, 1fr); gap:12px;">
                        <div class="stat-card" style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3);">
                            <span class="stat-title" style="color: #f87171;">Previous Term Arrears</span>
                            <h3 style="color: #ef4444; margin:4px 0 0 0;">GHS ${arrears.toFixed(2)}</h3>
                        </div>
                        <div class="stat-card" style="background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.3);">
                            <span class="stat-title" style="color: #a5b4fc;">Current Term Bill</span>
                            <h3 style="color: #818cf8; margin:4px 0 0 0;">GHS ${currentBill.toFixed(2)}</h3>
                        </div>
                        <div class="stat-card" style="background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3);">
                            <span class="stat-title" style="color: #4ade80;">Total Amount Paid</span>
                            <h3 style="color: #22c55e; margin:4px 0 0 0;">GHS ${totalPaid.toFixed(2)}</h3>
                        </div>
                        <div class="stat-card" style="background: ${balance > 0 ? 'rgba(234, 179, 8, 0.1)' : 'rgba(34, 197, 94, 0.1)'}; border: 1px solid ${balance > 0 ? 'rgba(234, 179, 8, 0.3)' : 'rgba(34, 197, 94, 0.3)'};">
                            <span class="stat-title" style="color: ${balance > 0 ? '#facc15' : '#4ade80'};">Total Balance Due</span>
                            <h3 style="color: ${balance > 0 ? '#eab308' : '#22c55e'}; margin:4px 0 0 0;">GHS ${balance.toFixed(2)}</h3>
                        </div>
                    </div>

                    <h4 style="margin-top:15px; margin-bottom:10px;"><i class="fa-solid fa-list-ol"></i> Itemized Fee Structure Breakdown</h4>
                    <table class="table mb-15">
                        <thead>
                            <tr>
                                <th style="width:40px; text-align:center;">#</th>
                                <th>Fee Particulars</th>
                                <th>Category</th>
                                <th style="text-align:right;">Amount (GHS)</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${particularsRows || '<tr><td colspan="4" class="text-center">No fee items assigned yet.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            `;

            container.querySelector(".btn-quick-pay-dash")?.addEventListener("click", () => {
                const paySel = document.getElementById("payment-student-select");
                if (paySel) paySel.value = s.id;
                openModal("modal-record-payment");
                if (typeof loadStudentPaymentParticulars === "function") {
                    loadStudentPaymentParticulars(s.id);
                }
            });
        })
        .catch(err => {
            container.innerHTML = `<div class="text-center p-20 text-danger">Failed to load fee particulars: ${err.message}</div>`;
        });
}

function loadFees() {
    initTabs("panel-fees");
    loadFinancialOverviewDashboard();
    loadPlatformBill();
    loadFeeTemplates();
    loadFeesLedger();
    loadFinancialReport();

    // Billed Students List
    apiFetch("/api/fees/structures")
        .then(bills => {
             const tbody = document.querySelector("#fees-bills-table tbody");
             if (!tbody) return;
             tbody.innerHTML = "";
             if (bills.length === 0) {
                  tbody.innerHTML = '<tr><td colspan="7" class="text-center">No bills registered yet. Define a fee template and bill a class.</td></tr>';
                  return;
             }
             bills.forEach(b => {
                 const statusColor = b.status === "Paid" ? "badge-academic" : b.status === "Partially Paid" ? "badge-warning" : "badge-branch";
                 const billedAmt = (b.total_billed || 0).toFixed(2);
                 const paidAmt = (b.total_paid || 0).toFixed(2);
                 tbody.innerHTML += `
                     <tr>
                         <td><strong>${b.student_id || '—'}</strong></td>
                         <td>${b.student_name || '—'}</td>
                         <td>${b.fee_name || '—'}</td>
                         <td>${b.term_name || '—'}</td>
                         <td>GHS ${billedAmt}</td>
                         <td>GHS ${paidAmt}</td>
                         <td><span class="badge ${statusColor}">${b.status || 'Pending'}</span></td>
                     </tr>`;
             });
        });
        
    // Payments records list
    apiFetch("/api/fees/payments")
        .then(payments => {
             const tbody = document.querySelector("#fees-payments-table tbody");
             if (!tbody) return;
             tbody.innerHTML = "";
             if(payments.length === 0) {
                  tbody.innerHTML = '<tr><td colspan="8" class="text-center">No payments logged yet.</td></tr>';
                  return;
             }
             payments.forEach(p => {
                  const pAmt = (p.amount || 0).toFixed(2);
                  tbody.innerHTML += `
                      <tr>
                          <td><strong>#${p.id}</strong></td>
                          <td>${p.student_id || '—'}</td>
                          <td>${p.student_name || '—'}</td>
                          <td>GHS ${pAmt}</td>
                          <td>${p.payment_mode || 'Cash'}</td>
                          <td>${p.ref_number || "N/A"}</td>
                          <td>${p.date || '—'}</td>
                          <td><a href="/api/fees/payments/${p.id}/receipt?token=${encodeURIComponent(currentToken)}" target="_blank" class="btn btn-secondary btn-icon" title="Receipt"><i class="fa-solid fa-file-pdf"></i></a></td>
                      </tr>`;
             });
        });
        
    // Outstanding balances & Debtors list
    apiFetch("/api/fees/balances")
        .then(balances => {
             const tbody = document.querySelector("#fees-balances-table tbody");
             if (!tbody) return;
             tbody.innerHTML = "";
             if(balances.length === 0) {
                  tbody.innerHTML = '<tr><td colspan="8" class="text-center">No outstanding fee balances! All accounts clear.</td></tr>';
                  return;
             }
             balances.forEach((b, idx) => {
                  const activeAuthToken = localStorage.getItem("orion_token") || localStorage.getItem("token") || currentToken || "";
                  const tokenQuery = activeAuthToken ? `&token=${encodeURIComponent(activeAuthToken)}` : "";
                  const bBilled = (b.total_billed || 0).toFixed(2);
                  const bPaid = (b.total_paid || 0).toFixed(2);
                  const bBal = (b.balance || 0).toFixed(2);
                  tbody.innerHTML += `
                      <tr>
                          <td style="text-align:center; font-weight:700;">${idx + 1}</td>
                          <td><strong>${b.student_id || '—'}</strong></td>
                          <td><strong>${b.student_name || '—'}</strong></td>
                          <td><span class="badge" style="background:rgba(99,102,241,0.15); color:#818cf8;">${b.class_name || 'General'}</span></td>
                          <td>GHS ${bBilled}</td>
                          <td>GHS ${bPaid}</td>
                          <td style="color:#ef4444; font-weight:700;">GHS ${bBal}</td>
                          <td style="text-align:center;">
                              <button class="btn btn-success btn-xs btn-pay-debtor" data-student-id="${b.student_id}">
                                  <i class="fa-solid fa-receipt"></i> Pay Fees
                              </button>
                              <a href="/api/fees/reports/financial/pdf?student_id=${b.student_id}${tokenQuery}" target="_blank" class="btn btn-secondary btn-xs" title="Statement PDF">
                                  <i class="fa-solid fa-file-pdf"></i> Statement
                              </a>
                          </td>
                      </tr>`;
             });

             document.querySelectorAll(".btn-pay-debtor").forEach(btn => {
                 btn.addEventListener("click", (e) => {
                     const sid = e.currentTarget.dataset.studentId;
                     const paySel = document.getElementById("payment-student-select");
                     if (paySel) paySel.value = sid;
                     openModal("modal-record-payment");
                     if (typeof loadStudentPaymentParticulars === "function") {
                         loadStudentPaymentParticulars(sid);
                     }
                 });
             });
        });
}

function loadFeesLedger() {
    const filterType = document.getElementById("ledger-filter-type") ? document.getElementById("ledger-filter-type").value : "All";
    apiFetch(`/api/fees/ledger?transaction_type=${encodeURIComponent(filterType)}`)
        .then(res => {
            const summary = res.summary || {};
            document.getElementById("ledger-total-income").innerText = (summary.total_income || 0).toFixed(2);
            document.getElementById("ledger-total-expenses").innerText = (summary.total_expenses || 0).toFixed(2);
            document.getElementById("ledger-net-balance").innerText = (summary.net_balance || 0).toFixed(2);

            const tbody = document.getElementById("fees-ledger-body");
            tbody.innerHTML = "";
            const entries = res.entries || [];
            if (entries.length === 0) {
                tbody.innerHTML = '<tr><td colspan="10" class="text-center">No ledger entries found.</td></tr>';
                return;
            }
            entries.forEach((e, idx) => {
                const isIncome = e.transaction_type === "Income";
                const badgeClass = isIncome ? "badge-academic" : "badge-branch";
                const amountColor = isIncome ? "#22c55e" : "#ef4444";
                const sign = isIncome ? "+" : "-";

                tbody.innerHTML += `
                    <tr>
                        <td><strong>#${e.id}</strong></td>
                        <td>${e.date}</td>
                        <td><strong>${e.title}</strong>${e.description ? `<br><small style="color:rgba(255,255,255,0.5);">${e.description}</small>` : ''}</td>
                        <td>${e.category}</td>
                        <td><span class="badge ${badgeClass}">${e.transaction_type}</span></td>
                        <td style="color:${amountColor}; font-weight:700;">${sign} GHS ${e.amount.toFixed(2)}</td>
                        <td>${e.payment_method}</td>
                        <td>${e.reference_no || '—'}</td>
                        <td>${e.recorded_by_name}</td>
                        <td>
                            <button class="btn btn-secondary btn-icon" onclick="deleteLedgerEntry(${e.id})" title="Delete Entry"><i class="fa-solid fa-trash"></i></button>
                        </td>
                    </tr>`;
            });
        })
        .catch(err => console.error("Error loading ledger:", err));
}

function deleteLedgerEntry(entryId) {
    if (!confirm("Are you sure you want to delete this ledger transaction entry?")) return;
    apiFetch(`/api/fees/ledger/${entryId}`, { method: "DELETE" })
        .then(() => {
            showToast("Ledger entry deleted successfully", "success");
            loadFeesLedger();
            loadFinancialReport();
        })
        .catch(err => showToast(err.message, "error"));
}
window.deleteLedgerEntry = deleteLedgerEntry;

function loadFinancialReport() {
    apiFetch("/api/fees/reports/financial")
        .then(data => {
            document.getElementById("fin-total-billed").innerText = `GHS ${(data.total_billed || 0).toFixed(2)}`;
            document.getElementById("fin-total-collected").innerText = `GHS ${(data.total_collected || 0).toFixed(2)}`;
            document.getElementById("fin-outstanding-debt").innerText = `GHS ${(data.outstanding_debt || 0).toFixed(2)}`;
            document.getElementById("fin-net-position").innerText = `GHS ${(data.net_surplus || 0).toFixed(2)}`;

            const incBody = document.getElementById("fin-income-cat-body");
            incBody.innerHTML = "";
            const incCats = data.income_by_category || [];
            if (incCats.length === 0) {
                incBody.innerHTML = '<tr><td colspan="2" class="text-center">No income records</td></tr>';
            } else {
                incCats.forEach(c => {
                    incBody.innerHTML += `<tr><td>${c.category}</td><td style="font-weight:700; color:#22c55e;">GHS ${c.amount.toFixed(2)}</td></tr>`;
                });
            }

            const expBody = document.getElementById("fin-expense-cat-body");
            expBody.innerHTML = "";
            const expCats = data.expense_by_category || [];
            if (expCats.length === 0) {
                expBody.innerHTML = '<tr><td colspan="2" class="text-center">No expense records</td></tr>';
            } else {
                expCats.forEach(c => {
                    expBody.innerHTML += `<tr><td>${c.category}</td><td style="font-weight:700; color:#ef4444;">GHS ${c.amount.toFixed(2)}</td></tr>`;
                });
            }
        })
        .catch(err => console.error("Error loading financial summary:", err));
}

function openRecordLedgerModal() {
    const form = document.getElementById("form-add-ledger");
    if (form) form.reset();
    const dateInput = document.getElementById("ledger-date-input");
    if (dateInput) dateInput.value = new Date().toISOString().split("T")[0];
    openModal("modal-add-ledger");
}
window.openRecordLedgerModal = openRecordLedgerModal;

// Global Delegated Click Listener for Fee Actions & Report Downloads
document.addEventListener("click", (e) => {
    // Record Income/Expense trigger
    const addLedgerBtn = e.target.closest("#btn-add-ledger-trigger, #btn-tab-add-ledger-trigger, .btn-add-ledger-trigger");
    if (addLedgerBtn) {
        openRecordLedgerModal();
        return;
    }

    // Modal Close/Cancel button delegate
    const cancelBtn = e.target.closest(".modal-close, .btn-modal-cancel");
    if (cancelBtn) {
        const modalEl = cancelBtn.closest(".modal-backdrop, .modal");
        if (modalEl) closeModal(modalEl);
        return;
    }

    // Carry Forward Debt / Push Arrears trigger
    const pushArrearsBtn = e.target.closest("#btn-push-arrears-trigger");
    if (pushArrearsBtn) {
        Promise.all([
            apiFetch("/api/academics/years"),
            apiFetch("/api/academics/terms")
        ]).then(([years, terms]) => {
            const ySelect = document.getElementById("arrears-target-year-select");
            if (ySelect) {
                ySelect.innerHTML = "";
                years.forEach(y => {
                    ySelect.innerHTML += `<option value="${y.id}" ${y.is_current ? 'selected' : ''}>${y.name}</option>`;
                });
            }

            const tSelect = document.getElementById("arrears-target-term-select");
            if (tSelect) {
                tSelect.innerHTML = "";
                terms.forEach(t => {
                    tSelect.innerHTML += `<option value="${t.id}" ${t.is_current ? 'selected' : ''}>${t.name}</option>`;
                });
            }

            openModal("modal-push-arrears");
        }).catch(err => showToast("Failed loading academic periods", "error"));
        return;
    }

    // Refresh Ledger
    const btnRefLedger = e.target.closest("#btn-refresh-ledger");
    if (btnRefLedger) {
        loadFeesLedger();
        return;
    }

    // Download Financial Statement PDF
    const dlFinPdf = e.target.closest("#btn-download-financial-pdf");
    if (dlFinPdf) {
        window.open(`/api/fees/reports/financial/pdf?token=${encodeURIComponent(currentToken)}`, "_blank");
        return;
    }

    // Download Financial Statement Excel
    const dlFinExcel = e.target.closest("#btn-download-financial-excel");
    if (dlFinExcel) {
        window.open(`/api/fees/reports/financial/excel?token=${encodeURIComponent(currentToken)}`, "_blank");
        return;
    }

    // Download Ledger PDF
    const dlLedgerPdf = e.target.closest("#btn-download-ledger-pdf");
    if (dlLedgerPdf) {
        const type = document.getElementById("ledger-filter-type") ? document.getElementById("ledger-filter-type").value : "All";
        window.open(`/api/fees/ledger/pdf?transaction_type=${encodeURIComponent(type)}&token=${encodeURIComponent(currentToken)}`, "_blank");
        return;
    }

    // Download Ledger Excel
    const dlLedgerExcel = e.target.closest("#btn-download-ledger-excel");
    if (dlLedgerExcel) {
        const type = document.getElementById("ledger-filter-type") ? document.getElementById("ledger-filter-type").value : "All";
        window.open(`/api/fees/ledger/excel?transaction_type=${encodeURIComponent(type)}&token=${encodeURIComponent(currentToken)}`, "_blank");
        return;
    }

    // Download Balances / Debtors PDF
    const dlBalPdf = e.target.closest("#btn-download-balances-pdf");
    if (dlBalPdf) {
        window.open(`/api/fees/balances/pdf?token=${encodeURIComponent(currentToken)}`, "_blank");
        return;
    }

    // Download Balances / Debtors Excel
    const dlBalExcel = e.target.closest("#btn-download-balances-excel");
    if (dlBalExcel) {
        window.open(`/api/fees/balances/excel?token=${encodeURIComponent(currentToken)}`, "_blank");
        return;
    }
});

const selLedgerFilter = document.getElementById("ledger-filter-type");
if (selLedgerFilter) selLedgerFilter.addEventListener("change", loadFeesLedger);

const formAddLedger = document.getElementById("form-add-ledger");
if (formAddLedger) {
    formAddLedger.addEventListener("submit", (e) => {
        e.preventDefault();
        const payload = {
            title: document.getElementById("ledger-title-input").value,
            category: document.getElementById("ledger-category-input").value,
            transaction_type: document.getElementById("ledger-type-input").value,
            amount: parseFloat(document.getElementById("ledger-amount-input").value),
            payment_method: document.getElementById("ledger-method-input").value,
            reference_no: document.getElementById("ledger-ref-input").value,
            date: document.getElementById("ledger-date-input").value,
            description: document.getElementById("ledger-desc-input").value
        };

        apiFetch("/api/fees/ledger", { method: "POST", body: payload })
            .then(() => {
                showToast("Ledger transaction saved successfully!", "success");
                const modal = document.getElementById("modal-add-ledger");
                if (modal) modal.classList.remove("show");
                formAddLedger.reset();
                loadFeesLedger();
                loadFinancialReport();
            })
            .catch(err => showToast(err.message, "error"));
    });
}

const formPushArrears = document.getElementById("form-push-arrears");
if (formPushArrears) {
    formPushArrears.addEventListener("submit", (e) => {
        e.preventDefault();
        const payload = {
            target_academic_year_id: parseInt(document.getElementById("arrears-target-year-select").value),
            target_term_id: parseInt(document.getElementById("arrears-target-term-select").value)
        };

        apiFetch("/api/fees/arrears/push", { method: "POST", body: payload })
            .then(data => {
                showToast(`Carried forward GHS ${data.total_debt_pushed.toFixed(2)} debt for ${data.students_migrated} students!`, "success");
                const modal = document.getElementById("modal-push-arrears");
                if (modal) modal.classList.remove("show");
                loadFees();
            })
            .catch(err => showToast(err.message, "error"));
    });
}

// Receive Payment / Fees Collection triggers
let totalBilledParticulars = 0;

function updateDueBalance() {
    let totalPaying = 0;
    const inputs = document.querySelectorAll(".particular-pay-input");
    if (inputs.length > 0) {
        inputs.forEach(inp => {
            totalPaying += parseFloat(inp.value || "0");
        });
        const totalEl = document.getElementById("fee-total-amount");
        if (totalEl) totalEl.innerText = totalPaying.toFixed(2);
        const depInput = document.getElementById("payment-amount-input");
        if (depInput) depInput.value = totalPaying.toFixed(2);
    } else {
        totalPaying = parseFloat(document.getElementById("payment-amount-input")?.value || "0");
    }

    const due = Math.max(0, totalBilledParticulars - totalPaying);
    const dueEl = document.getElementById("fee-due-balance");
    if (dueEl) {
        dueEl.innerText = due.toFixed(2);
        dueEl.style.color = due > 0 ? "#ef4444" : "#22c55e";
    }
}

document.getElementById("payment-amount-input")?.addEventListener("input", updateDueBalance);

document.getElementById("fee-particulars-body")?.addEventListener("input", (e) => {
    if (e.target.classList.contains("particular-pay-input")) {
        updateDueBalance();
    }
});

document.getElementById("payment-student-select")?.addEventListener("change", (e) => {
    const studentId = e.target.value;
    if (!studentId) {
        document.getElementById("fee-card-reg").innerText = "—";
        document.getElementById("fee-card-name").innerText = "—";
        document.getElementById("fee-card-guardian").innerText = "—";
        document.getElementById("fee-card-class").innerText = "—";
        document.getElementById("fee-particulars-body").innerHTML = '<tr><td colspan="3" class="text-center" style="color:#94a3b8; padding: 20px;">Select a student above to display fee breakdown particulars.</td></tr>';
        document.getElementById("fee-arrears-amount").innerText = "GHS 0.00";
        document.getElementById("fee-current-amount").innerText = "GHS 0.00";
        document.getElementById("fee-total-amount").innerText = "0.00";
        document.getElementById("payment-amount-input").value = "";
        document.getElementById("fee-due-balance").innerText = "0.00";
        totalBilledParticulars = 0;
        return;
    }

    apiFetch(`/api/fees/student/${encodeURIComponent(studentId)}/particulars`)
        .then(data => {
            document.getElementById("fee-card-reg").innerText = data.registration || studentId;
            document.getElementById("fee-card-name").innerText = data.student_name || "—";
            document.getElementById("fee-card-guardian").innerText = data.guardian_name || "N/A";
            document.getElementById("fee-card-class").innerText = data.class_name || "Unassigned";

            const arrearsDue = data.arrears_due || 0;
            const currentDue = data.current_bill_due || 0;

            const arrearsEl = document.getElementById("fee-arrears-amount");
            if (arrearsEl) arrearsEl.innerText = `GHS ${arrearsDue.toFixed(2)}`;

            const currentEl = document.getElementById("fee-current-amount");
            if (currentEl) currentEl.innerText = `GHS ${currentDue.toFixed(2)}`;

            const tbody = document.getElementById("fee-particulars-body");
            tbody.innerHTML = "";

            if (!data.particulars || data.particulars.length === 0) {
                tbody.innerHTML = '<tr><td colspan="3" class="text-center" style="color:#94a3b8; padding: 20px;">No outstanding fee particulars logged for this student.</td></tr>';
                totalBilledParticulars = 0;
            } else {
                totalBilledParticulars = data.total_due || 0;
                data.particulars.forEach(p => {
                    const isArrears = p.is_arrears || (p.particular && (p.particular.toLowerCase().includes("arrears") || p.particular.toLowerCase().includes("debt brought forward")));
                    const badgeHtml = isArrears
                        ? `<span class="badge badge-danger" style="font-weight:700; font-size:11px; margin-left:8px; padding:3px 8px; border-radius:4px;"><i class="fa-solid fa-triangle-exclamation"></i> Arrears</span>`
                        : `<span class="badge badge-branch" style="font-weight:600; font-size:11px; margin-left:8px; padding:3px 8px; border-radius:4px;"><i class="fa-solid fa-file-invoice"></i> Current Bill</span>`;
                    const rowBg = isArrears 
                        ? `background: rgba(239, 68, 68, 0.12); border-left: 4px solid #ef4444; border-bottom: 1px solid rgba(239,68,68,0.2);` 
                        : `border-bottom: 1px solid rgba(255,255,255,0.08);`;

                    tbody.innerHTML += `
                        <tr style="${rowBg}">
                            <td style="text-align:center; font-weight:700; color:${isArrears ? '#fca5a5' : '#a5b4fc'}; padding: 10px;">${p.sr}</td>
                            <td style="font-weight:700; color:#f8fafc; font-size:14px; padding: 10px;">
                                ${p.particular} ${badgeHtml}
                                <div style="font-size:11px; color:${isArrears ? '#fca5a5' : '#94a3b8'}; margin-top:3px; font-weight:500;">
                                    ${isArrears ? '⚠️ Unpaid debt brought forward from previous term' : '📄 Current term fee item'} — Billed: GHS ${p.amount_billed.toFixed(2)} | Paid: GHS ${p.amount_paid.toFixed(2)}
                                </div>
                            </td>
                            <td style="text-align:right; padding: 6px 10px;">
                                <input type="number" step="0.01" min="0" max="${p.due}" 
                                       class="form-control particular-pay-input" 
                                       data-bill-id="${p.bill_id}" 
                                       value="${p.due.toFixed(2)}" 
                                       style="width: 140px; text-align: right; font-weight: 800; font-size:14px; color: ${isArrears ? '#ef4444' : '#38bdf8'}; background: rgba(15,23,42,0.9); border: 1.5px solid ${isArrears ? '#ef4444' : '#38bdf8'}; border-radius: 6px; float: right;">
                            </td>
                        </tr>`;
                });
            }

            updateDueBalance();
        })
        .catch(err => showToast("Failed to fetch student particulars: " + err.message, "error"));
});

document.getElementById("btn-record-payment-trigger")?.addEventListener("click", () => {
    // Set default month & date
    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    
    const periodInput = document.getElementById("fee-period-input");
    if (periodInput) periodInput.value = `${yyyy}-${mm}`;
    const dateInput = document.getElementById("fee-date-input");
    if (dateInput) dateInput.value = `${yyyy}-${mm}-${dd}`;

    // Reset cards and particulars
    document.getElementById("fee-card-reg").innerText = "—";
    document.getElementById("fee-card-name").innerText = "—";
    document.getElementById("fee-card-guardian").innerText = "—";
    document.getElementById("fee-card-class").innerText = "—";
    document.getElementById("fee-particulars-body").innerHTML = '<tr><td colspan="3" class="text-center" style="color:#94a3b8; padding: 20px;">Select a student above to display fee breakdown particulars.</td></tr>';
    document.getElementById("fee-total-amount").innerText = "0.00";
    document.getElementById("fee-due-balance").innerText = "0.00";
    totalBilledParticulars = 0;

    const searchInput = document.getElementById("payment-student-search-input");
    const searchResults = document.getElementById("payment-student-search-results");
    const select = document.getElementById("payment-student-select");
    if (searchInput) searchInput.value = "";
    if (select) select.value = "";
    if (searchResults) searchResults.style.display = "none";

    apiFetch("/api/students?status=Active")
        .then(students => {
             allFeeStudentsList = students || [];
             document.getElementById("modal-record-payment").classList.add("show");
             if (searchInput) setTimeout(() => searchInput.focus(), 200);
        });
});

let allFeeStudentsList = [];

function selectSearchStudent(id, fullName, className, admNo) {
    const input = document.getElementById("payment-student-search-input");
    const results = document.getElementById("payment-student-search-results");
    if (input) input.value = `${fullName} (${className} - ${admNo})`;
    if (results) results.style.display = "none";
    fetchStudentFeeParticulars(id);
}

function fetchStudentFeeParticulars(studentId) {
    if (!studentId) return;
    document.getElementById("payment-student-select").value = studentId;

    apiFetch(`/api/fees/student/${encodeURIComponent(studentId)}/particulars`)
        .then(data => {
            document.getElementById("fee-card-reg").innerText = data.registration || studentId;
            document.getElementById("fee-card-name").innerText = data.student_name || "—";
            document.getElementById("fee-card-guardian").innerText = data.guardian_name || "N/A";
            document.getElementById("fee-card-class").innerText = data.class_name || "Unassigned";

            const arrearsDue = data.arrears_due || 0;
            const currentDue = data.current_bill_due || 0;

            const arrearsEl = document.getElementById("fee-arrears-amount");
            if (arrearsEl) arrearsEl.innerText = `GHS ${arrearsDue.toFixed(2)}`;

            const currentEl = document.getElementById("fee-current-amount");
            if (currentEl) currentEl.innerText = `GHS ${currentDue.toFixed(2)}`;

            const tbody = document.getElementById("fee-particulars-body");
            tbody.innerHTML = "";

            totalBilledParticulars = 0;
            if (!data.particulars || data.particulars.length === 0) {
                tbody.innerHTML = '<tr><td colspan="3" class="text-center" style="color:#94a3b8; padding: 20px;">No outstanding fee particulars logged for this student.</td></tr>';
            } else {
                let idx = 1;
                data.particulars.forEach(item => {
                    const itemAmount = (item.due !== undefined && item.due !== null) ? item.due : (item.amount || 0);
                    const itemDesc = item.particular || item.description || "Fee Item";
                    totalBilledParticulars += itemAmount;
                    tbody.innerHTML += `
                        <tr>
                            <td class="text-center" style="font-weight:700; color:#94a3b8;">${idx++}</td>
                            <td>
                                <strong>${itemDesc}</strong>
                                <br><small style="color:#94a3b8;">${item.particular_type || 'Term Fee'} | Billed: GHS ${(item.amount_billed || 0).toFixed(2)} | Paid: GHS ${(item.amount_paid || 0).toFixed(2)}</small>
                            </td>
                            <td class="text-right">
                                <input type="number" step="0.01" min="0" max="${itemAmount}" class="form-control particular-pay-input text-right" data-bill-id="${item.bill_id}" value="${itemAmount.toFixed(2)}" style="font-weight:800; color:#818cf8; background:#0f172a;" oninput="updateDueBalance()">
                            </td>
                        </tr>
                    `;
                });
            }
            updateDueBalance();
        })
        .catch(err => showToast(parseApiDetailMessage ? parseApiDetailMessage(err, err.message || "Failed to load fee particulars") : err.message, "error"));
}

window.selectSearchStudent = selectSearchStudent;
window.fetchStudentFeeParticulars = fetchStudentFeeParticulars;

// Student Live Search Listener
document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("payment-student-search-input");
    const searchResults = document.getElementById("payment-student-search-results");
    const clearBtn = document.getElementById("btn-clear-student-search");

    if (searchInput && searchResults) {
        searchInput.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase().trim();
            if (clearBtn) clearBtn.style.display = query ? "block" : "none";

            if (!query) {
                searchResults.style.display = "none";
                searchResults.innerHTML = "";
                return;
            }

            const matches = allFeeStudentsList.filter(s => {
                const className = (s.class_name || (s.student_class ? s.student_class.name : "")).toLowerCase();
                const admNo = (s.admission_number || s.id || "").toString().toLowerCase();
                const fn = (s.first_name || "").toLowerCase();
                const ln = (s.last_name || "").toLowerCase();
                return fn.includes(query) || ln.includes(query) || admNo.includes(query) || className.includes(query);
            }).slice(0, 10);

            if (matches.length === 0) {
                searchResults.innerHTML = `<div style="padding:12px; color:#94a3b8; text-align:center;">No active students found matching "${query}"</div>`;
            } else {
                searchResults.innerHTML = matches.map(s => {
                    const fullName = `${s.first_name || ''} ${s.last_name || ''}`.trim();
                    const cls = s.class_name || (s.student_class ? s.student_class.name : "Unassigned");
                    const adm = s.admission_number || s.id;
                    const safeFull = fullName.replace(/'/g, "\\'");
                    const safeCls = cls.replace(/'/g, "\\'");
                    const safeAdm = String(adm).replace(/'/g, "\\'");
                    const safeId = String(s.id).replace(/'/g, "\\'");

                    return `
                        <div class="search-item" onclick="selectSearchStudent('${safeId}', '${safeFull}', '${safeCls}', '${safeAdm}')" style="padding:10px 15px; border-bottom:1px solid rgba(255,255,255,0.08); cursor:pointer; display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <strong style="color:#f8fafc; font-size:14px;">${fullName}</strong>
                                <div style="font-size:12px; color:#94a3b8;">Adm No: ${adm} | Parent: ${s.parent_phone || 'N/A'}</div>
                            </div>
                            <span class="badge badge-branch">${cls}</span>
                        </div>
                    `;
                }).join("");
            }
            searchResults.style.display = "block";
        });

        // Close dropdown when clicking outside
        document.addEventListener("click", (e) => {
            if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                searchResults.style.display = "none";
            }
        });
    }

    if (clearBtn) {
        clearBtn.addEventListener("click", () => {
            if (searchInput) searchInput.value = "";
            if (searchResults) searchResults.style.display = "none";
            clearBtn.style.display = "none";
        });
    }
});

document.getElementById("form-record-payment")?.addEventListener("submit", (e) => {
     e.preventDefault();
     const itemized = [];
     document.querySelectorAll(".particular-pay-input").forEach(inp => {
         const billId = parseInt(inp.getAttribute("data-bill-id"));
         const amt = parseFloat(inp.value || "0");
         if (billId && amt > 0) {
             itemized.push({ bill_id: billId, amount: amt });
         }
     });

     const payload = {
         student_id: document.getElementById("payment-student-select").value,
         amount: parseFloat(document.getElementById("payment-amount-input").value),
         payment_mode: document.getElementById("payment-mode-select").value,
         ref_number: document.getElementById("payment-ref-input").value,
         itemized_payments: itemized
     };
     
     apiFetch("/api/fees/payments", { method: "POST", body: payload })
         .then(data => {
              showToast("Fee payment recorded successfully!", "success");
              document.getElementById("modal-record-payment").classList.remove("show");
              document.getElementById("form-record-payment").reset();
              loadFees();
              if (data.payment_id) {
                  const tokenParam = currentToken ? `?token=${encodeURIComponent(currentToken)}` : '';
                  window.open(`/api/fees/payments/${data.payment_id}/receipt${tokenParam}`, "_blank");
              }
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

// --- Fee Template CRUD ---

// Open Add Fee Template modal
document.getElementById("btn-add-fee-template-trigger").addEventListener("click", () => {
    document.getElementById("form-add-fee-template").reset();
    document.getElementById("modal-add-fee-template").classList.add("show");
});

// Save new fee template
document.getElementById("form-add-fee-template").addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {
        bill_item: document.getElementById("fee-tmpl-name").value,
        amount: parseFloat(document.getElementById("fee-tmpl-amount").value),
        class_level: document.getElementById("fee-tmpl-class-level").value
    };
    // POST to structures which now creates a Fee template (no billing yet when no class_id)
    apiFetch("/api/fees/structures", { method: "POST", body: payload })
        .then(data => {
            showToast(`Fee template created! (${data.billed_students} students auto-billed if class_level matched)`, "success");
            document.getElementById("modal-add-fee-template").classList.remove("show");
            document.getElementById("form-add-fee-template").reset();
            loadFeeTemplates();
        })
        .catch(err => showToast(err.message, "error"));
});

// Fee templates table actions (delegated)
document.querySelector("#fee-templates-table tbody").addEventListener("click", (e) => {
    // Delete fee template
    const delBtn = e.target.closest(".btn-delete-fee-template");
    if (delBtn) {
        const id = delBtn.dataset.id;
        const name = delBtn.dataset.name;
        if (!confirm(`Delete fee template "${name}"? All linked student bills will also be removed.`)) return;
        apiFetch(`/api/fees/templates/${id}`, { method: "DELETE" })
            .then(() => {
                showToast(`Fee template "${name}" deleted.`, "success");
                loadFeeTemplates();
                loadFees();
            })
            .catch(err => showToast(err.message, "error"));
        return;
    }

    // Apply template → open Bill Class modal pre-filled
    const applyBtn = e.target.closest(".btn-apply-template");
    if (applyBtn) {
        apiFetch("/api/academics/classes")
            .then(classes => {
                const select = document.getElementById("bill-class-select");
                select.innerHTML = '<option value="">Select class...</option>';
                classes.forEach(c => select.innerHTML += `<option value="${c.id}">${c.name}</option>`);
                document.getElementById("bill-description-input").value = applyBtn.dataset.name;
                document.getElementById("bill-amount-input").value = applyBtn.dataset.amount;
                document.getElementById("modal-bill-class").classList.add("show");
            });
    }
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
                 tbody.innerHTML = '<tr><td colspan="8" class="text-center">No inventory assets logged.</td></tr>';
                 return;
             }
             items.forEach(i => {
                  tbody.innerHTML += `
                      <tr>
                          <td><strong>#${i.id}</strong></td>
                          <td>${i.item_name}</td>
                          <td>${i.category}</td>
                          <td><strong>${i.quantity}</strong></td>
                          <td>${i.available}</td>
                          <td>${i.unit}</td>
                          <td><span class="badge" style="background:rgba(99,102,241,0.15);color:#818cf8;">${i.condition}</span></td>
                          <td>${i.location}</td>
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
             location: document.getElementById("inv-value") ? document.getElementById("inv-value").value : ""
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
    
    // Academic Calendar (Years & Terms)
    loadAcademicCalendar();
    
    // Profiles details
    apiFetch("/api/settings/school-profile")
        .then(profile => {
             document.getElementById("set-school-name").value = profile.school_name || "";
             if (document.getElementById("set-gps-address")) {
                 document.getElementById("set-gps-address").value = profile.gps_address || "";
             }
             document.getElementById("set-school-motto").value = profile.school_motto || "";
             document.getElementById("set-school-tagline").value = profile.school_tagline || "ORION";
             document.getElementById("set-school-phone").value = profile.school_phone || "";
             document.getElementById("set-school-email").value = profile.school_email || "";
             document.getElementById("set-school-address").value = profile.school_address || "";

             if (profile.school_logo) {
                 const logoUrl = profile.school_logo.startsWith("/") ? profile.school_logo : "/" + profile.school_logo;
                 const previewImg = document.getElementById("set-logo-preview");
                 if (previewImg) {
                     previewImg.src = `${logoUrl}?v=${Date.now()}`;
                     previewImg.style.display = "inline-block";
                     previewImg.style.opacity = "1";
                 }
                 updateHeaderBranding(profile.school_name, logoUrl);
             } else {
                 const previewImg = document.getElementById("set-logo-preview");
                 if (previewImg) {
                     previewImg.src = "";
                     previewImg.style.display = "none";
                 }
                 updateHeaderBranding(profile.school_name, "");
             }
             if (profile.headteacher_signature) {
                 const sigUrl = profile.headteacher_signature.startsWith("/") ? profile.headteacher_signature : "/" + profile.headteacher_signature;
                 const sigImg = document.getElementById("set-signature-preview");
                 if (sigImg) {
                     sigImg.src = `${sigUrl}?v=${Date.now()}`;
                     sigImg.style.display = "inline-block";
                     sigImg.style.opacity = "1";
                 }
             } else {
                 const sigImg = document.getElementById("set-signature-preview");
                 if (sigImg) {
                     sigImg.src = "";
                     sigImg.style.display = "none";
                 }
             }
        });
        
    // Grading scale
    loadGradingScale();
    
    // Backups table list
    loadBackupsTable();

    // Payment gateway settings for school admins
    loadSettingsPaymentGateway();
}

function loadGradingScale() {
    apiFetch("/api/settings/grades")
        .then(grades => {
             const tbody = document.getElementById("grades-table-body");
             if (!tbody) return;
             tbody.innerHTML = "";
             
             // Sort by min_score descending
             grades.sort((a, b) => b.min_score - a.min_score);
             
             grades.forEach((g) => {
                 addGradingRow(g.grade, g.min_score, g.remark);
             });
             
             setupGradingScaleListeners();
        });
}

let gradingListenersInitialized = false;
function setupGradingScaleListeners() {
    if (gradingListenersInitialized) return;
    gradingListenersInitialized = true;
    
    const btnAdd = document.getElementById("btn-add-grading-rule");
    if (btnAdd) {
        btnAdd.addEventListener("click", () => {
            addGradingRow("", 0.0, "");
        });
    }
    
    const btnSave = document.getElementById("btn-save-grading-scale");
    if (btnSave) {
        btnSave.addEventListener("click", () => {
            saveGradingScale();
        });
    }
}

function addGradingRow(grade = "", min_score = 0.0, remark = "") {
    const tbody = document.getElementById("grades-table-body");
    if (!tbody) return;
    
    const row = document.createElement("tr");
    row.className = "grading-row";
    row.innerHTML = `
        <td class="row-index text-center" style="font-weight: 600; color: var(--text-muted); vertical-align: middle;"></td>
        <td>
            <input type="text" class="table-input grade-name-input" value="${grade}" placeholder="e.g. A1 or 1">
        </td>
        <td>
            <input type="number" step="0.1" min="0" max="100" class="table-input grade-score-input" value="${min_score}" placeholder="0.0">
        </td>
        <td>
            <input type="text" class="table-input grade-remark-input" value="${remark}" placeholder="e.g. Excellent">
        </td>
        <td style="text-align: center; vertical-align: middle;">
            <button type="button" class="btn btn-sm btn-danger btn-delete-grading-row" style="padding: 4px 8px;"><i class="fa-solid fa-trash"></i></button>
        </td>
    `;
    
    // Wire up delete event
    row.querySelector(".btn-delete-grading-row").addEventListener("click", () => {
        row.remove();
        recalculateRowIndices();
    });
    
    tbody.appendChild(row);
    recalculateRowIndices();
}

function recalculateRowIndices() {
    const tbody = document.getElementById("grades-table-body");
    if (!tbody) return;
    const rows = tbody.querySelectorAll(".grading-row");
    rows.forEach((row, idx) => {
        row.querySelector(".row-index").innerText = idx + 1;
    });
}

function saveGradingScale() {
    const tbody = document.getElementById("grades-table-body");
    if (!tbody) return;
    
    const rows = tbody.querySelectorAll(".grading-row");
    const list = [];
    let hasValidationError = false;
    
    rows.forEach((row, idx) => {
        const gradeVal = row.querySelector(".grade-name-input").value.trim();
        const scoreVal = parseFloat(row.querySelector(".grade-score-input").value);
        const remarkVal = row.querySelector(".grade-remark-input").value.trim();
        
        if (!gradeVal) {
            showToast(`Row ${idx + 1}: Grade name is required`, "error");
            hasValidationError = true;
            return;
        }
        if (isNaN(scoreVal) || scoreVal < 0 || scoreVal > 100) {
            showToast(`Row ${idx + 1}: Min Score must be between 0 and 100`, "error");
            hasValidationError = true;
            return;
        }
        
        list.push({
            grade: gradeVal,
            min_score: scoreVal,
            remark: remarkVal
        });
    });
    
    if (hasValidationError) return;
    
    // Sort by min_score descending
    list.sort((a, b) => b.min_score - a.min_score);
    
    apiFetch("/api/settings/grades", { method: "PUT", body: list })
        .then(() => {
            showToast("Grading scale configurations saved successfully", "success");
            loadGradingScale();
        })
        .catch(err => showToast(err.message, "error"));
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
        })
        .catch(err => showToast(err.message || "Failed to load backups", "error"));
}

function updateHeaderBranding(schoolName, logoUrl) {
    const brandText = document.getElementById("header-brand-text");
    const brandIcon = document.getElementById("header-brand-icon");
    const brandLogo = document.getElementById("header-school-logo");
    
    if (brandText && schoolName) {
        brandText.innerText = schoolName.toUpperCase();
    }
    if (brandLogo) {
        if (logoUrl) {
            brandLogo.src = `${logoUrl}?v=${Date.now()}`;
            brandLogo.style.display = "inline-block";
            if (brandIcon) brandIcon.style.display = "none";
        } else {
            brandLogo.style.display = "none";
            if (brandIcon) brandIcon.style.display = "inline-block";
        }
    }
}

document.getElementById("form-settings-profile")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    
    const submitBtn = e.target.querySelector("button[type='submit']");
    const originalBtnHtml = submitBtn ? submitBtn.innerHTML : "";
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Saving Profile...`;
    }

    try {
        const logoFile = document.getElementById("set-logo-file")?.files[0];
        const sigFile = document.getElementById("set-signature-file")?.files[0];

        let logoUrl = null;

        if (logoFile) {
            const formData = new FormData();
            formData.append("file", logoFile);
            const logoRes = await apiFetch("/api/settings/upload-logo", { method: "POST", body: formData });
            if (logoRes && logoRes.status === "success") {
                logoUrl = logoRes.logo_url;
                const preview = document.getElementById("set-logo-preview");
                if (preview) {
                    preview.src = `${logoUrl}?v=${Date.now()}`;
                    preview.style.display = "inline-block";
                    preview.style.opacity = "1";
                }
            }
        }

        if (sigFile) {
            const formData = new FormData();
            formData.append("file", sigFile);
            const sigRes = await apiFetch("/api/settings/upload-signature", { method: "POST", body: formData });
            if (sigRes && sigRes.status === "success") {
                const sigUrl = sigRes.signature_url;
                const preview = document.getElementById("set-signature-preview");
                if (preview) {
                    preview.src = `${sigUrl}?v=${Date.now()}`;
                    preview.style.display = "inline-block";
                    preview.style.opacity = "1";
                }
            }
        }

        const payload = {
            school_motto: document.getElementById("set-school-motto").value,
            school_tagline: document.getElementById("set-school-tagline").value,
            school_phone: document.getElementById("set-school-phone").value,
            school_email: document.getElementById("set-school-email").value,
            school_address: document.getElementById("set-school-address").value,
            gps_address: document.getElementById("set-gps-address")?.value || ""
        };

        await apiFetch("/api/settings/school-profile", { method: "PUT", body: payload });
        
        showToast("School configurations profile saved successfully!", "success");
        updateHeaderBranding(payload.school_name, logoUrl || undefined);
        loadSettings();
    } catch (err) {
        showToast(err.message || "Failed to save profile settings", "error");
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnHtml || `<i class="fa-solid fa-floppy-disk"></i> Save Profile Details`;
        }
    }
});

document.getElementById("set-logo-file")?.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);

    apiFetch("/api/settings/upload-logo", {
        method: "POST",
        body: formData
    })
    .then(data => {
        if (data && data.status === "success") {
            showToast("School logo uploaded successfully!", "success");
            const preview = document.getElementById("set-logo-preview");
            if (preview) {
                preview.src = `${data.logo_url}?v=${Date.now()}`;
                preview.style.opacity = "1";
            }
            updateHeaderBranding(document.getElementById("set-school-name").value, data.logo_url);
        } else {
            showToast((data && data.detail) || "Failed to upload logo", "error");
        }
    })
    .catch(err => showToast(err.message || "Failed to upload logo", "error"));
});

document.getElementById("set-signature-file")?.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);

    apiFetch("/api/settings/upload-signature", {
        method: "POST",
        body: formData
    })
    .then(data => {
        if (data && data.status === "success") {
            showToast("Headteacher signature uploaded successfully!", "success");
            const preview = document.getElementById("set-signature-preview");
            if (preview) {
                preview.src = `${data.signature_url}?v=${Date.now()}`;
                preview.style.opacity = "1";
            }
        } else {
            showToast((data && data.detail) || "Failed to upload signature", "error");
        }
    })
    .catch(err => showToast(err.message || "Failed to upload signature", "error"));
});

document.getElementById("btn-trigger-backup-now").addEventListener("click", () => {
     apiFetch("/api/settings/backups", { method: "POST" })
         .then(() => {
              showToast("Manual database zip backup completed", "success");
              loadBackupsTable();
         })
         .catch(err => showToast(err.message, "error"));
});

function setSysadminActiveBranch(branchId, branchName) {
    if (!branchId) {
        activeBranchIdOverride = null;
        const badge = document.getElementById("header-branch-badge");
        if (badge) badge.innerHTML = `<i class="fa-solid fa-globe"></i> Global System View`;
        showToast("Switched to Global System Overview", "info");
    } else {
        activeBranchIdOverride = parseInt(branchId);
        const badge = document.getElementById("header-branch-badge");
        if (badge) badge.innerHTML = `<i class="fa-solid fa-building-flag"></i> ${branchName || 'Branch #' + branchId}`;
        showToast(`Switched active branch context to: ${branchName || 'Branch #' + branchId}`, "success");
    }

    // Sync dropdown values
    const sysSel = document.getElementById("sys-branch-switcher");
    if (sysSel) sysSel.value = branchId ? branchId.toString() : "";
    const headSel = document.getElementById("header-branch-switcher");
    if (headSel) headSel.value = branchId ? branchId.toString() : "";
}

// Add change listeners for branch switchers
document.getElementById("sys-branch-switcher")?.addEventListener("change", (e) => {
    const bId = e.target.value;
    const bName = e.target.options[e.target.selectedIndex]?.text || '';
    setSysadminActiveBranch(bId, bName);
});

document.getElementById("header-branch-switcher")?.addEventListener("change", (e) => {
    const bId = e.target.value;
    const bName = e.target.options[e.target.selectedIndex]?.text || '';
    setSysadminActiveBranch(bId, bName);
});

// --- System Admin Panel (Global Scope) ---
function updateToggleCardState(checkboxEl) {
    const badge = checkboxEl.parentElement.querySelector(".toggle-switch-badge");
    if (!badge) return;
    if (checkboxEl.checked) {
        badge.innerText = "ENABLED";
    } else {
        badge.innerText = "DISABLED";
    }
}

document.addEventListener("change", (e) => {
    if (e.target.classList.contains("module-toggle-cb")) {
        updateToggleCardState(e.target);
    }
});

function syncDisabledModulesFromContainer(containerId, hiddenInputId) {
    const disabled = [];
    document.querySelectorAll(`#${containerId} .module-toggle-cb`).forEach(cb => {
        if (!cb.checked) {
            disabled.push(cb.value);
        }
    });
    const hidden = document.getElementById(hiddenInputId);
    if (hidden) hidden.value = disabled.join(",");
    return disabled.join(",");
}

function syncDisabledModulesToToggles(containerId, disabledStr) {
    const disabledList = (disabledStr || "").toLowerCase().split(",").map(s => s.trim());
    document.querySelectorAll(`#${containerId} .module-toggle-cb`).forEach(cb => {
        cb.checked = !disabledList.includes(cb.value.toLowerCase());
        updateToggleCardState(cb);
    });
}

function loadSysadmin() {
    initTabs("panel-sysadmin");

    // Show header branch switcher dropdown if user is System Admin
    const headSel = document.getElementById("header-branch-switcher");
    if (headSel && currentUser && currentUser.role === "System Admin") {
        headSel.style.display = "inline-block";
    }
    
    // Fetch global stats
    apiFetch("/api/sysadmin/stats")
        .then(stats => {
             window.currentSysadminStats = stats;
             const bEl = document.getElementById("sys-stat-branches");
             const sEl = document.getElementById("sys-stat-students");
             const feeEl = document.getElementById("sys-stat-fee-revenue");

             if (bEl) bEl.innerText = stats.total_branches || 0;
             if (sEl) sEl.innerText = stats.total_students || 0;
             if (feeEl) {
                 feeEl.innerText = `GHS ${(stats.total_system_fee_cost || stats.total_system_fee || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
             }

             // Populate branch dropdown switchers
             const sysSel = document.getElementById("sys-branch-switcher");
             let selectHtml = '<option value="">— System Overview (All Branches) —</option>';

             if (stats.branches && stats.branches.length > 0) {
                 stats.branches.forEach(b => {
                     selectHtml += `<option value="${b.id}">${b.name} (${b.code})</option>`;
                 });
             }

             if (sysSel) {
                 sysSel.innerHTML = selectHtml;
                 sysSel.value = activeBranchIdOverride ? activeBranchIdOverride.toString() : "";
             }
             if (headSel) {
                 headSel.innerHTML = selectHtml;
                 headSel.value = activeBranchIdOverride ? activeBranchIdOverride.toString() : "";
             }

             // Render Branches Table
             const tbody = document.querySelector("#sys-branches-table tbody");
             tbody.innerHTML = "";
             if(!stats.branches || stats.branches.length === 0) {
                  tbody.innerHTML = '<tr><td colspan="9">No branches registered.</td></tr>';
                  return;
             }
             stats.branches.forEach(b => {
                  const activeBadge = b.is_active ? '<span class="badge badge-branch">Active</span>' : '<span class="badge badge-branch" style="background:rgba(239, 68, 68, 0.1); color:#f87171; border-color:rgba(239, 68, 68, 0.2);">Suspended</span>';
                  const activeToggleText = b.is_active ? "Suspend" : "Activate";
                  const totalFeeFormatted = `GHS ${(b.total_system_fee || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

                  tbody.innerHTML += `
                      <tr>
                          <td><strong>${b.id}</strong></td>
                          <td style="font-weight:700; color:#f8fafc;">${b.name}</td>
                          <td><strong>${b.code}</strong></td>
                          <td>GHS ${(b.system_fee || 0).toFixed(2)}</td>
                          <td><span class="badge badge-branch" style="font-size:13px; font-weight:800;">${b.students}</span></td>
                          <td style="font-weight:900; color:#34d399; font-size:14px;">${totalFeeFormatted}</td>
                          <td>${b.staff}</td>
                          <td>${activeBadge}</td>
                          <td style="display:flex; gap:5px; flex-wrap:wrap;">
                              <button class="btn btn-success btn-xs btn-switch-branch" data-id="${b.id}" data-name="${b.name}"><i class="fa-solid fa-right-to-bracket"></i> Switch Branch</button>
                              <button class="btn btn-primary btn-xs btn-edit-branch" onclick="openEditBranchModal(${b.id})"><i class="fa-solid fa-pen"></i> Edit</button>
                              <button class="btn btn-secondary btn-xs btn-toggle-branch-status" data-id="${b.id}" data-active="${b.is_active}">${activeToggleText}</button>
                              ${(b.code !== 'MAIN' && b.id !== 1) ? `<button class="btn btn-danger btn-xs btn-delete-branch" onclick="deleteBranch(${b.id}, '${b.name.replace(/'/g, "\\'")}', '${b.code}')"><i class="fa-solid fa-trash"></i> Delete</button>` : ''}
                          </td>
                      </tr>`;
             });
             
             document.querySelectorAll(".btn-switch-branch").forEach(btn => {
                 btn.addEventListener("click", () => {
                     const bid = btn.getAttribute("data-id");
                     const bname = btn.getAttribute("data-name");
                     setSysadminActiveBranch(bid, bname);
                 });
             });

function openEditBranchModal(bid) {
    apiFetch("/api/sysadmin/stats")
        .then(stats => {
            window.currentSysadminStats = stats;
            const branch = (stats.branches || []).find(x => x.id == bid);
            if (!branch) {
                showToast("Branch data not found", "error");
                return;
            }
            document.getElementById("edit-branch-id").value = branch.id;
            document.getElementById("edit-branch-name").value = branch.name || "";
            document.getElementById("edit-branch-phone").value = branch.phone || "";
            document.getElementById("edit-branch-email").value = branch.email || "";
            document.getElementById("edit-branch-status").value = branch.is_active ? "true" : "false";
            document.getElementById("edit-branch-address").value = branch.address || "";
            document.getElementById("edit-branch-system-fee").value = branch.system_fee || 0;
            document.getElementById("edit-branch-notes").value = branch.notes || "";
            syncDisabledModulesToToggles("edit-branch-module-toggles", branch.disabled_modules || "");
            
            openModal("modal-edit-branch");
        })
        .catch(err => showToast("Failed to load branch details: " + err.message, "error"));
}
window.openEditBranchModal = openEditBranchModal;

             document.querySelectorAll(".btn-toggle-branch-status").forEach(btn => {
                 btn.addEventListener("click", () => {
                     const bid = btn.getAttribute("data-id");
                     const active = btn.getAttribute("data-active") === "true";
                     
                     const branch = stats.branches.find(x => x.id == bid);
                     const payload = {
                          name: branch.name,
                          address: branch.address,
                          phone: branch.phone,
                          email: branch.email,
                          system_fee: branch.system_fee || 0.0,
                          disabled_modules: branch.disabled_modules || "",
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

function deleteBranch(bid, bname, bcode) {
    if (bcode === "MAIN" || bid === 1) {
        showToast("The Primary MAIN School Branch cannot be deleted.", "error");
        return;
    }

    if (!confirm(`Are you sure you want to PERMANENTLY DELETE school branch "${bname}" (${bcode})?\n\nWARNING: This will permanently erase the branch database and all associated records!`)) {
        return;
    }

    apiFetch(`/api/sysadmin/branches/${bid}`, {
        method: "DELETE"
    })
    .then(res => {
        showToast(res.message || `Branch '${bname}' deleted successfully!`, "success");
        if (activeBranchIdOverride === bid) {
            clearSysadminBranchOverride();
        }
        loadSysadmin();
    })
    .catch(err => showToast(err.message || "Failed to delete branch", "error"));
}
window.deleteBranch = deleteBranch;
        
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

    // Defer non-critical sub-tab requests so the main Sysadmin Overview renders instantly
    setTimeout(() => {
        loadSysadminGlobalUsers();
        loadSysadminHealth();
        loadSysadminSMSGateway();
        loadSysadminPaymentGateway();
        loadSysadminAuditLogs();
        loadSysadminBroadcasts();
        loadSysadminBilling();
        loadSysadminTickets();
    }, 150);
}

function loadSysadminSMSGateway() {
    apiFetch("/api/sysadmin/sms-gateway")
        .then(gw => {
            if (!gw) return;
            const provEl = document.getElementById("sms-gw-provider");
            const senderEl = document.getElementById("sms-gw-sender-id");
            const keyEl = document.getElementById("sms-gw-api-key");
            const secretEl = document.getElementById("sms-gw-api-secret");
            const urlEl = document.getElementById("sms-gw-endpoint-url");

            if (provEl) provEl.value = gw.provider || "Arkesel";
            if (senderEl) senderEl.value = gw.sender_id || "ORION";
            if (keyEl) keyEl.value = gw.api_key || "";
            if (secretEl) secretEl.value = gw.api_secret || "";
            if (urlEl) urlEl.value = gw.endpoint_url || "";
        })
        .catch(err => console.error("Error loading SMS gateway settings:", err));
}

// --- Enterprise SysAdmin Feature Handlers ---
function loadSysadminGlobalUsers(query = "") {
    apiFetch(`/api/sysadmin/global-users?query=${encodeURIComponent(query)}`)
        .then(users => {
            const tbody = document.querySelector("#sys-global-users-table tbody");
            if (!tbody) return;
            tbody.innerHTML = "";
            if (!users || users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7">No matching users found across school databases.</td></tr>';
                return;
            }
            users.forEach(u => {
                const statusBadge = u.is_active ? '<span class="badge badge-success">Active</span>' : '<span class="badge badge-danger">Disabled</span>';
                tbody.innerHTML += `
                    <tr>
                        <td><strong>#${u.id}</strong></td>
                        <td style="font-weight:700; color:#f8fafc;">${u.username}</td>
                        <td>${u.full_name}</td>
                        <td><span class="badge badge-branch">${u.role}</span></td>
                        <td><strong>${u.branch_name}</strong></td>
                        <td>${statusBadge}</td>
                        <td>
                            <button class="btn btn-warning btn-xs" onclick="openGlobalResetPasswordModal(${u.id}, ${u.branch_id || 'null'}, '${u.username}', '${u.branch_name}', ${u.is_sysadmin})">
                                <i class="fa-solid fa-key"></i> Reset Password
                            </button>
                        </td>
                    </tr>`;
            });
        })
        .catch(err => console.error("Error loading user directory:", err));
}

function openGlobalResetPasswordModal(userId, branchId, username, branchName, isSysadmin) {
    document.getElementById("sys-reset-user-id").value = userId;
    document.getElementById("sys-reset-branch-id").value = branchId || "";
    document.getElementById("sys-reset-is-sysadmin").value = isSysadmin ? "true" : "false";
    document.getElementById("sys-reset-username-display").value = username;
    document.getElementById("sys-reset-branch-display").value = branchName;
    document.getElementById("sys-reset-new-password").value = "";
    openModal("modal-sys-reset-password");
}
window.openGlobalResetPasswordModal = openGlobalResetPasswordModal;

function loadSysadminHealth() {
    apiFetch("/api/sysadmin/system-health")
        .then(health => {
            const storageEl = document.getElementById("sys-health-total-storage");
            const freeDiskEl = document.getElementById("sys-health-free-disk");
            const serverTimeEl = document.getElementById("sys-health-server-time");

            if (storageEl) storageEl.innerText = `${health.total_storage_mb || 0} MB`;
            if (freeDiskEl) freeDiskEl.innerText = `${health.free_disk_gb || 0} GB Free of ${health.total_disk_gb || 0} GB`;
            if (serverTimeEl) serverTimeEl.innerText = health.server_time || "";

            const tbody = document.querySelector("#sys-health-files-table tbody");
            if (!tbody) return;
            tbody.innerHTML = "";
            (health.db_files || []).forEach(f => {
                tbody.innerHTML += `
                    <tr>
                        <td><strong>${f.filename}</strong></td>
                        <td>${f.name}</td>
                        <td><span class="badge badge-branch">${f.type}</span></td>
                        <td><strong style="color:#34d399;">${f.size_mb} MB</strong></td>
                    </tr>`;
            });
        });
}

function loadSysadminAuditLogs() {
    apiFetch("/api/sysadmin/audit-logs")
        .then(logs => {
            const tbody = document.querySelector("#sys-audit-table tbody");
            if (!tbody) return;
            tbody.innerHTML = "";
            if (!logs || logs.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7">No audit logs recorded yet.</td></tr>';
                return;
            }
            logs.forEach(l => {
                tbody.innerHTML += `
                    <tr>
                        <td><strong>#${l.id}</strong></td>
                        <td style="font-size:12px; color:#94a3b8;">${l.created_at}</td>
                        <td><strong>${l.admin_username}</strong></td>
                        <td><span class="badge badge-branch">${l.action_type}</span></td>
                        <td>${l.target_branch}</td>
                        <td>${l.details}</td>
                        <td><code style="font-size:11px;">${l.ip_address}</code></td>
                    </tr>`;
            });
        });
}

function loadSysadminBroadcasts() {
    apiFetch("/api/sysadmin/announcements/active")
        .then(anns => {
            const tbody = document.querySelector("#sys-broadcasts-table tbody");
            if (!tbody) return;
            tbody.innerHTML = "";
            if (!anns || anns.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6">No active broadcasts.</td></tr>';
                return;
            }
            anns.forEach(a => {
                const priorityBadge = a.priority === "Critical" ? '<span class="badge badge-danger">Critical</span>' :
                                      a.priority === "Warning" ? '<span class="badge badge-warning">Warning</span>' : '<span class="badge badge-branch">Info</span>';
                tbody.innerHTML += `
                    <tr>
                        <td><strong>#${a.id}</strong></td>
                        <td>${a.created_at}</td>
                        <td style="font-weight:700;">${a.title}</td>
                        <td>${priorityBadge}</td>
                        <td>${a.message}</td>
                        <td>${a.created_by}</td>
                    </tr>`;
            });
        });
}

function loadPlatformBill() {
    apiFetch("/api/finance/platform-bill")
        .then(bill => {
            if (!bill || bill.status === "error") return;
            const termEl = document.getElementById("platform-bill-term-name");
            const countEl = document.getElementById("platform-bill-students");
            const rateEl = document.getElementById("platform-bill-rate");
            const totalEl = document.getElementById("platform-bill-total-amount");
            const badgeEl = document.getElementById("platform-bill-status-badge");
            const payBtn = document.getElementById("btn-pay-platform-bill");

            if (termEl) termEl.innerText = `${bill.academic_year} ${bill.term_name}`;
            if (countEl) countEl.innerText = bill.student_count || 0;
            if (rateEl) rateEl.innerText = `GHS ${(bill.fee_per_student || 0).toFixed(2)}`;
            if (totalEl) totalEl.innerText = `GHS ${(bill.total_amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            
            const amtInput = document.getElementById("pay-platform-bill-amount");
            if (amtInput) amtInput.value = `GHS ${(bill.total_amount || 0).toFixed(2)}`;

            if (badgeEl) {
                if (bill.status === "Approved") {
                    badgeEl.className = "badge badge-success";
                    badgeEl.innerText = "✓ Paid & Approved";
                } else if (bill.status === "Paid") {
                    badgeEl.className = "badge badge-info";
                    badgeEl.innerText = "Pending Admin Approval";
                } else {
                    badgeEl.className = "badge badge-warning";
                    badgeEl.innerText = "Pending Payment";
                }
            }

            if (payBtn) {
                if (bill.status === "Approved") {
                    payBtn.disabled = true;
                    payBtn.innerHTML = '<i class="fa-solid fa-check"></i> Bill Settled';
                } else {
                    payBtn.disabled = false;
                    payBtn.innerHTML = '<i class="fa-solid fa-credit-card"></i> Pay Platform Bill';
                }
            }
        })
        .catch(err => console.error("Error loading platform bill:", err));
}

function openPayPlatformBillModal() {
    loadPlatformBill();
    const modal = document.getElementById("modal-pay-platform-bill");
    if (modal) modal.style.display = "flex";
}

function closePayPlatformBillModal() {
    const modal = document.getElementById("modal-pay-platform-bill");
    if (modal) modal.style.display = "none";
}

document.getElementById("form-pay-platform-bill")?.addEventListener("submit", function(e) {
    e.preventDefault();
    const refNo = document.getElementById("pay-platform-bill-ref").value.trim();
    if (!refNo) {
        if (typeof showToast === "function") showToast("Payment reference number is required", "warning");
        return;
    }

    apiFetch("/api/finance/platform-bill/pay", {
        method: "POST",
        body: JSON.stringify({ reference_no: refNo })
    })
    .then(res => {
        if (res.status === "success") {
            if (typeof showToast === "function") showToast("Platform bill payment submitted! Expense entry logged automatically.", "success");
            closePayPlatformBillModal();
            loadPlatformBill();
            if (typeof loadFeesLedger === "function") loadFeesLedger();
            if (typeof loadFinancialOverviewDashboard === "function") loadFinancialOverviewDashboard();
        } else {
            if (typeof showToast === "function") showToast(res.message || "Failed to process payment", "error");
        }
    })
    .catch(err => {
        if (typeof showToast === "function") showToast(err.message || "Error submitting payment", "error");
    });
});

function loadSysadminBilling() {
    apiFetch("/api/sysadmin/billing")
        .then(bills => {
            const tbody = document.querySelector("#sys-billing-table tbody");
            if (!tbody) return;
            tbody.innerHTML = "";
            if (!bills || bills.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9">No platform billing records found.</td></tr>';
                return;
            }
            bills.forEach(bill => {
                const statusBadge = bill.status === "Approved" ? '<span class="badge badge-success">✓ Approved</span>' :
                                      bill.status === "Paid" ? '<span class="badge badge-info">Paid (Pending Approval)</span>' :
                                      '<span class="badge badge-warning">Pending Payment</span>';
                
                const actionBtn = bill.status === "Approved" ? '<span style="color:#34d399; font-size:12px; font-weight:700;">✓ Approved</span>' :
                    `<button class="btn btn-sm btn-success" onclick="approvePlatformBill(${bill.id})"><i class="fa-solid fa-check"></i> Approve Payment</button>`;

                tbody.innerHTML += `
                    <tr>
                        <td><strong>#${bill.id}</strong></td>
                        <td style="font-weight:700; color:#f8fafc;">${bill.branch_name}</td>
                        <td>${bill.academic_year} ${bill.term_name}</td>
                        <td><span class="badge badge-branch">${bill.student_count}</span></td>
                        <td>GHS ${(bill.fee_per_student || 0).toFixed(2)}</td>
                        <td><strong style="color:#34d399; font-size:15px;">GHS ${(bill.total_amount || 0).toFixed(2)}</strong></td>
                        <td>${statusBadge}</td>
                        <td><code>${bill.reference_no || '—'}</code></td>
                        <td>${actionBtn}</td>
                    </tr>`;
            });
        })
        .catch(err => console.error("Error loading sysadmin billing:", err));
}

function approvePlatformBill(billId) {
    if (!confirm("Approve this platform bill payment? This will update the bill status and automatically log an Expense record in the branch ledger.")) return;

    apiFetch(`/api/sysadmin/billing/${billId}/approve`, {
        method: "POST"
    })
    .then(res => {
        if (res.status === "success") {
            if (typeof showToast === "function") showToast("Platform bill payment approved and recorded as expense in branch!", "success");
            loadSysadminBilling();
        } else {
            if (typeof showToast === "function") showToast(res.message || "Failed to approve bill", "error");
        }
    })
    .catch(err => {
        if (typeof showToast === "function") showToast(err.message || "Error approving bill", "error");
    });
}

// Global User Search Trigger
document.getElementById("btn-sys-search-users")?.addEventListener("click", () => {
    const q = document.getElementById("sys-user-search-input")?.value || "";
    loadSysadminGlobalUsers(q);
});

document.getElementById("sys-user-search-input")?.addEventListener("keyup", (e) => {
    if (e.key === "Enter") {
        loadSysadminGlobalUsers(e.target.value);
    }
});

// Password Reset Form Submit
document.getElementById("form-sys-reset-password")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const userId = parseInt(document.getElementById("sys-reset-user-id").value);
    const branchIdVal = document.getElementById("sys-reset-branch-id").value;
    const isSysadmin = document.getElementById("sys-reset-is-sysadmin").value === "true";
    const newPassword = document.getElementById("sys-reset-new-password").value;

    const payload = {
        user_id: userId,
        branch_id: branchIdVal ? parseInt(branchIdVal) : null,
        new_password: newPassword,
        is_sysadmin: isSysadmin
    };

    apiFetch("/api/sysadmin/reset-user-password", { method: "POST", body: payload })
        .then(res => {
            showToast(res.message || "Password updated successfully!", "success");
            closeModal("modal-sys-reset-password");
            loadSysadminGlobalUsers(document.getElementById("sys-user-search-input")?.value || "");
        })
        .catch(err => showToast(err.message, "error"));
});

// Export Global ZIP Backup
document.getElementById("btn-sys-export-backup")?.addEventListener("click", () => {
    const token = localStorage.getItem("orion_token") || currentToken;
    showToast("Generating global system backup archive...", "info");
    fetch("/api/sysadmin/backups/global-export", {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) throw new Error("Export backup failed");
        return response.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `orion_global_backup_${new Date().toISOString().slice(0,10)}.zip`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        showToast("Global system backup downloaded successfully!", "success");
    })
    .catch(err => showToast(err.message, "error"));
});

// Broadcast Announcement Trigger
document.getElementById("btn-sys-send-broadcast")?.addEventListener("click", () => {
    const title = document.getElementById("sys-broadcast-title")?.value;
    const message = document.getElementById("sys-broadcast-message")?.value;
    const priority = document.getElementById("sys-broadcast-priority")?.value;

    if (!title || !message) {
        showToast("Please provide both announcement title and message content", "error");
        return;
    }

    const payload = { title, message, priority, target_branch_id: null };

    apiFetch("/api/sysadmin/announcements/broadcast", { method: "POST", body: payload })
        .then(res => {
            showToast("Global announcement broadcasted to all branches!", "success");
            document.getElementById("sys-broadcast-title").value = "";
            document.getElementById("sys-broadcast-message").value = "";
            loadSysadminBroadcasts();
        })
        .catch(err => showToast(err.message, "error"));
});

// SMS Gateway Config Save Handler
document.getElementById("form-sys-sms-gateway")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {
        provider: document.getElementById("sms-gw-provider")?.value || "Arkesel",
        sender_id: document.getElementById("sms-gw-sender-id")?.value || "ORION",
        api_key: document.getElementById("sms-gw-api-key")?.value || "",
        api_secret: document.getElementById("sms-gw-api-secret")?.value || "",
        endpoint_url: document.getElementById("sms-gw-endpoint-url")?.value || ""
    };

    apiFetch("/api/sysadmin/sms-gateway", { method: "POST", body: payload })
        .then(res => {
            showToast(res.message || "SMS Gateway settings saved!", "success");
            loadSysadminSMSGateway();
        })
        .catch(err => showToast(err.message, "error"));
});

// Test SMS Dispatch Handler
document.getElementById("btn-sys-test-sms")?.addEventListener("click", () => {
    const phone = document.getElementById("sys-sms-test-phone")?.value;
    if (!phone) {
        showToast("Please enter a test phone number", "error");
        return;
    }

    showToast("Dispatching test SMS...", "info");
    apiFetch("/api/sysadmin/sms-gateway/test", { method: "POST", body: { test_phone: phone } })
        .then(res => {
            if (res.status === "success") {
                showToast(res.message, "success");
            } else {
                showToast("Test SMS Result: " + res.message, "warning");
            }
        })
        .catch(err => showToast("Test SMS failed: " + err.message, "error"));
});

function loadSysadminPaymentGateway() {
    apiFetch("/api/sysadmin/payment-gateway")
        .then(gw => {
            if (!gw) return;
            const provEl = document.getElementById("pay-gw-provider");
            const pubEl = document.getElementById("pay-gw-public-key");
            const secEl = document.getElementById("pay-gw-secret-key");
            const merEl = document.getElementById("pay-gw-merchant-id");

            if (provEl) provEl.value = gw.provider || "Paystack";
            if (pubEl) pubEl.value = gw.public_key || "";
            if (secEl) secEl.value = gw.secret_key || "";
            if (merEl) merEl.value = gw.merchant_id || "";
        })
        .catch(err => console.error("Error loading Payment gateway settings:", err));
}

// Payment Gateway Config Save Handler
document.getElementById("form-sys-pay-gateway")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {
        provider: document.getElementById("pay-gw-provider")?.value || "Paystack",
        public_key: document.getElementById("pay-gw-public-key")?.value || "",
        secret_key: document.getElementById("pay-gw-secret-key")?.value || "",
        merchant_id: document.getElementById("pay-gw-merchant-id")?.value || ""
    };

    apiFetch("/api/sysadmin/payment-gateway", { method: "POST", body: payload })
        .then(res => {
            showToast(res.message || "Payment Gateway settings saved!", "success");
            loadSysadminPaymentGateway();
        })
        .catch(err => showToast(err.message, "error"));
});

// --- Settings Panel Payment Gateway (for school admins: Super Admin / Admin/Headteacher) ---
function loadSettingsPaymentGateway() {
    apiFetch("/api/sysadmin/payment-gateway")
        .then(gw => {
            if (!gw) return;
            const provEl  = document.getElementById("set-pay-gw-provider");
            const pubEl   = document.getElementById("set-pay-gw-public-key");
            const secEl   = document.getElementById("set-pay-gw-secret-key");
            const merEl   = document.getElementById("set-pay-gw-merchant-id");
            const hookEl  = document.getElementById("set-pay-gw-webhook-url");

            if (provEl) provEl.value = gw.provider || "Paystack";
            if (pubEl)  pubEl.value  = gw.public_key || "";
            if (secEl)  secEl.value  = gw.secret_key || "";
            if (merEl)  merEl.value  = gw.merchant_id || "";
            if (hookEl) hookEl.value = `${window.location.origin}/api/payments/webhook/${(gw.provider || "paystack").toLowerCase()}`;
        })
        .catch(err => console.warn("Payment gateway not accessible for this role:", err.message));
}

document.getElementById("form-settings-pay-gateway")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {
        provider:    document.getElementById("set-pay-gw-provider")?.value  || "Paystack",
        public_key:  document.getElementById("set-pay-gw-public-key")?.value  || "",
        secret_key:  document.getElementById("set-pay-gw-secret-key")?.value  || "",
        merchant_id: document.getElementById("set-pay-gw-merchant-id")?.value || ""
    };

    apiFetch("/api/sysadmin/payment-gateway", { method: "POST", body: payload })
        .then(res => {
            showToast(res.message || "Payment Gateway credentials saved successfully!", "success");
            loadSettingsPaymentGateway();
        })
        .catch(err => showToast("Failed to save gateway settings: " + err.message, "error"));
});

// --- Redesigned Parent & Student Self-Service Portal Handlers ---
function switchParentPortalTab(tabId) {
    switchPanel("panel-parent-portal");

    const parentPanel = document.getElementById("panel-parent-portal");
    if (!parentPanel) return;

    // Activate corresponding tab button & tab content
    parentPanel.querySelectorAll(".tab-btn").forEach(btn => {
        if (btn.getAttribute("data-tab") === tabId) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    parentPanel.querySelectorAll(".tab-content").forEach(content => {
        if (content.id === tabId) {
            content.classList.add("active");
        } else {
            content.classList.remove("active");
        }
    });

    // Update parent sidebar active link highlight
    document.querySelectorAll("#sidebar-parent-menu .nav-link").forEach(link => {
        const onclickAttr = link.getAttribute("onclick") || "";
        if (onclickAttr.includes(tabId)) {
            link.classList.add("active");
        } else {
            link.classList.remove("active");
        }
    });
}

function switchParentChild(studentId) {
    if (studentId) {
        loadParentPortalData(studentId);
    }
}

function loadParentPortalData(studentId) {
    const ppPanel = document.getElementById("panel-parent-portal");
    const contentContainer = document.querySelector(".content-container");
    if (contentContainer) contentContainer.scrollTop = 0;

    if (typeof initTabs === "function") {
        initTabs("panel-parent-portal");
    }

    const isSysAdmin = currentUser && currentUser.role === "System Admin";
    const isAdmin = currentUser && (currentUser.role === "Admin/Headteacher" || currentUser.role === "Super Admin" || isSysAdmin);
    const isParent = currentUser && currentUser.role === "Parent";
    
    const adminBar = document.getElementById("parent-admin-selector-bar");
    const adminSel = document.getElementById("parent-admin-student-select");
    const branchRow = document.getElementById("parent-admin-branch-row");
    const branchSel = document.getElementById("parent-admin-branch-select");
    const barTitle = document.getElementById("parent-admin-bar-title");
    const childSelect = document.getElementById("parent-child-select");
    const childSwitcherWrap = document.getElementById("parent-child-switcher-container");

    // Admin Inspector Mode Setup
    if (isAdmin && adminBar) {
        adminBar.style.display = "block";
        if (barTitle) {
            barTitle.innerText = isSysAdmin
                ? "System Admin — Parent Portal Inspector (All Branches)"
                : "Headteacher / Admin — Parent Portal Inspector";
        }
        if (isSysAdmin && branchRow) {
            branchRow.style.display = "flex";
            if (branchSel && (!branchSel.dataset.loaded || branchSel.options.length <= 1)) {
                apiFetch("/api/sysadmin/branches")
                    .then(branches => {
                        branchSel.dataset.loaded = "true";
                        branchSel.innerHTML = `<option value="">— Select Branch —</option>` +
                            branches.map(b => `<option value="${b.id}">${b.name} (${b.code})</option>`).join("");
                        if (!branchSel.dataset.bound) {
                            branchSel.dataset.bound = "true";
                            branchSel.addEventListener("change", (e) => {
                                if (e.target.value) {
                                    activeBranchIdOverride = parseInt(e.target.value);
                                    if (adminSel) {
                                        adminSel.innerHTML = `<option value="">— Select Student to Inspect —</option>`;
                                        delete adminSel.dataset.loaded;
                                    }
                                    loadParentPortalData();
                                }
                            });
                        }
                    })
                    .catch(err => console.error("Error loading branches for sysadmin inspector:", err));
            }
        } else if (branchRow) {
            branchRow.style.display = "none";
        }

        if (adminSel && (!adminSel.dataset.loaded || adminSel.options.length <= 1)) {
            if (isSysAdmin && !activeBranchIdOverride) {
                adminSel.innerHTML = `<option value="">— Select a branch first —</option>`;
            } else {
                apiFetch("/api/students")
                    .then(students => {
                        adminSel.dataset.loaded = "true";
                        adminSel.innerHTML = `<option value="">— Select Student to Inspect —</option>` + students.map(s => `
                            <option value="${s.id}" ${studentId === s.id ? 'selected' : ''}>
                                ${s.first_name} ${s.last_name} (${s.id} - ${s.class_name || 'Unassigned'})
                            </option>
                        `).join("");
                        if (!adminSel.dataset.bound) {
                            adminSel.dataset.bound = "true";
                            adminSel.addEventListener("change", (e) => {
                                if (e.target.value) {
                                    loadParentPortalData(e.target.value);
                                }
                            });
                        }
                    })
                    .catch(err => console.error("Error loading students for parent inspector:", err));
            }
        }
    } else if (adminBar) {
        adminBar.style.display = "none";
    }

    // Populate Parent Child Switcher
    if (isParent && childSelect) {
        if (childSwitcherWrap) childSwitcherWrap.style.display = "flex";
        if (!childSelect.dataset.loaded) {
            apiFetch("/api/parent/children")
                .then(children => {
                    childSelect.dataset.loaded = "true";
                    if (children && children.length > 0) {
                        childSelect.innerHTML = children.map(c => `
                            <option value="${c.id}" ${studentId === c.id || (!studentId && c.id === children[0].id) ? 'selected' : ''}>
                                ${c.full_name} (${c.class_name || 'Class'})
                            </option>
                        `).join("");
                    } else {
                        childSelect.innerHTML = `<option value="">No linked children</option>`;
                    }
                })
                .catch(err => console.error("Error fetching parent children:", err));
        }
    } else if (childSwitcherWrap && !isAdmin) {
        childSwitcherWrap.style.display = "none";
    }

    if (!studentId && currentUser) studentId = currentUser.student_id || null;
    if (!studentId || studentId === "me") {
        if (isAdmin && adminSel && adminSel.value) {
            studentId = adminSel.value;
        } else if (isAdmin) {
            const nameEl = document.getElementById("parent-student-name");
            const metaEl = document.getElementById("parent-student-meta");
            if (nameEl) nameEl.innerHTML = `<i class="fa-solid fa-user-magnifying-glass" style="color:var(--accent-primary);"></i> Parent Portal Inspector`;
            if (metaEl) metaEl.innerText = isSysAdmin
                ? "Select a branch, then choose a student to inspect their portal."
                : "Select a student from the dropdown above to inspect their profile, fees, attendance, and results.";
            ["parent-kpi-balance","parent-kpi-attendance","parent-kpi-reports","parent-kpi-notices"].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.innerText = "—";
            });
            return;
        } else {
            studentId = "me";
        }
    }

    apiFetch(`/api/parent/student-overview/${studentId}`)
        .then(data => {
            if (!data || !data.student) return;
            window.currentParentOverview = data;

            // Student Meta Header
            const nameEl = document.getElementById("parent-student-name");
            const metaEl = document.getElementById("parent-student-meta");
            const branchTag = document.getElementById("parent-branch-tag");

            if (nameEl) nameEl.innerHTML = `<i class="fa-solid fa-graduation-cap" style="color:var(--accent-primary);"></i> ${data.student.full_name || 'Student Portal'}`;
            if (metaEl) metaEl.innerText = `Class: ${data.student.class_name || 'Unassigned'} | Admission No: ${data.student.admission_number || data.student.id} | Parent: ${data.student.parent_name || 'N/A'}`;
            if (branchTag && currentUser) branchTag.innerText = currentUser.branch_name || "Main Campus";

            // KPI Cards
            const balEl = document.getElementById("parent-kpi-balance");
            const attEl = document.getElementById("parent-kpi-attendance");
            const repEl = document.getElementById("parent-kpi-reports");
            const notEl = document.getElementById("parent-kpi-notices");

            const bal = (data.financials && data.financials.balance_due) ? data.financials.balance_due : 0;
            if (balEl) {
                balEl.innerText = `GHS ${bal.toFixed(2)}`;
                balEl.style.color = bal > 0 ? '#f87171' : '#34d399';
            }
            if (attEl && data.attendance_behavior) attEl.innerText = `${data.attendance_behavior.attendance_rate || 100}%`;
            if (repEl && data.academic && data.academic.reports) repEl.innerText = `${data.academic.reports.length} Terms`;
            
            const msgCount = (data.communication && data.communication.messages) ? data.communication.messages.length : 0;
            const annCount = (data.communication && data.communication.announcements) ? data.communication.announcements.length : 0;
            if (notEl) notEl.innerText = `${msgCount + annCount} Active`;

            // TAB 1: ACADEMIC MONITORING
            // Published Reports
            const repContainer = document.getElementById("parent-reports-container");
            if (repContainer && data.academic && data.academic.reports) {
                if (data.academic.reports.length === 0) {
                    repContainer.innerHTML = `<div class="glass-panel" style="padding:20px; text-align:center; color:#94a3b8; grid-column:span 2;">
                        <i class="fa-solid fa-lock" style="font-size:32px; margin-bottom:10px;"></i><br>
                        No approved report cards have been published by the Headteacher for this term yet.
                    </div>`;
                } else {
                    repContainer.innerHTML = data.academic.reports.map(r => `
                        <div class="glass-panel" style="padding:15px; border-left:4px solid var(--accent-primary);">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                                <h4 style="margin:0;"><i class="fa-solid fa-scroll"></i> ${r.year_name} - ${r.term_name}</h4>
                                <span class="badge badge-success"><i class="fa-solid fa-check-circle"></i> Published</span>
                            </div>
                            <p style="font-size:13px; color:#94a3b8; margin-bottom:8px;">
                                <strong>Academic Average:</strong> <span style="color:#60a5fa; font-weight:700;">${r.average_score}%</span> | 
                                <strong>Subjects Graded:</strong> ${r.subject_count}
                            </p>
                            <p style="font-size:12px; font-style:italic; color:#cbd5e1; margin-bottom:12px;">
                                "${r.headteacher_remark}"
                            </p>
                            <button class="btn btn-sm btn-primary" onclick="openReportCardModal('${data.student.id}', ${r.year_id}, ${r.term_id})" style="font-weight:700;">
                                <i class="fa-solid fa-file-pdf"></i> View / Download Report Card PDF
                            </button>
                        </div>
                    `).join("");
                }
            }

            // Subject Grades Table
            const gradesTable = document.querySelector("#parent-grades-table tbody");
            if (gradesTable && data.academic && data.academic.recent_grades) {
                if (data.academic.recent_grades.length === 0) {
                    gradesTable.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#94a3b8;">No subject grade entries found.</td></tr>`;
                } else {
                    gradesTable.innerHTML = data.academic.recent_grades.map(g => `
                        <tr>
                            <td><strong>${g.subject_name}</strong></td>
                            <td>${(g.class_score || 0).toFixed(1)}</td>
                            <td>${(g.exam_score || 0).toFixed(1)}</td>
                            <td style="color:#60a5fa; font-weight:700;">${(g.total_score || 0).toFixed(1)}</td>
                            <td><span class="badge badge-branch">${g.grade}</span></td>
                        </tr>
                    `).join("");
                }
            }

            // Timetable Table
            const timeTable = document.querySelector("#parent-timetable-table tbody");
            if (timeTable && data.academic && data.academic.timetable) {
                if (data.academic.timetable.length === 0) {
                    timeTable.innerHTML = `<tr><td colspan="4" style="text-align:center; color:#94a3b8;">No timetable slots defined for this class.</td></tr>`;
                } else {
                    timeTable.innerHTML = data.academic.timetable.map(t => `
                        <tr>
                            <td><strong>${t.day_of_week}</strong></td>
                            <td>${t.start_time} - ${t.end_time}</td>
                            <td><span class="badge badge-branch">${t.subject_name}</span></td>
                            <td>${t.teacher_name}</td>
                        </tr>
                    `).join("");
                }
            }

            // Exam Schedule Table
            const examTable = document.querySelector("#parent-exams-table tbody");
            if (examTable && data.academic && data.academic.exam_schedules) {
                if (data.academic.exam_schedules.length === 0) {
                    examTable.innerHTML = `<tr><td colspan="3" style="text-align:center; color:#94a3b8;">No upcoming examinations scheduled.</td></tr>`;
                } else {
                    examTable.innerHTML = data.academic.exam_schedules.map(e => `
                        <tr>
                            <td><strong>${e.name}</strong></td>
                            <td>${e.academic_year} (${e.term})</td>
                            <td><span class="badge badge-warning">${e.start_date || 'TBD'} to ${e.end_date || 'TBD'}</span></td>
                        </tr>
                    `).join("");
                }
            }

            // TAB 2: ATTENDANCE & BEHAVIOR
            const attPres = document.getElementById("parent-att-present");
            const attAbs = document.getElementById("parent-att-absent");
            const attLate = document.getElementById("parent-att-late");
            if (attPres && data.attendance_behavior) attPres.innerText = `${data.attendance_behavior.present || 0} Days`;
            if (attAbs && data.attendance_behavior) attAbs.innerText = `${data.attendance_behavior.absent || 0} Days`;
            if (attLate && data.attendance_behavior) attLate.innerText = `${data.attendance_behavior.late || 0} Days`;

            const attLogTable = document.querySelector("#parent-attendance-log-table tbody");
            if (attLogTable && data.attendance_behavior && data.attendance_behavior.logs) {
                if (data.attendance_behavior.logs.length === 0) {
                    attLogTable.innerHTML = `<tr><td colspan="3" style="text-align:center; color:#94a3b8;">No daily attendance records.</td></tr>`;
                } else {
                    attLogTable.innerHTML = data.attendance_behavior.logs.map(l => `
                        <tr>
                            <td>${l.date}</td>
                            <td>
                                <span class="badge ${l.status === 'Present' ? 'badge-success' : l.status === 'Late' ? 'badge-warning' : 'badge-danger'}">
                                    ${l.status}
                                </span>
                            </td>
                            <td>${l.remarks}</td>
                        </tr>
                    `).join("");
                }
            }

            const behaviorContainer = document.getElementById("parent-behavior-container");
            if (behaviorContainer && data.attendance_behavior && data.attendance_behavior.behavior_reports) {
                if (data.attendance_behavior.behavior_reports.length === 0) {
                    behaviorContainer.innerHTML = `<div class="glass-panel" style="padding:14px; color:#94a3b8;">No behavior or disciplinary reports logged for this student.</div>`;
                } else {
                    behaviorContainer.innerHTML = data.attendance_behavior.behavior_reports.map(b => `
                        <div class="glass-panel" style="padding:12px; border-left:4px solid ${b.incident_type === 'Positive Feedback' ? '#10b981' : '#f59e0b'};">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <strong style="font-size:13px; color:#ffffff;">${b.title}</strong>
                                <span class="badge ${b.incident_type === 'Positive Feedback' ? 'badge-success' : 'badge-warning'}">${b.incident_type}</span>
                            </div>
                            <p style="font-size:12px; color:#cbd5e1; margin:6px 0;">${b.description}</p>
                            <div style="display:flex; justify-content:space-between; font-size:11px; color:#94a3b8;">
                                <span>Action: ${b.action_taken}</span>
                                <span>${b.date} | ${b.reported_by_name}</span>
                            </div>
                        </div>
                    `).join("");
                }
            }

            // TAB 3: COMMUNICATION & PTA
            const annContainer = document.getElementById("parent-announcements-container");
            if (annContainer && data.communication && data.communication.announcements) {
                if (data.communication.announcements.length === 0) {
                    annContainer.innerHTML = `<div class="glass-panel" style="padding:14px; color:#94a3b8;">No announcements active.</div>`;
                } else {
                    annContainer.innerHTML = data.communication.announcements.map(a => `
                        <div class="glass-panel" style="padding:12px; border-left:4px solid #38bdf8;">
                            <strong style="font-size:13px; color:#38bdf8;">${a.title}</strong>
                            <p style="font-size:12px; color:#e2e8f0; margin:6px 0;">${a.content}</p>
                            <span style="font-size:11px; color:#94a3b8;"><i class="fa-solid fa-clock"></i> ${a.date}</span>
                        </div>
                    `).join("");
                }
            }

            const msgContainer = document.getElementById("parent-messages-container");
            if (msgContainer && data.communication && data.communication.messages) {
                if (data.communication.messages.length === 0) {
                    msgContainer.innerHTML = `<div class="glass-panel" style="padding:14px; color:#94a3b8;">No direct messages sent yet. Click "Message Teacher / Headmaster" above to start a conversation.</div>`;
                } else {
                    msgContainer.innerHTML = data.communication.messages.map(m => `
                        <div class="glass-panel" style="padding:12px; border-left:4px solid #a78bfa;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <strong style="font-size:13px; color:#a78bfa;">${m.subject}</strong>
                                <span class="badge badge-branch">${m.recipient_role}</span>
                            </div>
                            <p style="font-size:12px; color:#e2e8f0; margin:6px 0;"><strong>Parent:</strong> ${m.message}</p>
                            ${m.reply ? `<p style="font-size:12px; color:#34d399; margin:4px 0 0 0; background:rgba(52,211,153,0.1); padding:8px; border-radius:6px;"><strong>School Reply:</strong> ${m.reply}</p>` : `<span style="font-size:11px; color:#fbbf24;">Awaiting response from school staff</span>`}
                        </div>
                    `).join("");
                }
            }

            const ptaTable = document.querySelector("#parent-pta-table tbody");
            if (ptaTable && data.communication && data.communication.pta_meetings) {
                if (data.communication.pta_meetings.length === 0) {
                    ptaTable.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#94a3b8;">No virtual PTA meetings scheduled.</td></tr>`;
                } else {
                    ptaTable.innerHTML = data.communication.pta_meetings.map(p => `
                        <tr>
                            <td><strong>${p.title}</strong></td>
                            <td>${p.meeting_date} (${p.meeting_time})</td>
                            <td>${p.organizer_name}</td>
                            <td><span class="badge badge-branch">${p.target_class_name}</span></td>
                            <td>
                                ${p.meeting_link ? `<a href="${p.meeting_link}" target="_blank" class="btn btn-xs btn-outline-success"><i class="fa-solid fa-video"></i> Join Meeting Link</a>` : 'Link TBD'}
                            </td>
                        </tr>
                    `).join("");
                }
            }

            // TAB 4: FINANCE & ONLINE FEES
            const billTable = document.querySelector("#parent-bill-items-table tbody");
            if (billTable && data.financials && data.financials.bill_items) {
                if (data.financials.bill_items.length === 0) {
                    billTable.innerHTML = `<tr><td colspan="4" style="text-align:center; color:#94a3b8;">No fee items billed.</td></tr>`;
                } else {
                    billTable.innerHTML = data.financials.bill_items.map(b => `
                        <tr>
                            <td><strong>${b.description}</strong></td>
                            <td>GHS ${(b.amount || 0).toFixed(2)}</td>
                            <td style="color:#34d399;">GHS ${(b.amount_paid || 0).toFixed(2)}</td>
                            <td><span class="badge ${b.status === 'Paid' ? 'badge-success' : 'badge-danger'}">${b.status}</span></td>
                        </tr>
                    `).join("");
                }
            }

            const feeTable = document.querySelector("#parent-fees-history-table tbody");
            if (feeTable && data.financials && data.financials.payment_history) {
                if (data.financials.payment_history.length === 0) {
                    feeTable.innerHTML = `<tr><td colspan="5" style="text-align:center; color:#94a3b8;">No fee payments recorded yet.</td></tr>`;
                } else {
                    feeTable.innerHTML = data.financials.payment_history.map(p => `
                        <tr>
                            <td><strong>${p.receipt_no}</strong></td>
                            <td>${p.date}</td>
                            <td><span class="badge badge-branch">${p.method}</span></td>
                            <td style="color:#34d399; font-weight:700;">GHS ${(p.amount || 0).toFixed(2)}</td>
                            <td>
                                <button class="btn btn-xs btn-outline-info" onclick="downloadPaymentReceiptPdf(${p.id})">
                                    <i class="fa-solid fa-file-arrow-down"></i> Receipt PDF
                                </button>
                            </td>
                        </tr>
                    `).join("");
                }
            }

            // TAB 5: EVENTS & ACTIVITIES
            const actContainer = document.getElementById("parent-activities-container");
            if (actContainer && data.events_activities && data.events_activities.activities) {
                if (data.events_activities.activities.length === 0) {
                    actContainer.innerHTML = `<div class="glass-panel" style="padding:16px; color:#94a3b8; grid-column:span 2;">No extracurricular activities currently open for registration.</div>`;
                } else {
                    actContainer.innerHTML = data.events_activities.activities.map(act => `
                        <div class="glass-panel" style="padding:15px; border-left:4px solid #f59e0b;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                                <h4 style="margin:0;"><i class="fa-solid fa-trophy" style="color:#f59e0b;"></i> ${act.title}</h4>
                                <span class="badge badge-branch">${act.category}</span>
                            </div>
                            <p style="font-size:12px; color:#cbd5e1; margin-bottom:8px;">${act.description}</p>
                            <p style="font-size:12px; color:#94a3b8; margin-bottom:12px;">
                                <strong>Schedule:</strong> ${act.schedule_info} | <strong>Fee:</strong> GHS ${act.fee.toFixed(2)}
                            </p>
                            ${act.is_registered 
                                ? `<button class="btn btn-sm btn-success" disabled><i class="fa-solid fa-check-circle"></i> Registered</button>` 
                                : `<button class="btn btn-sm btn-warning" onclick="registerExtracurricular(${act.id}, '${data.student.id}')" style="font-weight:800;"><i class="fa-solid fa-plus-circle"></i> Register Child</button>`}
                        </div>
                    `).join("");
                }
            }

            // TAB 6: SUPPORT & ENGAGEMENT
            const medInp = document.getElementById("parent-medical-info");
            const emNameInp = document.getElementById("parent-emergency-name");
            const emPhoneInp = document.getElementById("parent-emergency-phone");

            if (medInp) medInp.value = data.student.medical_info || "";
            if (emNameInp) emNameInp.value = data.student.emergency_contact_name || "";
            if (emPhoneInp) emPhoneInp.value = data.student.emergency_contact_phone || "";

            const consentContainer = document.getElementById("parent-consent-container");
            if (consentContainer && data.support_engagement && data.support_engagement.consent_requests) {
                if (data.support_engagement.consent_requests.length === 0) {
                    consentContainer.innerHTML = `<div class="glass-panel" style="padding:14px; color:#94a3b8;">No active trip or activity consent requests.</div>`;
                } else {
                    consentContainer.innerHTML = data.support_engagement.consent_requests.map(c => `
                        <div class="glass-panel" style="padding:14px; border-left:4px solid ${c.consent_status === 'Approved' ? '#10b981' : c.consent_status === 'Declined' ? '#ef4444' : '#38bdf8'};">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <strong style="font-size:13px; color:#ffffff;">${c.title}</strong>
                                <span class="badge ${c.consent_status === 'Approved' ? 'badge-success' : c.consent_status === 'Declined' ? 'badge-danger' : 'badge-warning'}">${c.consent_status}</span>
                            </div>
                            <p style="font-size:12px; color:#cbd5e1; margin:6px 0;">${c.description}</p>
                            <p style="font-size:11px; color:#94a3b8; margin-bottom:10px;">Date: ${c.event_date} | Fee: GHS ${c.fee_amount.toFixed(2)}</p>
                            <div style="display:flex; gap:10px;">
                                <button class="btn btn-xs btn-success" onclick="respondConsent(${c.id}, 'Approved')" style="font-weight:700;"><i class="fa-solid fa-check"></i> Grant Consent</button>
                                <button class="btn btn-xs btn-danger" onclick="respondConsent(${c.id}, 'Declined')" style="font-weight:700;"><i class="fa-solid fa-xmark"></i> Decline</button>
                            </div>
                        </div>
                    `).join("");
                }
            }

            const surveyContainer = document.getElementById("parent-surveys-container");
            if (surveyContainer && data.support_engagement && data.support_engagement.surveys) {
                if (data.support_engagement.surveys.length === 0) {
                    surveyContainer.innerHTML = `<div class="glass-panel" style="padding:14px; color:#94a3b8;">No active parent feedback surveys.</div>`;
                } else {
                    surveyContainer.innerHTML = data.support_engagement.surveys.map(s => `
                        <div class="glass-panel" style="padding:15px; border-left:4px solid #a78bfa;">
                            <h4 style="margin:0 0 6px 0; color:#a78bfa;"><i class="fa-solid fa-poll"></i> ${s.title}</h4>
                            <p style="font-size:12px; color:#cbd5e1; margin-bottom:10px;">${s.description}</p>
                            <form onsubmit="submitParentSurvey(event, ${s.id}, '${data.student.id}')" style="display:flex; flex-direction:column; gap:8px;">
                                <div style="display:flex; align-items:center; gap:10px;">
                                    <label style="font-size:12px; color:#94a3b8;">Satisfaction Rating (1-5):</label>
                                    <select id="survey-rating-${s.id}" class="form-control" style="width:80px;">
                                        <option value="5">5 ⭐ (Excellent)</option>
                                        <option value="4">4 ⭐ (Very Good)</option>
                                        <option value="3">3 ⭐ (Good)</option>
                                        <option value="2">2 ⭐ (Fair)</option>
                                        <option value="1">1 ⭐ (Poor)</option>
                                    </select>
                                </div>
                                <textarea id="survey-text-${s.id}" class="form-control" rows="2" placeholder="Write feedback comments..."></textarea>
                                <button type="submit" class="btn btn-sm btn-primary" style="font-weight:800; align-self:flex-start;"><i class="fa-solid fa-paper-plane"></i> Submit Feedback</button>
                            </form>
                        </div>
                    `).join("");
                }
            }
        })
        .catch(err => console.error("Error loading parent overview:", err));
}

// Action Helper Functions
function registerExtracurricular(activityId, studentId) {
    apiFetch("/api/parent/activities/register", {
        method: "POST",
        body: { activity_id: activityId, student_id: studentId }
    })
    .then(res => {
        showToast(res.message, res.status === "success" ? "success" : "info");
        loadParentPortalData(studentId);
    })
    .catch(err => showToast("Registration error: " + err.message, "error"));
}

function respondConsent(consentId, status) {
    apiFetch("/api/parent/consent/respond", {
        method: "POST",
        body: { consent_id: consentId, consent_status: status }
    })
    .then(res => {
        showToast(res.message, "success");
        if (window.currentParentOverview && window.currentParentOverview.student) {
            loadParentPortalData(window.currentParentOverview.student.id);
        }
    })
    .catch(err => showToast("Consent error: " + err.message, "error"));
}

function submitParentSurvey(e, surveyId, studentId) {
    e.preventDefault();
    const rating = parseInt(document.getElementById(`survey-rating-${surveyId}`)?.value || "5");
    const feedback = document.getElementById(`survey-text-${surveyId}`)?.value || "";

    apiFetch("/api/parent/surveys/submit", {
        method: "POST",
        body: { survey_id: surveyId, student_id: studentId, rating: rating, feedback_text: feedback }
    })
    .then(res => {
        showToast(res.message, "success");
        loadParentPortalData(studentId);
    })
    .catch(err => showToast("Survey error: " + err.message, "error"));
}

// Listener: Update Medical & Emergency Info Form
document.getElementById("form-parent-update-student-info")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const overview = window.currentParentOverview;
    if (!overview || !overview.student) return;

    const payload = {
        student_id: overview.student.id,
        emergency_contact_name: document.getElementById("parent-emergency-name")?.value || "",
        emergency_contact_phone: document.getElementById("parent-emergency-phone")?.value || "",
        medical_info: document.getElementById("parent-medical-info")?.value || ""
    };

    apiFetch("/api/parent/student-profile/update", { method: "PUT", body: payload })
        .then(res => {
            showToast(res.message, "success");
            loadParentPortalData(overview.student.id);
        })
        .catch(err => showToast("Update error: " + err.message, "error"));
});

// Listener: Open Parent Message Modal
document.getElementById("btn-open-parent-message-modal")?.addEventListener("click", () => {
    document.getElementById("modal-parent-message")?.classList.add("show");
});

// Listener: Send Parent Direct Message Form
document.getElementById("form-parent-send-message")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const overview = window.currentParentOverview;
    const studentId = overview && overview.student ? overview.student.id : "";

    const payload = {
        student_id: studentId,
        recipient_role: document.getElementById("parent-msg-recipient-role")?.value || "Teacher",
        subject: document.getElementById("parent-msg-subject")?.value || "",
        message: document.getElementById("parent-msg-content")?.value || ""
    };

    apiFetch("/api/parent/messages", { method: "POST", body: payload })
        .then(res => {
            showToast(res.message, "success");
            document.getElementById("modal-parent-message")?.classList.remove("show");
            document.getElementById("form-parent-send-message")?.reset();
            if (studentId) loadParentPortalData(studentId);
        })
        .catch(err => showToast("Message error: " + err.message, "error"));
});

// Parent Open Online Payment Modal Listener
document.getElementById("btn-parent-open-pay-online")?.addEventListener("click", () => {
    const overview = window.currentParentOverview;
    if (!overview || !overview.student) {
        showToast("Unable to load student payment details. Please refresh.", "error");
        return;
    }

    const nameEl = document.getElementById("parent-pay-student-name");
    const balEl = document.getElementById("parent-pay-balance-due");
    const amtInp = document.getElementById("parent-pay-amount-input");
    const phoneInp = document.getElementById("parent-pay-phone");

    const bal = overview.financials ? overview.financials.balance_due : 0;

    if (nameEl) nameEl.value = overview.student.full_name;
    if (balEl) balEl.value = `GHS ${bal.toFixed(2)}`;
    if (amtInp) amtInp.value = bal > 0 ? bal.toFixed(2) : "50.00";
    if (phoneInp) phoneInp.value = overview.student.parent_phone || "";

    document.getElementById("modal-parent-pay-online")?.classList.add("show");
});

// Parent Submit Online Fee Payment
document.getElementById("form-parent-pay-online")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const overview = window.currentParentOverview;
    if (!overview || !overview.student) {
        showToast("Invalid student record session", "error");
        return;
    }

    const amount = parseFloat(document.getElementById("parent-pay-amount-input")?.value || "0");
    const channel = document.getElementById("parent-pay-channel")?.value || "mobile_money";
    const phone = document.getElementById("parent-pay-phone")?.value || overview.student.parent_phone || "";

    if (amount <= 0) {
        showToast("Please enter a valid payment amount", "error");
        return;
    }

    const submitBtn = document.getElementById("btn-parent-submit-momo");
    if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...'; }

    const initPayload = {
        student_id: overview.student.id,
        amount: amount,
        channel: channel,
        phone_number: phone,
        email: `parent_${overview.student.id}@orion.edu`
    };

    apiFetch("/api/payments/online/initiate", { method: "POST", body: initPayload })
        .then(res => {
            const ref = res.reference;
            if (res.authorization_url) {
                window.open(res.authorization_url, "_blank");
            }

            showToast("Verifying and reconciling payment with financial ledger...", "info");

            return apiFetch(`/api/payments/online/verify/${ref}`, {
                method: "POST",
                body: { reference: ref, student_id: overview.student.id, amount: amount }
            });
        })
        .then(vRes => {
            showToast(`🎉 ${vRes.message} SMS receipt dispatched to ${phone}!`, "success");
            document.getElementById("modal-parent-pay-online")?.classList.remove("show");
            document.getElementById("form-parent-pay-online")?.reset();
            loadParentPortalData(overview.student.id);
            if (vRes.payment_id) {
                const tokenParam = currentToken ? `?token=${encodeURIComponent(currentToken)}` : '';
                window.open(`/api/fees/payments/${vRes.payment_id}/receipt${tokenParam}`, "_blank");
            }
        })
        .catch(err => showToast("Online payment error: " + err.message, "error"))
        .finally(() => {
            if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = '<i class="fa-solid fa-lock"></i> Proceed to Pay'; }
        });
});

document.getElementById("btn-add-branch-trigger")?.addEventListener("click", () => {
     syncDisabledModulesToToggles("add-branch-module-toggles", "");
     openModal("modal-add-branch");
});

document.getElementById("form-add-branch")?.addEventListener("submit", (e) => {
     e.preventDefault();
     const disabledMods = syncDisabledModulesFromContainer("add-branch-module-toggles", "branch-disabled-modules");
     const payload = {
          name: document.getElementById("branch-name").value.trim(),
          code: document.getElementById("branch-code").value.trim(),
          phone: document.getElementById("branch-phone").value.trim(),
          email: document.getElementById("branch-email").value.trim(),
          address: document.getElementById("branch-address").value.trim(),
          notes: document.getElementById("branch-notes").value.trim(),
          system_fee: parseFloat(document.getElementById("branch-system-fee").value || "0"),
          disabled_modules: disabledMods,
          head_username: document.getElementById("branch-head-username").value.trim(),
          head_password: document.getElementById("branch-head-password").value,
          head_full_name: document.getElementById("branch-head-fullname").value.trim(),
          head_email: document.getElementById("branch-head-email").value.trim()
     };
     
     apiFetch("/api/sysadmin/branches", { method: "POST", body: payload })
         .then(() => {
              showToast("New school branch registered and seeded successfully!", "success");
              closeModal("modal-add-branch");
              document.getElementById("form-add-branch").reset();
              loadSysadmin();
         })
         .catch(err => showToast(parseApiDetailMessage(err, err.message || "Failed to create branch"), "error"));
});

document.getElementById("form-edit-branch")?.addEventListener("submit", (e) => {
     e.preventDefault();
     const bid = document.getElementById("edit-branch-id").value;
     const disabledMods = syncDisabledModulesFromContainer("edit-branch-module-toggles", "edit-branch-disabled-modules");
     const payload = {
          name: document.getElementById("edit-branch-name").value,
          phone: document.getElementById("edit-branch-phone").value,
          email: document.getElementById("edit-branch-email").value,
          address: document.getElementById("edit-branch-address").value,
          is_active: document.getElementById("edit-branch-status").value === "true",
          system_fee: parseFloat(document.getElementById("edit-branch-system-fee").value || "0"),
          disabled_modules: disabledMods,
          notes: document.getElementById("edit-branch-notes").value
     };

     apiFetch(`/api/sysadmin/branches/${bid}`, { method: "PUT", body: payload })
         .then(() => {
              showToast("Branch configuration updated successfully!", "success");
              closeModal("modal-edit-branch");
              loadSysadmin();
         })
         .catch(err => showToast(parseApiDetailMessage(err, err.message || "Failed to update branch"), "error"));
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
    const header = document.querySelector(`#${panelId} .tab-header`) || document.querySelector(`#${panelId} .module-tabs`);
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

function openModal(modalId) {
    const modal = typeof modalId === "string" ? document.getElementById(modalId) : modalId;
    if (modal) {
        modal.classList.add("show");
        modal.style.display = "flex";
    }
}

function closeModal(modalId) {
    const modal = typeof modalId === "string" ? document.getElementById(modalId) : modalId;
    if (modal) {
        modal.classList.remove("show");
        modal.style.display = "none";
    }
}

// Global modal close listener
document.addEventListener("click", (e) => {
    const btn = e.target.closest(".modal-close, .btn-modal-cancel");
    if (btn) {
        const modal = btn.closest(".modal-backdrop, .modal");
        if (modal) {
            closeModal(modal);
        }
    }
});

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

// ── TIMETABLE PANELS & CONTROLLER ───────────────────────────────────────────

function loadTimetablePanel() {
    initTabs("panel-timetable");
    
    // Load class dropdown options
    apiFetch("/api/academics/classes")
        .then(classes => {
            const select = document.getElementById("timetable-class-select");
            if (!select) return;
            select.innerHTML = '<option value="">— Select Class Timetable —</option>';
            classes.forEach(c => {
                select.innerHTML += `<option value="${c.id}">${c.name} (${c.level}${c.stream ? ' ' + c.stream : ''})</option>`;
            });
            
            // If class was already selected, reload it
            if (select.value) {
                loadTimetableGrid(select.value);
            }
        });
        
    // Listen for class selection change
    const classSelect = document.getElementById("timetable-class-select");
    if (classSelect) {
        classSelect.addEventListener("change", (e) => {
            const cid = e.target.value;
            if (cid) {
                loadTimetableGrid(cid);
            } else {
                document.querySelector("#timetable-grid-table thead").innerHTML = "";
                document.querySelector("#timetable-grid-table tbody").innerHTML = '<tr><td class="text-center">Please select a class to load its schedule.</td></tr>';
            }
        });
    }

    // Load setup days and periods
    loadTimetableConfig();
}

function loadTimetableConfig() {
    apiFetch("/api/timetable/config")
        .then(cfg => {
            // Check correct days checkboxes
            const daysCheckboxes = document.querySelectorAll('input[name="tt-days"]');
            daysCheckboxes.forEach(cb => {
                cb.checked = cfg.days.includes(cb.value);
            });
            
            // Render active periods list
            const tbody = document.querySelector("#timetable-periods-list-table tbody");
            if (tbody) {
                tbody.innerHTML = "";
                if (cfg.periods.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" class="text-center">No periods configured.</td></tr>';
                    return;
                }
                cfg.periods.forEach((p, idx) => {
                    const typeBadge = p.is_break 
                        ? '<span class="badge" style="background:rgba(239,68,68,0.15);color:#f87171;">Break / Recess</span>'
                        : '<span class="badge" style="background:rgba(16,185,129,0.15);color:#34d399;">Teachable Slot</span>';
                        
                    tbody.innerHTML += `
                        <tr>
                            <td><strong>${p.name}</strong></td>
                            <td>${p.start}</td>
                            <td>${p.end}</td>
                            <td>${typeBadge}</td>
                            <td>
                                <button class="btn btn-sm btn-secondary btn-edit-tt-period" data-index="${idx}" data-name="${p.name}" data-start="${p.start}" data-end="${p.end}" data-break="${p.is_break ? 'true' : 'false'}" style="margin-right:6px;">
                                    <i class="fa-solid fa-pencil"></i> Edit
                                </button>
                                <button class="btn btn-sm btn-danger btn-delete-tt-period" data-index="${idx}">
                                    <i class="fa-solid fa-trash"></i> Delete
                                </button>
                            </td>
                        </tr>`;
                });
            }
        });
}

// Handler: Checkbox active days change
document.addEventListener("change", (e) => {
    if (e.target.name === "tt-days") {
        const activeDays = [];
        document.querySelectorAll('input[name="tt-days"]:checked').forEach(cb => {
            activeDays.push(cb.value);
        });
        
        // Fetch current periods to save alongside days
        apiFetch("/api/timetable/config")
            .then(cfg => {
                apiFetch("/api/timetable/config", {
                    method: "POST",
                    body: { days: activeDays, periods: cfg.periods }
                })
                .then(() => {
                    showToast("Timetable days updated", "success");
                    const classSelect = document.getElementById("timetable-class-select");
                    if (classSelect && classSelect.value) {
                        loadTimetableGrid(classSelect.value);
                    }
                });
            });
    }
});

function checkPeriodOverlap(periods, newPeriod, excludeIndex = -1) {
    const parseTime = (t) => {
        const parts = t.split(":");
        const h = parseInt(parts[0], 10);
        const m = parseInt(parts[1], 10);
        return h * 60 + m;
    };
    const newStart = parseTime(newPeriod.start);
    const newEnd = parseTime(newPeriod.end);
    
    if (newStart >= newEnd) {
        return "Start time must be strictly before end time.";
    }
    
    for (let i = 0; i < periods.length; i++) {
        if (i === excludeIndex) continue;
        const p = periods[i];
        const pStart = parseTime(p.start);
        const pEnd = parseTime(p.end);
        
        if (newStart < pEnd && pStart < newEnd) {
            return `This period overlaps with "${p.name}" (${p.start} - ${p.end}).`;
        }
    }
    return null;
}

// Form submit: Add time period
const formAddPeriod = document.getElementById("form-add-timetable-period");
if (formAddPeriod) {
    formAddPeriod.addEventListener("submit", (e) => {
        e.preventDefault();
        const pName = document.getElementById("tt-period-name").value;
        const pStart = document.getElementById("tt-period-start").value;
        const pEnd = document.getElementById("tt-period-end").value;
        const isBreak = document.getElementById("tt-period-break").checked;
        
        apiFetch("/api/timetable/config")
            .then(cfg => {
                const newPeriod = { name: pName, start: pStart, end: pEnd, is_break: isBreak };
                const overlapError = checkPeriodOverlap(cfg.periods, newPeriod);
                if (overlapError) {
                    showToast(overlapError, "error");
                    return;
                }
                // Keep periods sorted by start time
                const periods = [...cfg.periods, newPeriod].sort((a,b) => a.start.localeCompare(b.start));
                
                apiFetch("/api/timetable/config", {
                    method: "POST",
                    body: { days: cfg.days, periods: periods }
                })
                .then(() => {
                    showToast("Time period added successfully", "success");
                    formAddPeriod.reset();
                    loadTimetableConfig();
                    const classSelect = document.getElementById("timetable-class-select");
                    if (classSelect && classSelect.value) {
                        loadTimetableGrid(classSelect.value);
                    }
                });
            });
    });
}

// Edit & Delete delegation: edit or delete period
document.addEventListener("click", (e) => {
    const delBtn = e.target.closest(".btn-delete-tt-period");
    if (delBtn) {
        const index = parseInt(delBtn.dataset.index);
        if (!confirm("Are you sure you want to delete this period? This will also clear assignments in slots scheduled for this period.")) return;
        
        apiFetch("/api/timetable/config")
            .then(cfg => {
                const periods = [...cfg.periods];
                periods.splice(index, 1);
                
                apiFetch("/api/timetable/config", {
                    method: "POST",
                    body: { days: cfg.days, periods: periods }
                })
                .then(() => {
                    showToast("Period removed", "success");
                    loadTimetableConfig();
                    const classSelect = document.getElementById("timetable-class-select");
                    if (classSelect && classSelect.value) {
                        loadTimetableGrid(classSelect.value);
                    }
                });
            });
        return;
    }

    const editBtn = e.target.closest(".btn-edit-tt-period");
    if (editBtn) {
        const idx = editBtn.dataset.index;
        document.getElementById("edit-tt-period-index").value = idx;
        document.getElementById("edit-tt-period-name").value = editBtn.dataset.name;
        document.getElementById("edit-tt-period-start").value = editBtn.dataset.start;
        document.getElementById("edit-tt-period-end").value = editBtn.dataset.end;
        document.getElementById("edit-tt-period-break").checked = (editBtn.dataset.break === "true");
        
        const modal = document.getElementById("modal-edit-timetable-period");
        if (modal) modal.classList.add("show");
    }
});

// Form submit: Edit time period
const formEditPeriod = document.getElementById("form-edit-timetable-period");
if (formEditPeriod) {
    formEditPeriod.addEventListener("submit", (e) => {
        e.preventDefault();
        const idx = parseInt(document.getElementById("edit-tt-period-index").value);
        const pName = document.getElementById("edit-tt-period-name").value;
        const pStart = document.getElementById("edit-tt-period-start").value;
        const pEnd = document.getElementById("edit-tt-period-end").value;
        const isBreak = document.getElementById("edit-tt-period-break").checked;
        
        apiFetch("/api/timetable/config")
            .then(cfg => {
                const newPeriod = { name: pName, start: pStart, end: pEnd, is_break: isBreak };
                const overlapError = checkPeriodOverlap(cfg.periods, newPeriod, idx);
                if (overlapError) {
                    showToast(overlapError, "error");
                    return;
                }
                const periods = [...cfg.periods];
                periods[idx] = newPeriod;
                // Keep periods sorted by start time
                periods.sort((a,b) => a.start.localeCompare(b.start));
                
                apiFetch("/api/timetable/config", {
                    method: "POST",
                    body: { days: cfg.days, periods: periods }
                })
                .then(() => {
                    showToast("Time period updated successfully", "success");
                    const modal = document.getElementById("modal-edit-timetable-period");
                    if (modal) modal.classList.remove("show");
                    loadTimetableConfig();
                    const classSelect = document.getElementById("timetable-class-select");
                    if (classSelect && classSelect.value) {
                        loadTimetableGrid(classSelect.value);
                    }
                });
            });
    });
}


function loadTimetableGrid(classId) {
    Promise.all([
        apiFetch("/api/timetable/config"),
        apiFetch(`/api/timetable/class/${classId}`)
    ]).then(([cfg, slots]) => {
        const thead = document.querySelector("#timetable-grid-table thead");
        const tbody = document.querySelector("#timetable-grid-table tbody");
        if (!thead || !tbody) return;
        
        // 1. Render Header Days
        let headerHtml = '<tr><th>Time Period</th>';
        cfg.days.forEach(d => {
            headerHtml += `<th class="text-center">${d}</th>`;
        });
        headerHtml += '</tr>';
        thead.innerHTML = headerHtml;
        
        // Build lookup map (day, slot) -> slot object
        const gridMap = {};
        slots.forEach(s => {
            gridMap[`${s.day_of_week}_${s.time_slot}`] = s;
        });
        
        // 2. Render Rows (Periods)
        tbody.innerHTML = "";
        if (cfg.periods.length === 0) {
            tbody.innerHTML = `<tr><td colspan="${cfg.days.length + 1}" class="text-center">No periods configured. Add some in the Days &amp; Periods Setup tab.</td></tr>`;
            return;
        }
        
        cfg.periods.forEach(p => {
            const time_slot_key = `${p.start} - ${p.end}`;
            const tr = document.createElement("tr");
            
            // First cell: Period name & time range
            let rowHtml = `
                <td style="font-weight:600; min-width:130px; border-right:2px solid rgba(255,255,255,0.05);">
                    <div style="color:var(--primary-color);">${p.name}</div>
                    <div style="font-size:11px;color:var(--text-secondary);">${time_slot_key}</div>
                </td>`;
                
            if (p.is_break) {
                // Break periods are spanned across all days
                const breakText = p.name.toUpperCase();
                rowHtml += `
                    <td colspan="${cfg.days.length}" class="text-center" style="background:rgba(255,255,255,0.03); color:var(--text-secondary); font-weight:700; letter-spacing:4px; font-size:12px; pointer-events:none;">
                        — ${breakText} —
                    </td>`;
                tr.innerHTML = rowHtml;
            } else {
                // Regular teachable periods
                cfg.days.forEach(d => {
                    const slot = gridMap[`${d}_${time_slot_key}`];
                    if (slot) {
                        rowHtml += `
                            <td class="text-center timetable-cell occupied" data-day="${d}" data-time="${time_slot_key}" data-slot-id="${slot.id}" data-subject-id="${slot.subject_id}" data-staff-id="${slot.staff_id}" style="cursor:pointer; vertical-align:middle; transition: background 0.2s;">
                                <div style="font-weight:700; color:#fff; font-size:13px;">${slot.subject_code || slot.subject_name}</div>
                                <div style="font-size:10px; color:var(--text-secondary); margin-top:2px;">${slot.teacher_name}</div>
                            </td>`;
                    } else {
                        rowHtml += `
                            <td class="text-center timetable-cell free" data-day="${d}" data-time="${time_slot_key}" style="cursor:pointer; color:rgba(255,255,255,0.2); vertical-align:middle; transition: background 0.2s;">
                                <span style="font-size:11px;">— FREE —</span>
                            </td>`;
                    }
                });
                tr.innerHTML = rowHtml;
            }
            tbody.appendChild(tr);
        });
        
        // Double-click cells handler for manual slot edits (Admin/Headteacher only)
        document.querySelectorAll(".timetable-cell").forEach(cell => {
            cell.addEventListener("dblclick", () => {
                if (currentUser && (currentUser.role === "Teacher" || currentUser.role === "Subject Teacher" || currentUser.is_class_teacher) && currentUser.role !== "System Admin" && currentUser.role !== "Admin/Headteacher" && currentUser.role !== "Super Admin") {
                    return; // View-only mode for teachers
                }
                const day = cell.getAttribute("data-day");
                const time = cell.getAttribute("data-time");
                const slotId = cell.getAttribute("data-slot-id") || "";
                const currentSubj = cell.getAttribute("data-subject-id") || "";
                const currentStaff = cell.getAttribute("data-staff-id") || "";
                
                document.getElementById("edit-tt-day").value = day;
                document.getElementById("edit-tt-time").value = time;
                document.getElementById("edit-tt-day-label").innerText = day;
                document.getElementById("edit-tt-time-label").innerText = time;
                
                // Populate options
                Promise.all([
                    apiFetch("/api/academics/subjects"),
                    apiFetch("/api/staff"),
                    apiFetch("/api/academics/assignments")
                ]).then(([subjects, staff, assignments]) => {
                    const subjSel = document.getElementById("edit-tt-subject-select");
                    const staffSel = document.getElementById("edit-tt-teacher-select");
                    
                    subjSel.innerHTML = '<option value="">— Select Subject —</option>';
                    subjects.forEach(s => {
                        subjSel.innerHTML += `<option value="${s.id}">${s.name} (${s.code})</option>`;
                    });
                    if (currentSubj) subjSel.value = currentSubj;
                    
                    staffSel.innerHTML = '<option value="">— Select Teacher —</option>';
                    staff.forEach(t => {
                        staffSel.innerHTML += `<option value="${t.id}">${t.first_name} ${t.last_name}</option>`;
                    });
                    if (currentStaff) staffSel.value = currentStaff;

                    // Auto-select assigned teacher when subject changes
                    subjSel.onchange = () => {
                        const subId = parseInt(subjSel.value);
                        if (!subId) return;
                        const match = assignments.find(a => parseInt(a.class_id) === parseInt(classId) && parseInt(a.subject_id) === subId);
                        if (match) {
                            staffSel.value = match.teacher_id;
                        }
                    };
                    
                    // Show or hide Clear button depending on whether cell is currently occupied
                    const btnDelete = document.querySelector(".btn-modal-delete-slot");
                    if (slotId) {
                        btnDelete.style.display = "block";
                        btnDelete.onclick = () => {
                            if (confirm("Clear this scheduled period?")) {
                                apiFetch(`/api/timetable/slots/${slotId}`, { method: "DELETE" })
                                    .then(() => {
                                        showToast("Timetable period cleared", "success");
                                        document.getElementById("modal-edit-timetable-slot").classList.remove("show");
                                        loadTimetableGrid(classId);
                                    });
                            }
                        };
                    } else {
                        btnDelete.style.display = "none";
                    }
                    
                    document.getElementById("modal-edit-timetable-slot").classList.add("show");
                });
            });
        });
    });
}

// Modal submit: save/edit timetable slot
const formEditSlot = document.getElementById("form-edit-timetable-slot");
if (formEditSlot) {
    formEditSlot.addEventListener("submit", (e) => {
        e.preventDefault();
        const classSelect = document.getElementById("timetable-class-select");
        if (!classSelect || !classSelect.value) return;
        
        const payload = {
            class_id: parseInt(classSelect.value),
            subject_id: parseInt(document.getElementById("edit-tt-subject-select").value),
            staff_id: parseInt(document.getElementById("edit-tt-teacher-select").value),
            day_of_week: document.getElementById("edit-tt-day").value,
            time_slot: document.getElementById("edit-tt-time").value
        };
        
        apiFetch("/api/timetable/slots", {
            method: "POST",
            body: payload
        })
        .then(() => {
            showToast("Slot saved successfully", "success");
            document.getElementById("modal-edit-timetable-slot").classList.remove("show");
            loadTimetableGrid(classSelect.value);
        })
        .catch(err => showToast(err.message, "error"));
    });
}

// Auto-Generate Button Action
const btnGenTimetable = document.getElementById("btn-generate-timetable");
if (btnGenTimetable) {
    btnGenTimetable.addEventListener("click", () => {
        const classSelect = document.getElementById("timetable-class-select");
        if (!classSelect || !classSelect.value) {
            showToast("Please select a class to generate a timetable for first.", "error");
            return;
        }
        
        btnGenTimetable.disabled = true;
        btnGenTimetable.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating...';
        
        apiFetch(`/api/timetable/generate/${classSelect.value}`, { method: "POST" })
            .then(res => {
                if (res.clash_free) {
                    showToast("Clash-free timetable auto-generated successfully!", "success");
                } else {
                    showToast("Timetable generated with minor clashes (limited teachers available). Please inspect and adjust manual cells if needed.", "warning");
                }
                loadTimetableGrid(classSelect.value);
            })
            .catch(err => showToast(err.message, "error"))
            .finally(() => {
                btnGenTimetable.disabled = false;
                btnGenTimetable.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Auto-Generate';
            });
    });
}

// Export PDF Button Action
const btnExportTTPdf = document.getElementById("btn-export-timetable-pdf");
if (btnExportTTPdf) {
    btnExportTTPdf.addEventListener("click", () => {
        const classSelect = document.getElementById("timetable-class-select");
        if (!classSelect || !classSelect.value) {
            showToast("Please select a class first.", "error");
            return;
        }
        
        viewPdf(`/api/timetable/class/${classSelect.value}/pdf`, `Timetable_${classSelect.value}.pdf`);
    });
}

// --- User Profile & Password Change Handlers ---
function openUserProfileModal() {
    initTabs("modal-user-profile");
    apiFetch("/api/user/profile")
        .then(data => {
            const uName = document.getElementById("user-profile-username");
            const uRole = document.getElementById("user-profile-role");
            const uFName = document.getElementById("user-profile-firstname");
            const uLName = document.getElementById("user-profile-lastname");
            const uEmail = document.getElementById("user-profile-email");
            const uPhone = document.getElementById("user-profile-phone");
            
            if (uName) uName.value = data.username || "";
            if (uRole) uRole.value = data.role || "";
            if (uFName) uFName.value = data.first_name || "";
            if (uLName) uLName.value = data.last_name || "";
            if (uEmail) uEmail.value = data.email || "";
            if (uPhone) uPhone.value = data.phone || "";

            // Clear password fields
            const pCurr = document.getElementById("user-pass-current");
            const pNew = document.getElementById("user-pass-new");
            const pConf = document.getElementById("user-pass-confirm");
            if (pCurr) pCurr.value = "";
            if (pNew) pNew.value = "";
            if (pConf) pConf.value = "";

            openModal("modal-user-profile");
        })
        .catch(err => showToast(err.message, "error"));
}

document.getElementById("form-user-personal-info")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {
        first_name: document.getElementById("user-profile-firstname").value,
        last_name: document.getElementById("user-profile-lastname").value,
        email: document.getElementById("user-profile-email").value,
        phone: document.getElementById("user-profile-phone").value
    };
    
    apiFetch("/api/user/profile", { method: "PUT", body: payload })
        .then(res => {
            showToast("Profile information updated successfully!", "success");
            if (res.full_name) {
                const dispName = document.getElementById("user-display-name");
                if (dispName) dispName.innerText = res.full_name;
            }
            closeModal("modal-user-profile");
        })
        .catch(err => showToast(err.message, "error"));
});

document.getElementById("form-user-change-password")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const currentPass = document.getElementById("user-pass-current").value;
    const newPass = document.getElementById("user-pass-new").value;
    const confirmPass = document.getElementById("user-pass-confirm").value;
    
    if (newPass !== confirmPass) {
        showToast("New password and confirmation do not match!", "error");
        return;
    }
    
    const payload = {
        current_password: currentPass,
        new_password: newPass,
        confirm_password: confirmPass
    };
    
    apiFetch("/api/user/change-password", { method: "POST", body: payload })
        .then(() => {
            showToast("Password updated successfully!", "success");
            closeModal("modal-user-profile");
        })
        .catch(err => showToast(err.message, "error"));
});

// --- Parent Directory & Guardian Management Handlers ---
window.parentsCache = [];

function loadParentsData() {
    apiFetch("/api/parents")
        .then(parents => {
            window.parentsCache = parents;
            renderParentsTable(parents);
            updateParentsKPIs(parents);
        })
        .catch(err => {
            console.error("Error loading parents directory:", err);
            showToast("Failed to load parent records", "error");
        });
}

function updateParentsKPIs(parents) {
    const totalEl = document.getElementById("parent-kpi-total");
    const linkedEl = document.getElementById("parent-kpi-linked-students");
    const unlinkedEl = document.getElementById("parent-kpi-unlinked-students");
    const accountsEl = document.getElementById("parent-kpi-portal-accounts");

    const totalParents = parents ? parents.length : 0;
    let totalLinkedStudents = 0;

    if (parents) {
        parents.forEach(p => {
            totalLinkedStudents += (p.linked_students ? p.linked_students.length : 0);
        });
    }

    if (totalEl) totalEl.innerText = totalParents;
    if (linkedEl) linkedEl.innerText = totalLinkedStudents;

    apiFetch("/api/students")
        .then(students => {
            const totalActive = students.length;
            const unlinkedCount = Math.max(0, totalActive - totalLinkedStudents);
            if (unlinkedEl) unlinkedEl.innerText = unlinkedCount;
            if (accountsEl) accountsEl.innerText = `${totalParents} Active`;
        })
        .catch(err => console.error("Error calculating unlinked students:", err));
}

function renderParentsTable(parents) {
    const tbody = document.querySelector("#parents-table tbody");
    if (!tbody) return;

    if (!parents || parents.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center" style="color:#94a3b8; padding:30px;">No parent records found. Click "Register New Parent" to add one.</td></tr>`;
        return;
    }

    tbody.innerHTML = parents.map(p => {
        const displayName = (p.full_name && p.full_name.trim()) ? p.full_name.trim() : (`${p.first_name || ''} ${p.last_name || ''}`.trim() || `Parent #${p.id}`);
        const displayPhone = (p.phone && p.phone.trim()) ? p.phone.trim() : 'N/A';
        const safeName = displayName.replace(/\\/g, "\\\\").replace(/'/g, "\\'").replace(/"/g, "&quot;");

        const studentPills = (p.linked_students && p.linked_students.length > 0)
            ? p.linked_students.map(s => {
                const sName = (s.name || '').trim();
                const safeSName = sName.replace(/\\/g, "\\\\").replace(/'/g, "\\'").replace(/"/g, "&quot;");
                return `
                <span class="badge" style="background:rgba(99,102,241,0.15); color:#818cf8; border:1px solid rgba(99,102,241,0.3); font-weight:700; padding:4px 10px; margin:2px; display:inline-flex; align-items:center; gap:6px;">
                    <i class="fa-solid fa-graduation-cap"></i> ${sName} (${s.id})
                    <i class="fa-solid fa-xmark" onclick="unlinkStudentFromParent(${p.id}, '${s.id}', '${safeSName}')" style="cursor:pointer; color:#f87171; margin-left:4px;" title="Unlink Student"></i>
                </span>
                `;
            }).join("")
            : `<span style="color:#f59e0b; font-size:12px; font-weight:700;"><i class="fa-solid fa-circle-exclamation"></i> No Linked Student</span>`;

        return `
            <tr>
                <td>
                    <strong style="color:#ffffff; font-size:14px;">${displayName}</strong>
                    <div style="font-size:11px; color:#94a3b8;">ID: PAR-${p.id}</div>
                </td>
                <td><strong style="color:#34d399; font-family:monospace;"><i class="fa-solid fa-phone" style="font-size:11px;"></i> ${displayPhone}</strong></td>
                <td>${p.email ? `<a href="mailto:${p.email}" style="color:#60a5fa;"><i class="fa-solid fa-envelope" style="font-size:11px;"></i> ${p.email}</a>` : `<span style="color:#64748b;">N/A</span>`}</td>
                <td>
                    <div style="font-weight:600; color:#e2e8f0;">${p.occupation || 'N/A'}</div>
                    <div style="font-size:12px; color:#94a3b8;">${p.address || ''}</div>
                </td>
                <td>${studentPills}</td>
                <td>
                    <div style="display:flex; gap:6px; flex-wrap:wrap;">
                        <button class="btn btn-sm btn-outline-info" onclick="openLinkStudentModal(${p.id}, '${safeName}')" title="Link Student">
                            <i class="fa-solid fa-link"></i> Link
                        </button>
                        <button class="btn btn-sm btn-secondary" onclick="openEditParentModal(${p.id})" title="Edit Info">
                            <i class="fa-solid fa-pen-to-square"></i> Edit
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deleteParent(${p.id}, '${safeName}')" title="Delete Parent">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join("");
}

document.getElementById("parent-search-input")?.addEventListener("input", (e) => {
    const query = (e.target.value || "").toLowerCase().trim();
    if (!window.parentsCache) return;

    if (!query) {
        renderParentsTable(window.parentsCache);
        return;
    }

    const filtered = window.parentsCache.filter(p => {
        const nameMatch = (p.full_name || "").toLowerCase().includes(query);
        const phoneMatch = (p.phone || "").toLowerCase().includes(query);
        const emailMatch = (p.email || "").toLowerCase().includes(query);
        const occMatch = (p.occupation || "").toLowerCase().includes(query);
        const studentMatch = p.linked_students && p.linked_students.some(s => (s.name || "").toLowerCase().includes(query) || (s.id || "").toLowerCase().includes(query));
        return nameMatch || phoneMatch || emailMatch || occMatch || studentMatch;
    });

    renderParentsTable(filtered);
});

document.getElementById("btn-open-add-parent")?.addEventListener("click", openAddParentModal);

function openAddParentModal() {
    const form = document.getElementById("form-add-parent");
    if (form) form.reset();

    const studentSel = document.getElementById("parent-initial-student");
    if (studentSel) {
        apiFetch("/api/students")
            .then(students => {
                studentSel.innerHTML = `<option value="">— Select Student to Link (Optional) —</option>` + students.map(s => `
                    <option value="${s.id}">${s.first_name} ${s.last_name} (${s.id} - ${s.class_name || 'Unassigned'})</option>
                `).join("");
            })
            .catch(err => console.error("Error loading students for parent modal:", err));
    }

    openModal("modal-add-parent");
}

document.getElementById("form-add-parent")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const payload = {
        first_name: document.getElementById("parent-fname")?.value || "",
        last_name: document.getElementById("parent-lname")?.value || "",
        phone: document.getElementById("parent-phone")?.value || "",
        email: document.getElementById("parent-email")?.value || "",
        occupation: document.getElementById("parent-occupation")?.value || "",
        address: document.getElementById("parent-address")?.value || "",
        student_id: document.getElementById("parent-initial-student")?.value || ""
    };

    apiFetch("/api/parents", {
        method: "POST",
        body: payload
    })
    .then(res => {
        showToast(res.message || "Parent registered successfully!", "success");
        closeModal("modal-add-parent");
        const searchInput = document.getElementById("parent-search-input");
        if (searchInput) searchInput.value = "";
        loadParentsData();
    })
    .catch(err => showToast(err.message || "Failed to register parent", "error"));
});

function openEditParentModal(parentId) {
    const parent = (window.parentsCache || []).find(p => p.id === parentId);
    if (!parent) return;

    document.getElementById("edit-parent-id").value = parent.id;
    document.getElementById("edit-parent-fname").value = parent.first_name || "";
    document.getElementById("edit-parent-lname").value = parent.last_name || "";
    document.getElementById("edit-parent-phone").value = parent.phone || "";
    document.getElementById("edit-parent-email").value = parent.email || "";
    document.getElementById("edit-parent-occupation").value = parent.occupation || "";
    document.getElementById("edit-parent-address").value = parent.address || "";

    openModal("modal-edit-parent");
}

document.getElementById("form-edit-parent")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const parentId = document.getElementById("edit-parent-id")?.value;
    if (!parentId) return;

    const payload = {
        first_name: document.getElementById("edit-parent-fname")?.value || "",
        last_name: document.getElementById("edit-parent-lname")?.value || "",
        phone: document.getElementById("edit-parent-phone")?.value || "",
        email: document.getElementById("edit-parent-email")?.value || "",
        occupation: document.getElementById("edit-parent-occupation")?.value || "",
        address: document.getElementById("edit-parent-address")?.value || ""
    };

    apiFetch(`/api/parents/${parentId}`, {
        method: "PUT",
        body: payload
    })
    .then(res => {
        showToast(res.message || "Parent updated successfully!", "success");
        closeModal("modal-edit-parent");
        loadParentsData();
    })
    .catch(err => showToast(err.message || "Failed to update parent", "error"));
});

function openLinkStudentModal(parentId, parentName) {
    document.getElementById("link-target-parent-id").value = parentId;
    const nameEl = document.getElementById("link-target-parent-name");
    if (nameEl) nameEl.innerText = parentName;

    const selectEl = document.getElementById("link-student-select");
    if (selectEl) {
        apiFetch("/api/students")
            .then(students => {
                selectEl.innerHTML = `<option value="">— Select Student to Link —</option>` + students.map(s => `
                    <option value="${s.id}">${s.first_name} ${s.last_name} (${s.id} - ${s.class_name || 'Unassigned'})</option>
                `).join("");
            })
            .catch(err => console.error("Error loading students for link modal:", err));
    }

    openModal("modal-link-parent-student");
}

document.getElementById("form-link-parent-student")?.addEventListener("submit", (e) => {
    e.preventDefault();
    const parentId = document.getElementById("link-target-parent-id")?.value;
    const studentId = document.getElementById("link-student-select")?.value;

    if (!parentId || !studentId) {
        showToast("Please select a student to link", "error");
        return;
    }

    apiFetch(`/api/parents/${parentId}/link-student`, {
        method: "POST",
        body: { student_id: studentId }
    })
    .then(res => {
        showToast(res.message || "Student linked to parent successfully!", "success");
        closeModal("modal-link-parent-student");
        loadParentsData();
    })
    .catch(err => showToast(err.message || "Failed to link student", "error"));
});

function unlinkStudentFromParent(parentId, studentId, studentName) {
    if (!confirm(`Are you sure you want to unlink ${studentName} (${studentId}) from this parent record?`)) return;

    apiFetch(`/api/parents/${parentId}/unlink-student/${studentId}`, {
        method: "DELETE"
    })
    .then(res => {
        showToast(res.message || "Student unlinked successfully!", "success");
        loadParentsData();
    })
    .catch(err => showToast(err.message || "Failed to unlink student", "error"));
}

function deleteParent(parentId, parentName) {
    if (!confirm(`Are you sure you want to delete parent record for "${parentName}"? Any linked students will be unlinked.`)) return;

    apiFetch(`/api/parents/${parentId}`, {
        method: "DELETE"
    })
    .then(res => {
        showToast(res.message || "Parent record deleted successfully!", "success");
        loadParentsData();
    })
    .catch(err => showToast(err.message || "Failed to delete parent record", "error"));
}

// --- Support Ticket Functions ---

function loadBranchTickets() {
    apiFetch("/api/support/tickets")
        .then(tickets => {
            const tbody = document.querySelector("#branch-tickets-table tbody");
            if (!tbody) return;
            tbody.innerHTML = "";
            if (!tickets || tickets.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" class="text-center">No support tickets submitted yet. Click "Submit New Support Ticket" if you need help or have a complaint.</td></tr>';
                return;
            }
            tickets.forEach(t => {
                const statusBadge = t.status === "Resolved" ? '<span class="badge badge-success">✓ Resolved</span>' :
                                      t.status === "In Progress" ? '<span class="badge badge-info">In Progress</span>' :
                                      t.status === "Closed" ? '<span class="badge badge-secondary">Closed</span>' :
                                      '<span class="badge badge-warning">Pending Review</span>';

                const priorityBadge = t.priority === "Critical" ? '<span class="badge badge-danger">Critical</span>' :
                                       t.priority === "High" ? '<span class="badge badge-warning">High</span>' :
                                       '<span class="badge badge-branch">' + t.priority + '</span>';

                const adminFeedback = t.admin_response ? 
                    `<div style="font-size:12px; background:rgba(34,197,94,0.1); border-left:3px solid #22c55e; padding:6px 10px; border-radius:4px; margin-top:4px; color:#f8fafc;">
                        <strong>SysAdmin Response (${t.resolved_by || 'Admin'}):</strong><br>${t.admin_response}
                     </div>` : '<em style="font-size:12px; color:var(--text-muted);">No response yet from System Administrator.</em>';

                tbody.innerHTML += `
                    <tr>
                        <td><strong>${t.ticket_number}</strong></td>
                        <td>${t.sender_name} (${t.sender_role})</td>
                        <td style="font-weight:700; color:#f8fafc;">${t.subject}</td>
                        <td>${t.category}</td>
                        <td>${priorityBadge}</td>
                        <td>${statusBadge}</td>
                        <td>${t.created_at}</td>
                        <td>${adminFeedback}</td>
                    </tr>`;
            });
        })
        .catch(err => console.error("Error loading branch tickets:", err));
}

function openCreateTicketModal() {
    const modal = document.getElementById("modal-create-ticket");
    if (modal) modal.style.display = "flex";
}

function closeCreateTicketModal() {
    const modal = document.getElementById("modal-create-ticket");
    if (modal) modal.style.display = "none";
}

document.getElementById("form-create-ticket")?.addEventListener("submit", function(e) {
    e.preventDefault();
    const subject = document.getElementById("ticket-subject").value.trim();
    const category = document.getElementById("ticket-category").value;
    const priority = document.getElementById("ticket-priority").value;
    const description = document.getElementById("ticket-description").value.trim();

    if (!subject || !description) {
        if (typeof showToast === "function") showToast("Subject and description are required", "warning");
        return;
    }

    apiFetch("/api/support/tickets", {
        method: "POST",
        body: JSON.stringify({ subject, category, priority, description })
    })
    .then(res => {
        if (res.status === "success") {
            if (typeof showToast === "function") showToast(res.message || "Support ticket submitted!", "success");
            closeCreateTicketModal();
            document.getElementById("form-create-ticket").reset();
            loadBranchTickets();
        } else {
            if (typeof showToast === "function") showToast(res.message || "Failed to submit ticket", "error");
        }
    })
    .catch(err => {
        if (typeof showToast === "function") showToast(err.message || "Error submitting ticket", "error");
    });
});

function loadSysadminTickets() {
    apiFetch("/api/sysadmin/tickets")
        .then(tickets => {
            const tbody = document.querySelector("#sys-tickets-table tbody");
            if (!tbody) return;
            tbody.innerHTML = "";
            if (!tickets || tickets.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" class="text-center">No branch support tickets found.</td></tr>';
                return;
            }
            tickets.forEach(t => {
                const statusBadge = t.status === "Resolved" ? '<span class="badge badge-success">✓ Resolved</span>' :
                                      t.status === "In Progress" ? '<span class="badge badge-info">In Progress</span>' :
                                      t.status === "Closed" ? '<span class="badge badge-secondary">Closed</span>' :
                                      '<span class="badge badge-warning">Open</span>';

                const priorityBadge = t.priority === "Critical" ? '<span class="badge badge-danger">Critical</span>' :
                                       t.priority === "High" ? '<span class="badge badge-warning">High</span>' :
                                       '<span class="badge badge-branch">' + t.priority + '</span>';

                tbody.innerHTML += `
                    <tr>
                        <td><strong>${t.ticket_number}</strong></td>
                        <td style="font-weight:700; color:#f8fafc;">${t.branch_name}</td>
                        <td>${t.sender_name} (${t.sender_role})</td>
                        <td style="font-weight:700;">${t.subject}</td>
                        <td>${t.category}</td>
                        <td>${priorityBadge}</td>
                        <td>${statusBadge}</td>
                        <td>${t.created_at}</td>
                        <td>
                            <button class="btn btn-sm btn-primary" onclick="openSysResolveTicketModal(${t.id}, '${escapeHtml(t.ticket_number)}', '${escapeHtml(t.branch_name)}', '${escapeHtml(t.sender_name)}', '${escapeHtml(t.description)}', '${t.status}', '${escapeHtml(t.admin_response || '')}')">
                                <i class="fa-solid fa-pen-to-square"></i> Review & Resolve
                            </button>
                        </td>
                    </tr>`;
            });
        })
        .catch(err => console.error("Error loading sysadmin tickets:", err));
}

function openSysResolveTicketModal(id, ticketNum, branchName, senderName, description, status, responseText) {
    document.getElementById("sys-ticket-id").value = id;
    document.getElementById("sys-ticket-info-header").innerHTML = `<strong>Ticket #${ticketNum}</strong> — Branch: <strong>${branchName}</strong> | Sender: <strong>${senderName}</strong>`;
    document.getElementById("sys-ticket-description").value = description;
    document.getElementById("sys-ticket-status").value = status || "Resolved";
    document.getElementById("sys-ticket-response").value = responseText || "";

    const modal = document.getElementById("modal-sys-resolve-ticket");
    if (modal) modal.style.display = "flex";
}

function closeSysResolveTicketModal() {
    const modal = document.getElementById("modal-sys-resolve-ticket");
    if (modal) modal.style.display = "none";
}

document.getElementById("form-sys-resolve-ticket")?.addEventListener("submit", function(e) {
    e.preventDefault();
    const ticketId = document.getElementById("sys-ticket-id").value;
    const status = document.getElementById("sys-ticket-status").value;
    const responseText = document.getElementById("sys-ticket-response").value.trim();

    if (!responseText && (status === "Resolved" || status === "In Progress")) {
        if (typeof showToast === "function") showToast("Resolution response feedback text is required", "warning");
        return;
    }

    apiFetch(`/api/sysadmin/tickets/${ticketId}/resolve`, {
        method: "POST",
        body: JSON.stringify({ status: status, admin_response: responseText })
    })
    .then(res => {
        if (res.status === "success") {
            if (typeof showToast === "function") showToast(res.message || "Ticket updated successfully!", "success");
            closeSysResolveTicketModal();
            loadSysadminTickets();
        } else {
            if (typeof showToast === "function") showToast(res.message || "Failed to update ticket", "error");
        }
    })
    .catch(err => {
        if (typeof showToast === "function") showToast(err.message || "Error updating ticket", "error");
    });
});

