# -*- coding: utf-8 -*-


def test_liverver_thread(driver, admin_user):
    driver.get('/admin/')
    driver.find_element_by_xpath("//input[@id='id_username']").send_keys(admin_user.username)

    driver.find_element_by_xpath('//input[@id="id_password"]').send_keys('admin')
    driver.find_element_by_xpath('//input[@type="submit"]').click()
    assert driver.find_element_by_xpath('//div[@id="user-tools"]')


def test_after_liveserver():
    "shouldnt have any users in db"
    from django.contrib.auth.models import User
    assert User.objects.count() == 0
