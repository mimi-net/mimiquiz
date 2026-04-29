async function fetchWithAuth(url, options = {}) {
    let response = await fetch(url, { ...options, credentials: 'include' });

    if (response.status === 401) {
        // Пытаемся обновить через обычный refresh endpoint
        const refreshRes = await fetch('/refresh', {
            method: 'POST',
            credentials: 'include',
            // Если используется CSRF защита для refresh, нужно добавить заголовок
        });

        if (refreshRes.ok) {
            // Токены обновлены, повторяем исходный запрос
            response = await fetch(url, { ...options, credentials: 'include' });
        } else {
            // Обычный refresh не сработал – пробуем обновить через сессию
            const sessionRefreshRes = await fetch('/refresh-from-session', {
                method: 'POST',
                credentials: 'include'
            });

            if (sessionRefreshRes.ok) {
                // Токены обновлены через сессию, повторяем исходный запрос
                response = await fetch(url, { ...options, credentials: 'include' });
            } else {
                // Всё плохо – перенаправляем на страницу входа
                window.location.href = '/login';
                return;
            }
        }
    }
    return response;
}