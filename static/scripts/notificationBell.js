(() => {
    const bell = document.getElementById('notificationBell');
    const dropdown = document.getElementById('notificationsDropdown');
    const countBadge = document.getElementById('notificationCount');
    const markAllBtn = document.getElementById('markAllReadBtn');
    const clearAllBtn = document.getElementById('clearAllBtn');

    function toggleDropdown() {
        dropdown.classList.toggle('active');
    }

    function updateBadgeCount(newCount) {
        if (newCount > 0) {
            if (countBadge) {
                countBadge.textContent = newCount;
            } else {
                // Create badge if missing
                const badge = document.createElement('span');
                badge.id = 'notificationCount';
                badge.className = 'notification-count';
                badge.textContent = newCount;
                bell.appendChild(badge);
            }
        } else {
            if (countBadge) countBadge.remove();
        }
    }

    function markAsRead(notificationItem) {
        if (notificationItem.classList.contains('unread')) {
            notificationItem.classList.remove('unread');
            let count = countBadge ? parseInt(countBadge.textContent) : 0;
            updateBadgeCount(count - 1);
            const notificationId = notificationItem.dataset.id;
            fetch('/notifications/mark-as-read/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: `notification_id=${notificationId}`
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) console.error('Failed to mark notification as read:', data.error);
            })
            .catch(error => console.error('Error marking notification as read:', error));
        }
    }

    function markAllRead() {
        const unreadItems = dropdown.querySelectorAll('.notification-item.unread');
        if (unreadItems.length === 0) return;
        const ids = Array.from(unreadItems).map(item => item.dataset.id);
        unreadItems.forEach(item => item.classList.remove('unread'));
        updateBadgeCount(0);
        fetch('/notifications/mark-all-read/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ notification_ids: ids })
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) console.error('Failed to mark all notifications as read:', data.error);
        })
        .catch(error => console.error('Error marking all notifications as read:', error));
    }

    function clearAll() {
        const container = document.getElementById('notificationsContainer');
        dropdown.querySelectorAll('.notification-item').forEach(item => item.remove());
        const noMsg = document.createElement('div');
        noMsg.className = 'notification-item no-notifications';
        noMsg.id = 'noNotificationsMsg';
        noMsg.textContent = 'No notifications.';
        container.appendChild(noMsg);
        updateBadgeCount(0);
        fetch('/notifications/clear-all/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            }
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) console.error('Failed to clear notifications:', data.error);
        })
        .catch(error => console.error('Error clearing notifications:', error));
    }

    // **Add stopPropagation here!**
    bell.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleDropdown();
    });

    // Also prevent clicks inside dropdown from bubbling up
    dropdown.addEventListener('click', (e) => {
        e.stopPropagation();
    });

    document.addEventListener('click', () => {
        dropdown.classList.remove('active');
    });

    bell.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            toggleDropdown();
        }
    });

    dropdown.querySelectorAll('.notification-item').forEach(item => {
        if (!item.classList.contains('no-notifications')) {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                markAsRead(item);
            });
        }
    });

    markAllBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        markAllRead();
    });

    clearAllBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        clearAll();
    });

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
})();
