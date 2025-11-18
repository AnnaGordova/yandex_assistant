// ===== УТИЛИТЫ =====

// Форматирование цены
export function formatPrice(price) {
    return new Intl.NumberFormat('ru-RU').format(price) + ' ₽';
}

// Форматирование времени
export function formatTime() {
    const now = new Date();
    return now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}

// Генерация звезд рейтинга
export function generateStars(rating) {
    const fullStars = Math.floor(rating);
    const emptyStars = 5 - fullStars;
    return '★'.repeat(fullStars) + '☆'.repeat(emptyStars);
}

// ===== РАБОТА С ТОКЕНАМИ =====

// Сохранение токена
export function saveToken(token) {
    localStorage.setItem('authToken', token);
}

// Получение токена
export function getToken() {
    return localStorage.getItem('authToken');
}

// Удаление токена
export function removeToken() {
    localStorage.removeItem('authToken');
}

// ===== ВАЛИДАЦИЯ =====

// Валидация пароля
export function validatePassword(password) {
    if (password.length < 8) {
        return 'Пароль должен содержать минимум 8 символов';
    }
    if (!/[A-Z]/.test(password)) {
        return 'Пароль должен содержать хотя бы одну заглавную букву';
    }
    if (!/[a-z]/.test(password)) {
        return 'Пароль должен содержать хотя бы одну строчную букву';
    }
    if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
        return 'Пароль должен содержать хотя бы один специальный символ (!@#$%^&* и т.д.)';
    }
    return null;
}

// Хеширование пароля (SHA-256)
export async function hashPassword(password) {
    const encoder = new TextEncoder();
    const data = encoder.encode(password);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    return hashHex;
}

// ===== ИНИЦИАЛИЗАЦИЯ ТАБОВ =====

export function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.getAttribute('data-tab');

            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(`tab-${tabName}`).classList.add('active');
        });
    });
}
