import re
from tables.models import Cell, Row, Column, Table
import datetime


def column_letters_to_number(letters):
    result = 0
    for char in letters:
        result = result * 26 + (ord(char) - ord('A') + 1)
    return result


def get_cell_value(cell_ref, table_id):
    """Получает числовое значение ячейки по ссылке"""
    try:
        col_letters = re.match(r'([A-Z]+)(\d+)', cell_ref).group(1)
        row_num = int(re.match(r'([A-Z]+)(\d+)', cell_ref).group(2)) - 1

        col_num = column_letters_to_number(col_letters)
        table = Table.objects.get(id=table_id)

        cell_row = Row.objects.get(table=table, order=row_num)
        cell_column = Column.objects.get(table=table, order=col_num)
        cell = Cell.objects.filter(
            table_id=table_id,
            row=cell_row.id,
            column=cell_column.id
        ).first()

        if cell and cell.value:
            try:
                return float(cell.value)
            except (ValueError, TypeError):
                try:
                    return float(datetime.datetime.strptime(cell.value, "%d.%m.%Y").timestamp())
                except (ValueError, TypeError):
                    return 0
        return 0
    except Exception as e:
        print(f"Ошибка получения ячейки {cell_ref}: {e}")
        return 0


def evaluate_comparison(left, operator, right):
    """Вычисляет результат сравнения"""
    if operator == '>':
        return left > right
    elif operator == '<':
        return left < right
    elif operator == '>=':
        return left >= right
    elif operator == '<=':
        return left <= right
    elif operator == '=':
        return abs(left - right) < 1e-10  # Сравнение с плавающей точкой
    elif operator == '<>':
        return abs(left - right) > 1e-10
    else:
        raise ValueError(f"Неизвестный оператор сравнения: {operator}")


def evaluate_function(func_name, arguments, table_id):
    """Вычисляет значение функции"""
    func_name = func_name.upper()

    if func_name == 'СУММ':
        total = 0
        for arg in arguments:
            if isinstance(arg, (int, float)):
                total += arg
            else:
                total += get_cell_value(arg, table_id)
        return total

    elif func_name == 'ЕСЛИ':
        if len(arguments) != 3:
            raise ValueError("Функция ЕСЛИ требует 3 аргумента")

        condition, true_value, false_value = arguments

        print(f"ЕСЛИ: условие={condition}, тип={type(condition)}")  # Отладка

        # Если условие - булево значение
        if isinstance(condition, bool):
            return true_value if condition else false_value
        # Если условие - число (0 = ложь, не 0 = истина)
        elif isinstance(condition, (int, float)):
            return true_value if condition != 0 else false_value
        else:
            # Если условие - строка (для текстовых сравнений)
            return true_value if condition else false_value

    else:
        raise ValueError(f"Неизвестная функция: {func_name}")


def parse_arguments(arg_tokens, table_id):
    """Разбирает и вычисляет аргументы функции"""
    arguments = []
    current_arg = []

    for token in arg_tokens:
        if token == ';':
            if current_arg:
                # Вычисляем значение аргумента
                arg_value = evaluate_expression(current_arg, table_id)
                arguments.append(arg_value)
                current_arg = []
        else:
            current_arg.append(token)

    if current_arg:
        arg_value = evaluate_expression(current_arg, table_id)
        arguments.append(arg_value)

    return arguments


