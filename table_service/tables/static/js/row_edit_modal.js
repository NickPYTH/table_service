document.addEventListener('DOMContentLoaded', function() {
    const addRowBtn = document.getElementById('add-row-btn');
    if (addRowBtn) {
        // Обработчик кнопки добавления строки
        document.getElementById('add-row-btn').addEventListener('click', function (e) {
            e.preventDefault();

            const modal = new bootstrap.Modal(document.getElementById('addRowModal'));

            // Загрузка формы
            fetch(this.href, {
                headers: {'X-Requested-With': 'XMLHttpRequest'}
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        document.getElementById('addRowModalContent').innerHTML = data.html;
                        modal.show();
                    }
                });
        })
    }
    // Обработка отправки формы добавления
    document.addEventListener('submit', function(e) {
    if (e.target && e.target.id === 'addRowForm') {
        e.preventDefault();
        const form = e.target;

        fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if(data.status === 'success') {
                bootstrap.Modal.getInstance(document.getElementById('addRowModal')).hide();
                window.location.reload(); // Обновляем таблицу
            } else {
                // Показываем ошибки валидации
                document.getElementById('addRowModalContent').innerHTML = data.html;
                }
            });
        }
    });
    // Обработчик кнопки редактирования
    document.addEventListener('click', function(e) {
        if (e.target.closest('.edit-row-btn')) {
            const btn = e.target.closest('.edit-row-btn');
            const rowId = btn.dataset.rowId;
            const tableId = btn.dataset.tableId;

            // Показываем модальное окно сразу
            const modal = new bootstrap.Modal(document.getElementById('rowEditModal'));
            modal.show();

            // Загрузка формы
            fetch(`/${tableId}/edit_row/${rowId}/`)
                .then(response => response.json())
                .then(data => {
                    if(data.status === 'success') {
                        document.getElementById('modalContent').innerHTML = data.html;
                    } else {
                        alert('Ошибка загрузки формы');
                        modal.hide();
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    modal.hide();
                });
        }
    });

    // Обработка отправки формы
    document.addEventListener('submit', function(e) {
        if (e.target && e.target.id === 'rowEditForm') {
            e.preventDefault();
            const form = e.target;
            const submitBtn = form.querySelector('button[type="submit"]');

            // Блокируем кнопку на время отправки
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Сохранение...';

            fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if(data.status === 'success') {
                    bootstrap.Modal.getInstance(document.getElementById('rowEditModal')).hide();
                    window.location.reload(); // Или обновление только строки
                } else {
                    alert('Ошибка сохранения: ' + (data.message || 'Неизвестная ошибка'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Ошибка соединения');
            })
            .finally(() => {
                submitBtn.disabled = false;
                submitBtn.textContent = 'Сохранить';
            });
        }
    });
});