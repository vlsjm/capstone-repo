(() => {
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                cookie = cookie.trim();
                if (cookie.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Initialize notification bell (works for both mobile and desktop)
    function initNotificationBell(config) {
        const bell = document.getElementById(config.bellId);
        const dropdown = document.getElementById(config.dropdownId);
        const markAllBtn = config.markAllBtnSelector.startsWith('.')
            ? document.querySelector(config.markAllBtnSelector)
            : document.getElementById(config.markAllBtnSelector);
        const clearAllBtn = config.clearAllBtnSelector.startsWith('.')
            ? document.querySelector(config.clearAllBtnSelector)
            : document.getElementById(config.clearAllBtnSelector);

        if (!bell || !dropdown) return;

        function updateBadgeCount(newCount) {
            // Update both mobile and desktop badges
            const mobileBadge = document.getElementById('notificationCount');
            const desktopBadge = document.getElementById('notificationCountDesktop');

            [mobileBadge, desktopBadge].forEach(badge => {
                if (badge) {
                    const bellWrapper = badge.closest('.notification-container');
                    if (newCount > 0) {
                        badge.textContent = newCount;
                    } else {
                        badge.remove();
                    }
                }
            });

            // Create badge if missing and count > 0
            if (newCount > 0) {
                ['notificationBell', 'notificationBellDesktop'].forEach(bellId => {
                    const bellElement = document.getElementById(bellId);
                    if (bellElement && !bellElement.querySelector('.notification-count')) {
                        const badge = document.createElement('span');
                        badge.id = bellId === 'notificationBell' ? 'notificationCount' : 'notificationCountDesktop';
                        badge.className = 'notification-count';
                        badge.textContent = newCount;
                        bellElement.appendChild(badge);
                    }
                });
            }
        }

        function markAllRead() {
            // Get unread items from both mobile and desktop dropdowns
            const mobileDropdown = document.getElementById('notificationsDropdown');
            const desktopDropdown = document.getElementById('notificationsDropdownDesktop');

            const mobileUnread = mobileDropdown ? mobileDropdown.querySelectorAll('.notification-item.unread') : [];
            const desktopUnread = desktopDropdown ? desktopDropdown.querySelectorAll('.notification-item.unread') : [];
            const allUnread = [...mobileUnread, ...desktopUnread];

            if (allUnread.length === 0) return;

            const ids = Array.from(allUnread).map(item => item.dataset.id);

            // Update UI immediately for both dropdowns
            allUnread.forEach(item => {
                item.classList.remove('unread');
                const unreadIndicator = item.querySelector('.unread-indicator');
                if (unreadIndicator) unreadIndicator.remove();
            });

            updateBadgeCount(0);

            // Send request to backend
            fetch('/mark-all-notifications-read/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({ notification_ids: ids })
            })
                .then(response => response.json())
                .then(data => {
                    if (!data.success) {
                        console.error('Failed to mark all notifications as read:', data.error);
                        location.reload();
                    }
                })
                .catch(error => {
                    console.error('Error marking all notifications as read:', error);
                    location.reload();
                });
        }

        function clearAll() {
            const mobileContainer = document.getElementById('notificationsContainer');
            const desktopContainer = document.querySelector('.desktop-notifications-body');

            const noMsgHTML = `
                <div class="empty-state">
                    <i class="fas fa-bell-slash"></i>
                    <p>No notifications</p>
                </div>
            `;

            // Clear mobile notifications
            if (mobileContainer) {
                const mobileItems = mobileContainer.querySelectorAll('.notification-item');
                mobileItems.forEach(item => item.remove());

                const noMsg = document.createElement('div');
                noMsg.className = 'notification-item no-notifications';
                noMsg.id = 'noNotificationsMsg';
                noMsg.innerHTML = noMsgHTML;
                mobileContainer.appendChild(noMsg);
            }

            // Clear desktop notifications
            if (desktopContainer) {
                const desktopItems = desktopContainer.querySelectorAll('.notification-item');
                desktopItems.forEach(item => item.remove());

                const noMsg = document.createElement('div');
                noMsg.className = 'notification-item no-notifications';
                noMsg.innerHTML = noMsgHTML;
                desktopContainer.appendChild(noMsg);
            }

            updateBadgeCount(0);

            // Send request to backend
            fetch('/clear-all-notifications/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                }
            })
                .then(response => response.json())
                .then(data => {
                    if (!data.success) {
                        console.error('Failed to clear notifications:', data.error);
                        location.reload();
                    }
                })
                .catch(error => {
                    console.error('Error clearing notifications:', error);
                    location.reload();
                });
        }

        // Bell click handler - toggle dropdown
        bell.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdown.classList.toggle('active');
        });

        // Prevent clicks inside dropdown from bubbling
        dropdown.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!bell.contains(e.target) && !dropdown.contains(e.target)) {
                dropdown.classList.remove('active');
            }
        });

        // Keyboard support
        bell.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                dropdown.classList.toggle('active');
            }
        });

        // Event listeners for action buttons
        if (markAllBtn) {
            markAllBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                markAllRead();
            });
        }

        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                clearAll();
            });
        }
    }

    // Initialize mobile notification bell
    initNotificationBell({
        bellId: 'notificationBell',
        dropdownId: 'notificationsDropdown',
        markAllBtnSelector: 'markAllReadBtn',
        clearAllBtnSelector: 'clearAllBtn'
    });

    // Initialize desktop notification bell  
    initNotificationBell({
        bellId: 'notificationBellDesktop',
        dropdownId: 'notificationsDropdownDesktop',
        markAllBtnSelector: '.desktop-mark-all',
        clearAllBtnSelector: '.desktop-clear-all'
    });

    // Handle three-dot actions menu (for both mobile and desktop)
    const actionsToggles = document.querySelectorAll('.actions-toggle, .desktop-actions-toggle, #actionsToggle');
    actionsToggles.forEach(toggle => {
        const actionsDropdown = toggle.nextElementSibling;
        if (actionsDropdown && actionsDropdown.classList.contains('actions-dropdown')) {
            toggle.addEventListener('click', function (e) {
                e.stopPropagation();
                actionsDropdown.classList.toggle('active');
            });

            // Close actions dropdown when clicking outside
            document.addEventListener('click', function (e) {
                if (!toggle.contains(e.target) && !actionsDropdown.contains(e.target)) {
                    actionsDropdown.classList.remove('active');
                }
            });

            // Close actions dropdown when an action is clicked
            actionsDropdown.addEventListener('click', function () {
                actionsDropdown.classList.remove('active');
            });
        }
    });
})();