def evaluate_expression(tokens, table_id):
    """Рекурсивно вычисляет выражение с учетом скобок, приоритетов и функций"""
    values = []
    operators = []

    i = 0
    while i < len(tokens):
        token = tokens[i]

        if token == '(':
            # Находим закрывающую скобку
            depth = 1
            j = i + 1
            while j < len(tokens) and depth > 0:
                if tokens[j] == '(':
                    depth += 1
                elif tokens[j] == ')':
                    depth -= 1
                j += 1

            # Рекурсивно вычисляем выражение в скобках
            sub_expression = tokens[i + 1:j - 1]
            result = evaluate_expression(sub_expression, table_id)
            values.append(result)
            i = j
            continue

        elif re.match(r'^[A-ZА-Я]{2,}\($', token):  # Функция (2+ буквы + скобка)
            func_name = token[:-1]  # Убираем открывающую скобку

            # Находим закрывающую скобку функции
            depth = 1
            j = i + 1
            args_tokens = []

            while j < len(tokens) and depth > 0:
                if tokens[j] == '(':
                    depth += 1
                elif tokens[j] == ')':
                    depth -= 1

                if depth > 0:  # Не включаем внешнюю закрывающую скобку
                    args_tokens.append(tokens[j])

                j += 1

            # Разбираем аргументы функции
            arguments = parse_arguments(args_tokens, table_id)

            # Вычисляем функцию
            result = evaluate_function(func_name, arguments, table_id)
            values.append(result)
            i = j
            continue

        elif token.isdigit():
            values.append(float(token))

        elif re.match(r'[A-Z]+\d+', token):  # Ячейка
            value = get_cell_value(token, table_id)
            values.append(value)

        elif token in ['+', '-', '*', '/']:  # Арифметические операторы
            operators.append(token)

        elif token in ['>', '<', '>=', '<=', '=', '<>']:  # Операторы сравнения
            operators.append(token)

        i += 1

    # Сначала обрабатываем операторы сравнения
    i = 0
    while i < len(operators):
        if operators[i] in ['>', '<', '>=', '<=', '=', '<>']:
            if i + 1 >= len(values):
                raise ValueError("Недостаточно операндов для оператора сравнения")

            left = values[i]
            right = values[i + 1]
            operator = operators[i]

            result = evaluate_comparison(left, operator, right)

            # Заменяем два значения на результат сравнения (булево значение)
            values[i] = result
            del values[i + 1]
            del operators[i]
        else:
            i += 1

    # Затем обрабатываем умножение и деление
    i = 0
    while i < len(operators):
        if operators[i] in ['*', '/']:
            left = values[i]
            right = values[i + 1]

            if operators[i] == '*':
                result = left * right
            else:  # '/'
                if right == 0:
                    raise ValueError("Деление на ноль")
                result = left / right

            values[i] = result
            del values[i + 1]
            del operators[i]
        else:
            i += 1

    # Затем обрабатываем сложение и вычитание
    if not values:
        return 0

    result = values[0]
    for i in range(len(operators)):
        if operators[i] == '+':
            result += values[i + 1]
        elif operators[i] == '-':
            result -= values[i + 1]

    return result


def calculate_formula(cell):
    try:
        formula = re.sub(r'\s+', '', cell.value.upper())

        if not formula.startswith('='):
            cell.formula_value = "Ошибка: формула должна начинаться с ="
            cell.save()
            return

        formula_content = formula[1:]

        # Обновленное регулярное выражение с операторами сравнения
        tokens = re.findall(
            r'[A-ZА-Я]{2,}\(|'  # Функции (минимум 2 буквы + скобка)
            r'>=|<=|<>|>|<|=|'  # Операторы сравнения (должны быть первыми!)
            r'\d+|'  # Числа
            r'[A-Z]+\d+|'  # Ячейки
            r'[\+\-\*\/\(\)]|;',  # Операторы, скобки и разделители
            formula_content
        )

        print(f"Разобранные токены: {tokens}")  # Для отладки

        if not tokens:
            cell.formula_value = "Ошибка: неверный формат формулы"
            cell.save()
            return

        try:
            result = evaluate_expression(tokens, cell.table_id)

            # Сохраняем результат
            if isinstance(result, (int, float)):
                if result.is_integer():
                    cell.formula_value = str(int(result))
                else:
                    cell.formula_value = str(round(result, 4))
            elif isinstance(result, bool):
                cell.formula_value = "ИСТИНА" if result else "ЛОЖЬ"
            else:
                cell.formula_value = "Ошибка: неверный тип результата"

        except ValueError as e:
            cell.formula_value = f"Ошибка: {str(e)}"
        except Exception as e:
            cell.formula_value = f"Ошибка вычисления: {str(e)}"
            print(f"Детальная ошибка вычисления: {e}")

        cell.save()

    except Exception as e:
        print(f"Ошибка при вычислении формулы: {e}")
        cell.formula_value = "Ошибка вычисления"
        cell.save()