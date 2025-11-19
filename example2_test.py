import sys
import os
import pytest
import traceback
from mrfix.mrfix import MrFixUI as MrUI
from Tests_Data.base_methods_and_data import TestsData, BaseMethods, TestRail
from Pages.main_page import MainPage
from Pages.user_page import UserPage
from Pages.sub_page import SubPayInPage
from Tests_Data.demo_data import DemoData
from Tests_Data.for_tests_selectors import Menu, SubPayIn

test_case_id = 'TEST_001'

@pytest.mark.smoke
def test(browser, add_logger):
    os.environ['test_case_id'] = 'TEST_001'
    os.environ['assignedto_id'] = '48'

    main = MainPage(browser, add_logger)
    sub_pay = SubPayInPage(browser, add_logger)
    user_management = UserPage(browser, add_logger)
    super_admin_user = TestsData.user_admin
    internal_user = TestsData.user_internal

    try:
        main.login(super_admin_user)
        main.go_to_Sub_PayIn()
        add_logger.info("Копируем значение processing_id у первой операции")
        processing_id = MrUI.get_element_text(browser, SubPayIn.Processing_Id_row0_xpath)
        add_logger.info(processing_id)
        user_management.edit_users_hide_transaction_option(internal_user, 'sub_payin_log', True)
        main.login(internal_user)
        main.go_to_Sub_PayIn_operation_log()
        add_logger.info("Проверяем, что у internal user отображается пустая страница")
        assert MrUI.is_element_present(browser, SubPayIn.No_data_message_xpath), "Таблица Sub PayIn Operations Log не пустая"
        add_logger.info("Изменяем диапазон дан и увеличиваем на 30 дней")
        date_from, date_to = main.get_date_from_last_30_day()
        sub_pay.set_dates(date_from, date_to)
        add_logger.info("Проверяем, что у internal user по прежнему отображается пустая страница")
        assert MrUI.is_element_present(browser,
                                       SubPayIn.No_data_message_xpath), "Таблица Sub PayIn Operations Log не пустая"
        add_logger.info("Вводим в фильтр в столбце Processing Id скопированное значение Processing Id")
        MrUI.send_text_to_input(browser, SubPayIn.Processing_Id_filter_xpath, processing_id)
        MrUI.click_element_by_xpath(browser, SubPayIn.Search_button_xpath)
        sub_pay.wait_table_load()
        add_logger.info(f"Проверяем, что в таблице отображается операция с processing_id {processing_id}")
        processing_id_from_table = MrUI.get_element_text(browser, SubPayIn.Processing_Id_row0_xpath)
        assert processing_id_from_table == processing_id, f"Processing_id из таблицы {processing_id_from_table} и скопированный ранее {processing_id} не совпадают"

        add_logger.info(f"Удаляем один символ из строки processing_id и проверяем, что отображается пустая таблица")
        MrUI.click_element_by_xpath(browser, SubPayIn.Processing_Id_filter_xpath)
        MrUI.press_backspace_key(browser, 1)
        MrUI.click_element_by_xpath(browser, SubPayIn.Search_button_xpath)
        sub_pay.wait_table_load()

        assert MrUI.is_element_present(browser,
                                       SubPayIn.No_data_message_xpath), "Таблица Sub PayIn Operations Log не пустая"

        add_logger.info(f"Удаляем из строки processing_id {processing_id}")
        MrUI.clear_input_element(browser, SubPayIn.Search_button_xpath)
        add_logger.info(f"Вводим в строку processing_id несуществующий в системе processing_id")
        MrUI
        user_management.edit_users_hide_transaction_option(internal_user, 'sub_payin_log', False)

        add_logger.info('ТЕСТ УСПЕШНО ЗАВЕРШЕН')
        add_logger.info(f'Добавляем результат записи в TestRail')

        status = '1'
        comment = 'test passed'

    except Exception as e:
        error_text = traceback.format_exc()
        add_logger.error(f"Тест упал с ошибкой: {e}\n{error_text}")
        status = '5'
        comment = f"test failed: {e}"
        raise

    finally:
        response = TestRail.add_test_result_with_attachment(
            DemoData.login,
            DemoData.password,
            test_case_id,
            status,
            comment,
            TestsData.log_file_name,
            my_test_run_id=TestRail.test_run_id
        )

        add_logger.info(f'Результат отправлен в TestRail: {response}')
