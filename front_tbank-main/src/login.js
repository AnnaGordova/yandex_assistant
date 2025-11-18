// ===== ИМПОРТЫ =====
import { validatePassword, hashPassword, saveToken, removeToken } from './utils.js';

// ===== ФУНКЦИИ АВТОРИЗАЦИИ =====

// Вход в систему
export async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    const errorEl = document.getElementById('loginError');
    const successEl = document.getElementById('loginSuccess');
    
    // Очищаем сообщения
    if (errorEl) errorEl.classList.remove('show');
    if (successEl) successEl.classList.remove('show');
    
    // Валидация
    if (!email || !password) {
        if (errorEl) {
            errorEl.textContent = 'Заполните все поля';
            errorEl.classList.add('show');
        }
        return;
    }
    
    try {
        // Хешируем пароль
        const hashedPassword = await hashPassword(password);
        
        // Отправка запроса на бэкенд
        const response = await fetch('http://localhost:3110/backend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'action': 'handleLogin'
            },
            body: JSON.stringify({
                email: email,
                password: hashedPassword
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Успех
            if (successEl) {
                successEl.textContent = 'Вход выполнен успешно! Перенаправление...';
                successEl.classList.add('show');
            }
            
            // Сохраняем токен
            saveToken(data.token);
            
            // Перенаправление
            setTimeout(() => {
                window.location.href = '/html/chat.html';
            }, 1500);
        } else {
            // Ошибка от сервера
            if (errorEl) {
                errorEl.textContent = data.message || 'Ошибка входа';
                errorEl.classList.add('show');
            }
        }
    } catch (error) {
        // Ошибка сети
        if (errorEl) {
            errorEl.textContent = 'Ошибка соединения с сервером';
            errorEl.classList.add('show');
        }
        console.error('Login error:', error);
    }
}

