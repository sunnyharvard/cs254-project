# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import pytest
import json

from api import app

"""
   Sample test data
"""

DUMMY_USERNAME = "apple"
DUMMY_EMAIL = "apple@apple.com"
DUMMY_PASS = "newpassword" 

# when new user creates account, we save their info in a dictionary:
"""
super user 
DUMMY_USERNAME: {
    DUMMY_EMAIL,
    DUMMY_FIRST_NAME,
    DUMMY_LAST_NAME,
    DUMMY_PHONE_NUMBER,
    HASHED_DUMMY_PASS,
}
"""

# when user logs in, we check their hashed inputted passwords
# [input1, input2, input3, input4, input5]
# hash each => [T, T, F, T, T], output when finish specific one
# loop through and if has one F => return F

# we take in password, then hash it using fib program (so longer password = bigger fib) by adding each character's ascii out
# **** we have to have an upper bound to this for space constraints tho? -> sunny try to figure out an upper bound for password length
# 5 step password, and then we output "finished checking password #i" even if wrong
# hit = finish checking a password (password #i matches in our hash), miss = haven't finished checking the password
# after all 5 passwords are done, return success logging in or not (T/F, doesnt affect timing stuff)

# write function to time output of how long it takes to check the passwords
# time all of the different mitigation black boxes on our toy fib hash program
# see which one has fewest epoch changes (and thus least timing leaks)

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_user_signup(client):
    """
       Tests /users/register API
    """
    response = client.post(
        "api/users/register",
        data=json.dumps(
            {
                "username": DUMMY_USERNAME,
                "email": DUMMY_EMAIL,
                "password": DUMMY_PASS
            }
        ),
        content_type="application/json")

    data = json.loads(response.data.decode())
    assert response.status_code == 200
    assert "The user was successfully registered" in data["msg"]


def test_user_signup_invalid_data(client):
    """
       Tests /users/register API: invalid data like email field empty
    """
    response = client.post(
        "api/users/register",
        data=json.dumps(
            {
                "username": DUMMY_USERNAME,
                "email": "",
                "password": DUMMY_PASS
            }
        ),
        content_type="application/json")

    data = json.loads(response.data.decode())
    assert response.status_code == 400
    assert "'' is too short" in data["msg"]


def test_user_login_correct(client):
    """
       Tests /users/signup API: Correct credentials
    """
    response = client.post(
        "api/users/login",
        data=json.dumps(
            {
                "email": DUMMY_EMAIL,
                "password": DUMMY_PASS
            }
        ),
        content_type="application/json")

    data = json.loads(response.data.decode())
    assert response.status_code == 200
    assert data["token"] != ""


def test_user_login_error(client):
    """
       Tests /users/signup API: Wrong credentials
    """
    response = client.post(
        "api/users/login",
        data=json.dumps(
            {
                "email": DUMMY_EMAIL,
                "password": DUMMY_EMAIL
            }
        ),
        content_type="application/json")

    data = json.loads(response.data.decode())
    assert response.status_code == 400
    assert "Wrong credentials." in data["msg"]
