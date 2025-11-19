import os
import sys
import time
import traceback

import pytest
from loguru import logger

from pages.main_page import MainPage
from pages.transaction_log_page import TransactionLogePage
from pages.sub_operation_log_page import SubPayOutOperationLogPage
from api.api_client import ApiClient
from utils.sql_client import SQL
from utils.ui_actions import UIActions
from utils.testrail_client import TestRail
from utils.data import TestsData, TestConfig


test_case_id = 'TC_DEMO_001'


@logger.catch(reraise=True)
def test(browser, add_logger):

    add_logger.info('ЕСТЬ БАГ: https://example.com/issue')
    status = 6
    comment = 'Test skipped'
    test_case_id = 'TC_DEMO_001'
    response = TestRail.add_test_result_with_attachment(...)
    add_logger.info(f'Добавили результат записи в TestRail: {response}')
    pytest.skip('Test skipped')

    os.environ['test_case_id'] = 'TC_DEMO_001'
    os.environ['assignedto_id'] = '48'

    main = MainPage(browser, add_logger)
    transaction_log = TransactionLogePage(browser, add_logger)
    sub_log = SubPayOutOperationLogPage(browser, add_logger)
    user = TestsData.user_demo
    sql = SQL()
    api = ApiClient()

    main.login(user)

    currency_exp = 'XXX'

    merchant = {'name': 'DEMO_MERCHANT', 'secret': 'DEMO_SECRET'}

    add_logger.info('Определяем имя оператора')
    code_name = 'operator_demo'
    operator_name = 'Operator Demo'
    name = sql.get_executor_name(add_logger, code_name)
    add_logger.info(f'Имя оператора: {name}')

    try:
        add_logger.info('Устанавливаем способ получения статуса')
        mode, browser, add_logger = api.check_status_mode(browser, add_logger, operator_name)

        if mode == 'webhook':
            add_logger.info('Webhook включен.')
        if mode == 'api_check':
            add_logger.info('API check включен. Меняем на Webhook')
            UIActions.set_webhook_mode(browser)
        if mode == 'error':
            add_logger.info('Некорректная конфигурация статусов.')

        add_logger.info('Создаём транзакцию')
        callback_url, callback_id = api.create_callback()
        response = api.create_payout(merchant['secret'], callback_url)

        add_logger.info('Проверяем параметры в ответе')
        add_logger.info(response)
        data = api.parse_payout_response(response)
        internal_id = data.get("internal_id")

        add_logger.info(f'iternal_id транзакции: {internal_id}')

        add_logger.info('Открываем Operations log')
        main.move_to_menu('operations_log')
        UIActions.click(browser, 'operations_log')

        add_logger.info('Открываем Transaction log')
        UIActions.click(browser, 'transaction_log')

        add_logger.info('Отправляем транзакцию исполнителю')
        transaction_log.send_transaction(internal_id, name)

        browser.refresh()
        add_logger.info('Проверяем статус')
        main.reset_filter()
        UIActions.send_text(browser, 'internal_id_filter', internal_id)
        transaction_log.click_search()
        current_status = main.get_text('status_row0')
        add_logger.info(f'Status == {current_status}')
        assert current_status == 'STATUS_API'

        add_logger.info('Запоминаем transaction_id')
        transaction_id = main.get_text('transaction_id_row0')

        add_logger.info('Запоминаем amount')
        amount_str = str(main.get_text('amount_row0')).replace(' ', '')

        add_logger.info('Проверяем Currency')
        currency = main.get_text('currency_row0')
        assert currency == currency_exp

        add_logger.info('Получаем operator payment id')
        payment_id = sql.get_payment_id(add_logger, internal_id)
        add_logger.info(f'Payment id: {payment_id}')

        add_logger.info('Меняем статус на Success через mock')
        response_change_status = api.set_status(payment_id=payment_id, status='success')

        add_logger.info('Проверяем параметры ответа')
        payment_id_mock = sql.get_mock_payment_id(add_logger, payment_id)
        api.check_change_status(response_change_status, payment_id_mock, 'PAID')
        time.sleep(5)

        main.go_to_transaction_log()
        main.reset_filter()
        UIActions.send_text(browser, 'internal_id_filter', internal_id)
        transaction_log.click_search()
        transaction_log.wait_table_load()

        add_logger.info('Проверяем статус в Transaction log')
        time.sleep(2)
        status_tr_log = main.get_text('status_row0')
        add_logger.info(f'Success == {status_tr_log}')
        assert status_tr_log == 'Success'

        main.go_to_sub_operations()
        sub_log.wait_table_load()
        main.send_text('transaction_id_filter', transaction_id)
        sub_log.wait_table_load()

        add_logger.info('Проверяем статус в Sub operation log')
        status_sub_pay_out = main.get_text('sub_status_row0')
        add_logger.info(f'Success == {status_sub_pay_out}')
        assert status_sub_pay_out == 'Success'

        add_logger.info('Проверяем саб-транзакцию')
        main.click('sub_expand_row0')
        time.sleep(1)
        status_sub_tr = main.get_text('sub_status_row0_sub')
        add_logger.info(f'Success == {status_sub_tr}')
        assert status_sub_tr == 'Success'

        add_logger.info('Проверяем полученный webhook')
        webhook = api.get_callback(callback_id)
        api.check_callback(webhook, 'success', transaction_id, amount_str, currency_exp)

        add_logger.info('Меняем статус на Fail через mock')
        response_change_status = api.set_status(payment_id=payment_id, status='fail')

        add_logger.info('Проверяем параметры ответа')
        payment_id_mock = sql.get_mock_payment_id(add_logger, payment_id)
        api.check_change_status(response_change_status, payment_id_mock, 'CANCELED')
        time.sleep(5)

        main.go_to_transaction_log()
        main.reset_filter()
        UIActions.send_text(browser, 'internal_id_filter', internal_id)
        transaction_log.click_search()

        add_logger.info('Проверяем статус в Transaction log')
        status_tr_log = main.get_text('status_row0')
        add_logger.info(f'Success == {status_tr_log}')
        assert status_tr_log == 'Success'

        main.go_to_sub_operations()
        sub_log.wait_table_load()
        main.send_text('transaction_id_filter', transaction_id)
        sub_log.wait_table_load()

        add_logger.info('Проверяем статус Sub operation log')
        status_sub_pay_out = main.get_text('sub_status_row0')
        add_logger.info(f'Success == {status_sub_pay_out}')
        assert status_sub_pay_out == 'Success'

        add_logger.info('Проверяем саб-транзакцию')
        main.click('sub_expand_row0')
        time.sleep(1)
        status_sub_tr = main.get_text('sub_status_row0_sub')
        add_logger.info(f'Success == {status_sub_tr}')
        assert status_sub_tr == 'Success'

        add_logger.info('ТЕСТ ЗАВЕРШЕН')
        status = '1'
        comment = 'test passed'

    except Exception as e:
        error_text = traceback.format_exc()
        add_logger.error(f"Ошибка: {e}\n{error_text}")
        status = '5'
        comment = f"test failed: {e}"
        raise

    finally:
        response = TestRail.add_test_result_with_attachment(
            TestConfig.login,
            TestConfig.password,
            test_case_id,
            status,
            comment,
            TestsData.log_file_name,
            my_test_run_id=TestRail.test_run_id
        )
        add_logger.info(f'Результат отправлен в TestRail: {response}')