// Регистрация
export async function handleRegister(e) {
    e.preventDefault();
    const email = document.getElementById('registerEmail').value.trim();
    const password = document.getElementById('registerPassword').value;
    const passwordConfirm = document.getElementById('registerPasswordConfirm').value;
    const errorEl = document.getElementById('registerError');
    const successEl = document.getElementById('registerSuccess');
    
    // Очищаем сообщения
    if (errorEl) errorEl.classList.remove('show');
    if (successEl) successEl.classList.remove('show');
    
    // Валидация
    if (!email || !password || !passwordConfirm) {
        if (errorEl) {
            errorEl.textContent = 'Заполните все обязательные поля';
            errorEl.classList.add('show');
        }
        return;
    }
    
    // Валидация пароля
    const passwordError = validatePassword(password);
    if (passwordError) {
        if (errorEl) {
            errorEl.textContent = passwordError;
            errorEl.classList.add('show');
        }
        return;
    }
    
    // Проверка совпадения паролей
    if (password !== passwordConfirm) {
        if (errorEl) {
            errorEl.textContent = 'Пароли не совпадают';
            errorEl.classList.add('show');
        }
        return;
    }
    
    try {
        // Хешируем пароль
        const hashedPassword = await hashPassword(password);
        // Отправка запроса на бэкенд
        const response = await fetch('http://localhost:3110/backend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'action': 'handleRegister'
            },
            body: JSON.stringify({
                email: email,
                password: hashedPassword
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Успех
            if (successEl) {
                successEl.textContent = 'Регистрация успешна! Перенаправление...';
                successEl.classList.add('show');
            }
            
            // Сохраняем токен
            saveToken(data.token);
            
            // Перенаправление
            setTimeout(() => {
                window.location.href = '/html/chat.html';
            }, 1500);
        } else {
            // Ошибка от сервера
            if (errorEl) {
                errorEl.textContent = data.message || 'Ошибка регистрации';
                errorEl.classList.add('show');
            }
        }
    } catch (error) {
        // Ошибка сети
        if (errorEl) {
            errorEl.textContent = 'Ошибка соединения с сервером';
            errorEl.classList.add('show');
        }
        console.error('Registration error:', error);
    }
}

// ===== ВОССТАНОВЛЕНИЕ ПАРОЛЯ =====

// Запрос на сброс пароля
export async function handlePasswordResetRequest(e) {
    e.preventDefault();
    if(token){
        removeToken();
    }
    const email = document.getElementById('resetEmail').value.trim();
    const errorEl = document.getElementById('resetError');
    const successEl = document.getElementById('resetSuccess');
    
    // Очищаем сообщения
    if (errorEl) errorEl.classList.remove('show');
    if (successEl) successEl.classList.remove('show');
    
    // Валидация email
    if (!email) {
        if (errorEl) {
            errorEl.textContent = 'Введите email';
            errorEl.classList.add('show');
        }
        return;
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        if (errorEl) {
            errorEl.textContent = 'Введите корректный email';
            errorEl.classList.add('show');
        }
        return;
    }
    
    try {
        // Отправка запроса
        const response = await fetch('http://localhost:3110/backend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'action': 'resetPassword'
            },
            body: JSON.stringify({
                email: email
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Успех
            if (successEl) {
                successEl.textContent = 'Ссылка для сброса пароля отправлена на ваш email';
                successEl.classList.add('show');
            }
            
            document.getElementById('resetEmail').value = '';
            setTimeout(() => {
                window.location.href = '/html/login.html';
            }, 3000);
        } else {
            // Ошибка
            if (errorEl) {
                errorEl.textContent = data.message || 'Ошибка при отправке запроса';
                errorEl.classList.add('show');
            }
        }
    } catch (error) {
        if (errorEl) {
            errorEl.textContent = 'Ошибка соединения с сервером';
            errorEl.classList.add('show');
        }
        console.error('Password reset request error:', error);
    }
}

// Установка нового пароля
export async function handlePasswordChange(e) {
    e.preventDefault();
    if(token){
        removeToken();
    }
    const email = document.getElementById('changeEmail').value.trim();
    const password = document.getElementById('changePassword').value;
    const passwordConfirm = document.getElementById('changePasswordConfirm').value;
    const errorEl = document.getElementById('changeError');
    const successEl = document.getElementById('changeSuccess');
    
    // Очищаем сообщения
    if (errorEl) errorEl.classList.remove('show');
    if (successEl) successEl.classList.remove('show');
    
    // Валидация
    if (!email || !password || !passwordConfirm) {
        if (errorEl) {
            errorEl.textContent = 'Заполните все поля';
            errorEl.classList.add('show');
        }
        return;
    }
    
    // Валидация email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        if (errorEl) {
            errorEl.textContent = 'Введите корректный email';
            errorEl.classList.add('show');
        }
        return;
    }
    
    // Валидация пароля
    const passwordError = validatePassword(password);
    if (passwordError) {
        if (errorEl) {
            errorEl.textContent = passwordError;
            errorEl.classList.add('show');
        }
        return;
    }
    
    // Проверка совпадения
    if (password !== passwordConfirm) {
        if (errorEl) {
            errorEl.textContent = 'Пароли не совпадают';
            errorEl.classList.add('show');
        }
        return;
    }
    
    try {
        // Получаем токен из URL
        const urlParams = new URLSearchParams(window.location.search);
        const resetToken = urlParams.get('token');
        /*
        if (!resetToken) {
            if (errorEl) {
                errorEl.textContent = 'Недействительная ссылка для сброса пароля';
                errorEl.classList.add('show');
            }
            return;
        }*/
        
        // Хешируем пароль
        const hashedPassword = await hashPassword(password);
        // Отправка запроса
        const response = await fetch('http://localhost:3110/backend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'action': 'changePassword'
            },
            body: JSON.stringify({
                email: email,
                token: resetToken,
                password: hashedPassword
            })
        });
        const data = await response.json();
        
        if (response.ok) {
            // Успех
            if (successEl) {
                successEl.textContent = 'Пароль успешно изменён! Перенаправление...';
                successEl.classList.add('show');
            }
            
            // Очищаем поля
            document.getElementById('changeEmail').value = '';
            document.getElementById('changePassword').value = '';
            document.getElementById('changePasswordConfirm').value = '';
            
            setTimeout(() => {
                window.location.href = '/html/login.html';
            }, 2000);
        } else {
            // Ошибка
            if (errorEl) {
                errorEl.textContent = data.message || 'Ошибка при изменении пароля';
                errorEl.classList.add('show');
            }
        }
    } catch (error) {
        if (errorEl) {
            errorEl.textContent = 'Ошибка соединения с сервером';
            errorEl.classList.add('show');
        }
        console.error('Password change error:', error);
    }
}

// ===== ИНИЦИАЛИЗАЦИЯ =====

export function initAuth() {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const resetForm = document.getElementById('resetPasswordForm');
    const changeForm = document.getElementById('changePasswordForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
    
    if (resetForm) {
        resetForm.addEventListener('submit', handlePasswordResetRequest);
    }
    
    if (changeForm) {
        changeForm.addEventListener('submit', handlePasswordChange);
    }
}

// Инициализируем при загрузке страницы
document.addEventListener('DOMContentLoaded', initAuth);
